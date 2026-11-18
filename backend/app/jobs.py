import asyncio
import shutil
import time
import uuid
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from app.config import Settings
from app.events import EventBus
from app.graph import build_graph
from app.media.audio import AudioProducer
from app.media.editor import VideoEditor
from app.media.poster import PosterArtDirector
from app.media.prefilter import prefilter_assets
from app.providers.gemini import GeminiProvider
from app.providers.mock import MockPerceptionProvider, MockScreenwriterProvider
from app.schemas import (
    AssetInput,
    AssetStatus,
    CuratedAsset,
    Genre,
    PressKitOutput,
    ProjectSnapshot,
    ProjectStatus,
)
from app.validation import UploadValidationError

BACKEND_DIR = Path(__file__).resolve().parent.parent
SAMPLE_DIR = BACKEND_DIR / "assets" / "sample"


@dataclass
class Job:
    id: str
    genre: Genre
    directory: Path
    events: EventBus
    created_at: float = field(default_factory=time.time)
    status: ProjectStatus = ProjectStatus.QUEUED
    assets: list[CuratedAsset] = field(default_factory=list)
    output: PressKitOutput | None = None
    error: str | None = None
    task: asyncio.Task | None = None

    def snapshot(self) -> ProjectSnapshot:
        return ProjectSnapshot(
            id=self.id,
            status=self.status,
            genre=self.genre,
            created_at=self.created_at,
            assets=self.assets,
            events=self.events.events,
            output=self.output,
            error=self.error,
        )


class JobManager:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.jobs: dict[str, Job] = {}

    @staticmethod
    def new_id() -> str:
        return uuid.uuid4().hex[:12]

    def project_dir(self, project_id: str) -> Path:
        if not project_id.isalnum():
            raise ValueError("Invalid project ID")
        return self.settings.data_dir / project_id

    def get(self, project_id: str) -> Job:
        try:
            return self.jobs[project_id]
        except KeyError as error:
            raise LookupError("Project not found") from error

    async def create(
        self,
        project_id: str,
        inputs: list[AssetInput],
        cast: list[str],
        genre: Genre,
        notes: str,
        voice_path: Path | None,
        sample: bool = False,
    ) -> ProjectSnapshot:
        directory = self.project_dir(project_id)
        job = Job(id=project_id, genre=genre, directory=directory, events=EventBus(project_id))
        self.jobs[project_id] = job
        try:
            job.assets = await asyncio.to_thread(prefilter_assets, directory, inputs)
        except Exception as exception:
            self.jobs.pop(project_id, None)
            await job.events.close()
            raise UploadValidationError(
                "Media decoding failed. Remove oversized-dimension or corrupt files and try again."
            ) from exception
        await job.events.emit(
            "prefilter", "complete", f"{len(job.assets)} source frames logged locally.", 5, assets=job.assets
        )
        job.task = asyncio.create_task(
            self._run(job, cast, notes, voice_path, sample), name=f"cutline-{project_id}"
        )
        return job.snapshot()

    async def create_sample(self) -> ProjectSnapshot:
        project_id = self.new_id()
        directory = self.project_dir(project_id)
        (directory / "uploads").mkdir(parents=True, exist_ok=False)
        inputs: list[AssetInput] = []
        for source in sorted((SAMPLE_DIR / "uploads").glob("*.jpg")):
            destination = directory / "uploads" / source.name
            await asyncio.to_thread(shutil.copy2, source, destination)
            inputs.append(
                AssetInput(
                    filename=source.name,
                    content_type="image/jpeg",
                    path=destination,
                    size=destination.stat().st_size,
                )
            )
        return await self.create(
            project_id,
            inputs,
            ["Maya", "Theo", "Nina", "Jules"],
            Genre.COMEDY,
            "Nobody admits who booked the house.",
            None,
            sample=True,
        )

    async def _run(self, job: Job, cast: list[str], notes: str, voice_path: Path | None, sample: bool) -> None:
        job.status = ProjectStatus.RUNNING
        try:
            if sample and (SAMPLE_DIR / "output" / "press-kit.json").exists():
                output = await self._replay_sample(job, cast, notes)
            else:
                perception = MockPerceptionProvider() if sample else GeminiProvider(self.settings.gemini_api_key or "")
                screenwriter = MockScreenwriterProvider() if sample else perception
                graph = build_graph(
                    perception,
                    screenwriter,
                    PosterArtDirector(use_rembg=not sample),
                    AudioProducer(),
                    VideoEditor(),
                    sample=sample,
                )
                result = await graph.ainvoke(
                    {
                        "project_id": job.id,
                        "project_dir": job.directory,
                        "assets": job.assets,
                        "cast": cast,
                        "genre": job.genre,
                        "notes": notes,
                        "voice_path": voice_path,
                        "events": job.events,
                    }
                )
                job.assets = result["assets"]
                output = result["output"]
            job.output = output
            job.status = ProjectStatus.COMPLETE
            await job.events.emit(
                "premiere", "complete", "The premiere is ready.", 100, payload={"output": output.model_dump()}
            )
        except Exception as error:
            job.status = ProjectStatus.FAILED
            job.error = str(error)
            await job.events.emit("pipeline", "failed", str(error), 100)
        finally:
            await job.events.close()

    async def _replay_sample(self, job: Job, cast: list[str], notes: str) -> PressKitOutput:
        await job.events.emit("memory_curator", "running", "Reading the contact sheet…", 12)
        await job.events.emit("voice_analyst", "running", "Listening for the real story…", 14)
        result = await MockPerceptionProvider().perceive(job.assets, cast, notes, None)
        scores = {score.id: score for score in result.assets}
        job.assets = [
            asset.model_copy(
                update={
                    "score": scores[asset.id].score,
                    "emotion": scores[asset.id].emotion,
                    "lighting": scores[asset.id].lighting,
                    "action": scores[asset.id].action,
                    "kept": scores[asset.id].kept,
                    "hero": scores[asset.id].hero,
                    "status": AssetStatus.KEPT if scores[asset.id].kept else AssetStatus.REJECTED,
                    "rejection_reason": scores[asset.id].rejection_reason,
                }
            )
            for asset in job.assets
        ]
        await asyncio.sleep(0.45)
        await job.events.emit("memory_curator", "complete", "8 shots made the cut.", 26, assets=job.assets)
        await job.events.emit("voice_analyst", "complete", "Destination locked: Big Sur.", 30)
        await job.events.emit("screenwriter", "running", "Cutting three acts from the chaos…", 36)
        edl = await MockScreenwriterProvider().write(job.assets, result.vibe, cast, job.genre, notes)
        await asyncio.sleep(0.45)
        await job.events.emit("screenwriter", "complete", "EDL locked at 22.0 seconds.", 46, payload={"edl": edl.model_dump()})
        await job.events.emit("poster_director", "complete", "Theatrical one-sheet printed.", 64)
        await job.events.emit("audio_producer", "complete", "4 narration cues locked.", 66)
        await job.events.emit("editor", "running", "Loading the pre-baked final cut…", 82)

        output_dir = job.directory / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        for source in (SAMPLE_DIR / "output").iterdir():
            if source.suffix in {".mp4", ".png", ".json"}:
                await asyncio.to_thread(shutil.copy2, source, output_dir / source.name)
        cached = PressKitOutput.model_validate_json((SAMPLE_DIR / "output" / "press-kit.json").read_text())
        cards = [
            credit.model_copy(
                update={
                    "card_url": f"/media/{job.id}/output/cast-{index + 1:02d}.png",
                    "card_path": output_dir / f"cast-{index + 1:02d}.png",
                }
            )
            for index, credit in enumerate(cached.cast_cards)
        ]
        output = cached.model_copy(
            update={
                "trailer_url": f"/media/{job.id}/output/trailer.mp4",
                "poster_url": f"/media/{job.id}/output/poster.png",
                "cast_cards": cards,
            }
        )
        await asyncio.sleep(0.45)
        await job.events.emit("editor", "complete", "Final cut exported.", 91)
        await job.events.emit("qa_critic", "complete", "Projection approved. Premiere is ready.", 100)
        return output

    def press_kit_zip(self, project_id: str) -> Path:
        job = self.get(project_id)
        if job.status != ProjectStatus.COMPLETE or not job.output:
            raise LookupError("Press kit is not ready")
        path = job.directory / "output" / "cutline-press-kit.zip"
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name in ("trailer.mp4", "poster.png", "edl.json"):
                source = job.directory / "output" / name
                archive.write(source, arcname=name)
            for index in range(len(job.output.cast_cards)):
                source = job.directory / "output" / f"cast-{index + 1:02d}.png"
                archive.write(source, arcname=f"cast/{source.name}")
        return path
