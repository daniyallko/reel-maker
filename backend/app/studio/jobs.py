import asyncio
import logging
import shutil
import time
import uuid
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from app.config import Settings
from app.events import EventBus
from app.schemas import ProjectStatus
from app.studio.graph import build_studio_graph
from app.studio.providers import GeminiStudioProvider, MockStudioProvider
from app.studio.renderer import SAMPLE_OUTPUT, MotionRenderer
from app.studio.schemas import SourceBundle, SourceCitation, StudioAsset, StudioOutput, StudioProjectSnapshot
from app.studio.sources import ingest_text, ingest_uploads
from app.studio.urls import validate_public_url
from app.studio.vision import VisionDirector, director_review_times
from app.studio.vision_providers import build_vision_router


def _image_manifest(assets: list[StudioAsset]) -> str:
    if not assets:
        return ""
    labels = ", ".join(asset.label for asset in assets)
    return f"{len(assets)} source image{'s' if len(assets) != 1 else ''}: {labels}"


def _upload_citations(text: str, assets: list[StudioAsset]) -> list[SourceCitation]:
    citations = []
    if text:
        citations.append(SourceCitation(url="inline://uploads", title="Uploaded documents", claim=text[:240]))
    if assets:
        citations.append(SourceCitation(url="inline://images", title="Uploaded images", claim=_image_manifest(assets)))
    return citations


@dataclass
class StudioJob:
    id: str
    source_url: str
    style: str
    voice: str
    directory: Path
    events: EventBus
    created_at: float = field(default_factory=time.time)
    status: ProjectStatus = ProjectStatus.QUEUED
    source_bundle: SourceBundle | None = None
    source_title: str = ""
    quality_mode: str = "strict"
    assets: list[StudioAsset] = field(default_factory=list)
    output: StudioOutput | None = None
    error: str | None = None
    task: asyncio.Task | None = None

    def snapshot(self) -> StudioProjectSnapshot:
        return StudioProjectSnapshot(
            id=self.id,
            status=self.status,
            source_url=self.source_url,
            source_title=self.source_title or self.source_url,
            style=self.style,
            voice=self.voice,
            quality_mode=self.quality_mode,
            created_at=self.created_at,
            assets=self.assets,
            events=self.events.events,
            output=self.output,
            error=self.error,
        )


class StudioJobManager:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.jobs: dict[str, StudioJob] = {}

    @staticmethod
    def new_id() -> str:
        return uuid.uuid4().hex[:12]

    def get(self, project_id: str) -> StudioJob:
        if project_id not in self.jobs:
            self._restore(project_id)
        return self.jobs[project_id]

    def _restore(self, project_id: str) -> None:
        directory = self.settings.data_dir / project_id
        output_path = directory / "output" / "studio-output.json"
        if not output_path.exists():
            raise LookupError("Project not found")
        output = StudioOutput.model_validate_json(output_path.read_text())
        source_url = output.source_url or (output.sources[0].url if output.sources else "")
        job = StudioJob(
            id=project_id,
            source_url=source_url,
            style=output.style,
            voice=output.voice,
            directory=directory,
            source_title=output.title,
            quality_mode=output.quality_mode,
            events=EventBus(project_id),
            status=ProjectStatus.COMPLETE,
            output=output,
        )
        self.jobs[project_id] = job

    async def create(self, url: str, style: str, voice: str, sample: bool = False, quality_mode: str = "strict") -> StudioProjectSnapshot:
        source_url = "https://daniyal.pro" if sample else await validate_public_url(url)
        project_id = self.new_id()
        directory = self.settings.data_dir / project_id
        directory.mkdir(parents=True, exist_ok=False)
        job = StudioJob(
            id=project_id,
            source_url=source_url,
            style=style,
            voice=voice,
            directory=directory,
            source_title="Mohd Daniyal — Production AI in Motion" if sample else source_url,
            quality_mode=quality_mode,
            events=EventBus(project_id),
        )
        self.jobs[project_id] = job
        logging.getLogger(__name__).info("Creating LINK2REEL project %s for %s", project_id, source_url)
        job.task = asyncio.create_task(self._run(job, sample), name=f"link2reel-{project_id}")
        return job.snapshot()

    async def create_input(self, source: str, style: str, voice: str, files: list[tuple[str, str, bytes]], quality_mode: str = "strict") -> StudioProjectSnapshot:
        source = source.strip()
        project_id = self.new_id()
        directory = self.settings.data_dir / project_id
        directory.mkdir(parents=True, exist_ok=False)
        uploaded_text, uploaded_assets, image_paths = ingest_uploads(files, directory)
        is_url = source.lower().startswith(("http://", "https://"))
        if is_url:
            source_url = await validate_public_url(source)
            bundle = SourceBundle(
                kind="mixed" if files else "url",
                title=source_url,
                source_url=source_url,
                dom_copy=uploaded_text,
                palette=[],
                fonts=[],
                assets=uploaded_assets,
                citations=_upload_citations(uploaded_text, uploaded_assets),
                image_paths=image_paths,
                scroll_video=Path(),
            )
        else:
            text = source or uploaded_text
            if not text and not uploaded_assets:
                raise ValueError("Enter a topic, description, URL, or source file.")
            bundle = ingest_text(text or Path(files[0][0]).stem, title=None if source else Path(files[0][0]).stem)
            combined = "\n\n".join(part for part in (source, uploaded_text) if part).strip() or _image_manifest(uploaded_assets)
            citations = [*_upload_citations(uploaded_text, uploaded_assets), *bundle.citations]
            bundle = bundle.model_copy(update={
                "kind": "mixed" if files else "text",
                "dom_copy": combined,
                "assets": uploaded_assets,
                "image_paths": image_paths,
                "citations": citations,
            })
        job = StudioJob(
            id=project_id,
            source_url=bundle.source_url,
            source_bundle=bundle,
            source_title=bundle.title,
            quality_mode=quality_mode,
            style=style,
            voice=voice,
            directory=directory,
            events=EventBus(project_id),
        )
        self.jobs[project_id] = job
        logging.getLogger(__name__).info("Creating LINK2REEL project %s for %s", project_id, bundle.source_url)
        job.task = asyncio.create_task(self._run(job, False), name=f"link2reel-{project_id}")
        return job.snapshot()

    async def _run(self, job: StudioJob, sample: bool) -> None:
        job.status = ProjectStatus.RUNNING
        try:
            if sample and (SAMPLE_OUTPUT / "sample.json").exists():
                output = await self._replay_sample(job)
            elif self.settings.kimi_only and not sample:
                from app.studio.kimi_only import make_film
                bundle = job.source_bundle
                if not bundle or not bundle.dom_copy or bundle.kind != "text":
                    raise ValueError("Kimi-only mode currently accepts a text brief.")
                async def progress(stage, message, value):
                    await job.events.emit(stage, "running", message, value)
                output = await make_film(self.settings, job.directory, bundle.dom_copy, progress, job.style, bundle.citations, job.quality_mode)
            else:
                provider = MockStudioProvider() if sample else GeminiStudioProvider(self.settings.gemini_api_key or "", settings=self.settings)
                graph = build_studio_graph(
                    provider,
                    MotionRenderer(),
                    None if sample else VisionDirector(provider.client, router=build_vision_router(self.settings, provider.client)),
                    sample=sample,
                )
                result = await graph.ainvoke({
                    "project_id": job.id,
                    "project_dir": job.directory,
                    "source_url": job.source_url,
                    "source_bundle": job.source_bundle,
                    "style": job.style,
                    "voice": job.voice,
                    "quality_mode": job.quality_mode,
                    "events": job.events,
                })
                job.assets = result["assets"]
                output = result["output"]
            job.output = output
            job.status = ProjectStatus.COMPLETE
            await job.events.emit("premiere", "complete", "Your motion reel is ready.", 100, payload={"output": output.model_dump()})
        except Exception as error:
            message = str(error) or type(error).__name__
            job.status = ProjectStatus.FAILED
            job.error = message
            await job.events.emit("pipeline", "failed", message, 100)
        finally:
            await job.events.close()

    async def _replay_sample(self, job: StudioJob) -> StudioOutput:
        import json
        payload = json.loads((SAMPLE_OUTPUT / "sample.json").read_text())
        output = StudioOutput.model_validate(payload["output"])
        assets: list[StudioAsset] = []
        for data in payload["assets"]:
            relative = data["url"].removeprefix("/media/sample-output/")
            destination = job.directory / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            await asyncio.to_thread(shutil.copy2, SAMPLE_OUTPUT / relative, destination)
            assets.append(StudioAsset(**{**data, "url": f"/media/{job.id}/{relative}", "local_path": destination}))
        critique_path = job.directory / "audit" / "contact-sheet.png"
        critique_path.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(shutil.copy2, SAMPLE_OUTPUT / "audit" / "contact-sheet.png", critique_path)
        if not any(asset.id == "critique" for asset in assets):
            assets.append(StudioAsset(id="critique", kind="critique", label="Director contact sheet", url=f"/media/{job.id}/audit/contact-sheet.png", mime_type="image/png", local_path=critique_path))
        visual_assets = [asset for asset in assets if asset.id.startswith("scene-") or asset.kind == "thumbnail"]
        visual_ids = {asset.id for asset in visual_assets}
        source_assets = [asset for asset in assets if asset.kind != "critique" and asset.id not in visual_ids]
        critique_assets = [asset for asset in assets if asset.kind == "critique"]
        web_count = sum(source.url.startswith(("http://", "https://")) for source in output.sources)
        inline_count = len(output.sources) - web_count
        review_count = len(director_review_times(output))
        await job.events.emit("harvester", "complete", "Portfolio captures and CV evidence loaded.", 20, assets=source_assets)
        await job.events.emit("researcher", "complete", f"{len(output.sources)} citations indexed ({web_count} web, {inline_count} inline).", 24)
        await job.events.emit("scriptwriter", "complete", f"Storyboard locked at {output.duration:g} seconds.", 42)
        await job.events.emit("nano_visuals", "complete", f"{len(visual_assets)} scene and cover visuals rendered.", 58, assets=visual_assets)
        await job.events.emit("voice_studio", "complete", "Narration aligned to scene timings; captions are scene-bounded estimates.", 60, payload={"preview_url": f"/media/{job.id}/audio/narration.wav"})
        await job.events.emit("motion_coder", "complete", "Every frame is locked to seekTo(t).", 72)
        await job.events.emit("vision_director", "complete", f"{review_count} director stills packaged for offline review.", 84, assets=critique_assets)
        await job.events.emit("renderer", "running", "Loading the pre-baked 30fps motion reel…", 92)

        output_dir = job.directory / "output"
        audio_dir = job.directory / "audio"
        output_dir.mkdir(parents=True, exist_ok=True)
        audio_dir.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(shutil.copy2, SAMPLE_OUTPUT / "trailer.mp4", output_dir / "trailer.mp4")
        await asyncio.to_thread(shutil.copy2, SAMPLE_OUTPUT / "visuals" / "thumbnail-03.png", output_dir / "thumbnail.png")
        await asyncio.to_thread(shutil.copy2, SAMPLE_OUTPUT / "audio" / "narration.wav", audio_dir / "narration.wav")
        output = output.model_copy(update={
            "trailer_url": f"/media/{job.id}/output/trailer.mp4",
            "thumbnail_url": f"/media/{job.id}/output/thumbnail.png",
            "preview_url": f"/media/{job.id}/audio/narration.wav",
        })
        job.assets = assets
        await asyncio.sleep(0.2)
        await job.events.emit("renderer", "complete", "Final motion reel exported.", 96)
        await job.events.emit("qa_critic", "complete", "Projection approved.", 100)
        return output

    def press_kit_zip(self, project_id: str) -> Path:
        job = self.get(project_id)
        if job.status != ProjectStatus.COMPLETE or not job.output:
            raise LookupError("Press kit is not ready")
        path = job.directory / "output" / "link2reel-press-kit.zip"
        thumbnail_relative = job.output.thumbnail_url.removeprefix(f"/media/{job.id}/")
        thumbnail_path = job.directory / thumbnail_relative
        if not thumbnail_path.exists():
            thumbnail_path = job.directory / "output" / "thumbnail.png"
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(job.directory / "output" / "trailer.mp4", "trailer.mp4")
            archive.write(thumbnail_path, "thumbnail.png")
            archive.writestr("script.txt", job.output.script)
            archive.writestr("sources.json", __import__("json").dumps([source.model_dump() for source in job.output.sources], indent=2))
        return path
