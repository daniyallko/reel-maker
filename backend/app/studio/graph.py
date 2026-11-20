import asyncio
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.events import EventBus
from app.studio.harvest import harvest
from app.studio.motion import fallback_motion_html, generate_motion_html, select_brand_accent
from app.studio.research import fallback_research_plan, fallback_research_report, research_queries
from app.studio.renderer import MotionRenderer, verify_studio_video
from app.studio.schemas import HarvestResult, ResearchReport, SourceCitation, Storyboard, StudioAsset, StudioAudio, StudioOutput
from app.studio.timeline import align_audio_timeline
from app.studio.vision import MAX_REVISIONS, capture_keyframes, require_passing_audit, require_unaudited_allowed, review_label_for, should_use_unaudited_fallback


async def emit_heartbeat(events: EventBus, agent: str, message: str, progress: float, work):
    task = asyncio.create_task(work)
    started = asyncio.get_running_loop().time()
    while not task.done():
        elapsed = round(asyncio.get_running_loop().time() - started)
        await events.emit(agent, "running", f"{message} ({elapsed}s)", progress)
        await asyncio.sleep(4)
    return await task


class StudioState(TypedDict, total=False):
    project_id: str
    project_dir: Path
    source_url: str
    source_bundle: HarvestResult
    style: str
    voice: str
    quality_mode: str
    review_label: str | None
    events: EventBus
    harvest: HarvestResult
    sources: list[SourceCitation]
    research_report: ResearchReport
    storyboard: Storyboard
    assets: list[StudioAsset]
    visuals: list[StudioAsset]
    audio: StudioAudio
    html: str
    output: StudioOutput
    critique_scores: dict[str, int]


def requires_web_harvest(bundle: HarvestResult) -> bool:
    return bundle.source_url.lower().startswith(("http://", "https://"))


def merge_source_bundle(primary: HarvestResult, uploaded: HarvestResult) -> HarvestResult:
    return primary.model_copy(update={
        "kind": uploaded.kind,
        "dom_copy": "\n\n".join(part for part in (primary.dom_copy, uploaded.dom_copy) if part),
        "assets": [*uploaded.assets, *primary.assets],
        "image_paths": [*uploaded.image_paths, *primary.image_paths],
        "citations": [*primary.citations, *uploaded.citations],
    })


async def research_bundle(
    provider,
    bundle: HarvestResult | None,
    source_url: str,
    project_dir: Path,
    sample: bool = False,
    style: str = "deep_dive",
) -> tuple[HarvestResult, ResearchReport]:
    needs_harvest = bundle is None or requires_web_harvest(bundle)
    if sample:
        harvested = await harvest(source_url, project_dir) if needs_harvest else bundle
        plan = fallback_research_plan(harvested, style)
        return harvested, fallback_research_report(harvested, plan, [])

    if needs_harvest and bundle is None:
        harvested = await harvest(source_url, project_dir)
        plan = await provider.plan_research(harvested, style)
        sources = await research_queries(source_url, plan.queries)
        report = await provider.synthesize_research(harvested, plan, sources)
        return harvested, report

    if needs_harvest:
        harvest_task = asyncio.create_task(harvest(source_url, project_dir))
        plan = await provider.plan_research(bundle, style)
        research_task = asyncio.create_task(research_queries(source_url, plan.queries))
        primary, sources = await asyncio.gather(harvest_task, research_task)
        harvested = merge_source_bundle(primary, bundle)
    else:
        harvested = bundle
        plan = await provider.plan_research(bundle, style)
        sources = await research_queries(source_url, plan.queries)
    report = await provider.synthesize_research(harvested, plan, sources)
    return harvested, report


def build_studio_graph(provider, renderer: MotionRenderer, vision_director=None, sample: bool = False):
    async def research(state: StudioState) -> dict[str, Any]:
        events = state["events"]
        await events.emit("harvester", "running", "Capturing the live page and brand system…", 8)
        await events.emit("researcher", "running", "Finding the story beyond the landing page…", 10)
        work = research_bundle(
            provider,
            state.get("source_bundle"),
            state["source_url"],
            state["project_dir"],
            sample=sample,
            style=state["style"],
        )
        agent = "harvester" if sample else "researcher"
        message = "Capturing the live page and brand system…" if sample else "Finding the story beyond the landing page…"
        progress = 8 if sample else 10
        harvested, report = await emit_heartbeat(events, agent, message, progress, work)
        await events.emit("harvester", "complete", f"{len(harvested.assets)} real source assets captured.", 20, assets=harvested.assets)
        await events.emit("researcher", "complete", f"{len(report.sources)} sources synthesized with {report.provider}.", 24)
        return {
            "harvest": harvested,
            "sources": report.sources,
            "research_report": report,
            "assets": harvested.assets,
        }

    async def write(state: StudioState) -> dict[str, Any]:
        events = state["events"]
        await events.emit("scriptwriter", "running", "Writing the four-act beat map…", 32)
        storyboard = await provider.write_storyboard(
            state["harvest"],
            state["sources"],
            state["style"],
            state["voice"],
            research=state["research_report"],
        )
        await events.emit("scriptwriter", "complete", f"Storyboard locked at {storyboard.duration:.0f} seconds.", 42, payload={"storyboard": storyboard.model_dump()})
        return {"storyboard": storyboard}

    async def visuals(state: StudioState) -> dict[str, Any]:
        events = state["events"]
        await events.emit("nano_visuals", "running", "Generating vertical art and the cover…", 48)
        assets = await provider.generate_visuals(state["storyboard"], state["harvest"], state["project_dir"])
        await events.emit("nano_visuals", "complete", f"{len(assets)} vertical assets rendered.", 58, assets=assets)
        return {"visuals": assets, "assets": state["assets"] + assets}

    async def audio(state: StudioState) -> dict[str, Any]:
        events = state["events"]
        await events.emit("voice_studio", "running", "Synthesizing and measuring narration segments…", 50)
        audio = await provider.synthesize(state["storyboard"], state["project_dir"])
        return {"audio": audio}

    async def timing(state: StudioState) -> dict[str, Any]:
        storyboard, audio = align_audio_timeline(state["storyboard"], state["audio"], state["project_dir"])
        await state["events"].emit(
            "voice_studio",
            "complete",
            "Narration aligned to scene timings.",
            60,
            payload={"preview_url": audio.preview_url},
        )
        return {"storyboard": storyboard, "audio": audio}

    async def motion(state: StudioState) -> dict[str, Any]:
        events = state["events"]
        await events.emit("motion_coder", "running", "Programming deterministic motion scenes…", 66)
        html = await generate_motion_html(state["storyboard"], state["visuals"], None if sample else provider, state["project_dir"], palette=state["harvest"].palette)
        await events.emit("motion_coder", "complete", "Every frame is locked to seekTo(t).", 72)
        return {"html": html}

    async def vision(state: StudioState) -> dict[str, Any]:
        events = state["events"]
        quality_mode = state.get("quality_mode", "strict")
        await events.emit("vision_director", "running", "Auditing six director stills…", 78)
        html = state["html"]
        audit = None
        reported = 0
        for attempt in range(MAX_REVISIONS + 1):
            contact = await capture_keyframes(html, state["project_dir"], [0.6, 3.5, 8, 14, 21, 27])
            if vision_director is None:
                break
            audit = await vision_director.safe_audit(contact, html)
            history = getattr(vision_director.router, "history", [])
            for entry in history[reported:]:
                await events.emit("vision_director", "running", f"Provider response / {entry}", 79)
            reported = len(history)
            try:
                require_passing_audit(audit, quality_mode)
            except RuntimeError:
                if not audit.scores:
                    if attempt == MAX_REVISIONS:
                        require_unaudited_allowed(quality_mode)
                        html = fallback_motion_html(state["storyboard"], state["visuals"], accent=select_brand_accent(state["harvest"].palette))
                        break
                    html = fallback_motion_html(state["storyboard"], state["visuals"], accent=select_brand_accent(state["harvest"].palette))
                    continue
                if attempt == MAX_REVISIONS:
                    if should_use_unaudited_fallback(quality_mode, attempt):
                        await events.emit("vision_director", "running", "Audit thresholds missed; rendering an unreviewed deterministic draft.", 82)
                        audit = None
                        html = fallback_motion_html(state["storyboard"], state["visuals"], accent=select_brand_accent(state["harvest"].palette))
                        break
                    raise
                try:
                    html = await vision_director.repair(contact, html, audit, state["project_dir"])
                except Exception:
                    await events.emit("vision_director", "running", "Motion repair failed; deterministic template selected.", 80)
                    html = fallback_motion_html(state["storyboard"], state["visuals"], accent=select_brand_accent(state["harvest"].palette))
            else:
                break
        asset = StudioAsset(id="critique", kind="critique", label="Director contact sheet", url=f"/media/{state['project_id']}/audit/contact-sheet.png", mime_type="image/png", local_path=contact)
        message = audit.issues[0] if audit and audit.issues else ("Six stills passed the director audit." if audit and audit.passed else "Six director stills captured for offline review.")
        scores = {score.criterion: score.score for score in audit.scores} if audit else {}
        review_label = review_label_for(audit, quality_mode)
        await events.emit("vision_director", "complete", message, 84, assets=[asset], payload={"critique_scores": scores, "review_label": review_label})
        return {"html": html, "assets": state["assets"] + [asset], "critique_scores": scores, "review_label": review_label}

    async def render(state: StudioState) -> dict[str, Any]:
        events = state["events"]
        await events.emit("renderer", "running", "Capturing 30fps motion frames and mixing audio…", 90)
        output = await renderer.render(state["html"], state["storyboard"], state["visuals"], state["audio"], state["project_dir"], source_url=state["source_url"], critique_scores=state.get("critique_scores", {}), quality_mode=state.get("quality_mode", "strict"), review_label=state.get("review_label"))
        await events.emit("renderer", "complete", "Final motion reel exported.", 96)
        return {"output": output}

    async def qa(state: StudioState) -> dict[str, Any]:
        events = state["events"]
        await events.emit("qa_critic", "running", "Checking duration, frames, and audio…", 98)
        result = verify_studio_video(state["project_dir"] / "output" / "trailer.mp4")
        if not result.valid:
            raise RuntimeError("; ".join(result.errors))
        await events.emit("qa_critic", "complete", "Projection approved.", 100)
        return {}

    graph = StateGraph(StudioState)
    graph.add_node("research", research)
    graph.add_node("write", write)
    graph.add_node("visuals", visuals)
    graph.add_node("audio", audio)
    graph.add_node("timing", timing)
    graph.add_node("motion", motion)
    graph.add_node("vision", vision)
    graph.add_node("render", render)
    graph.add_node("qa", qa)
    graph.add_edge(START, "research")
    graph.add_edge("research", "write")
    graph.add_edge("write", "visuals")
    graph.add_edge("write", "audio")
    graph.add_edge("visuals", "timing")
    graph.add_edge("audio", "timing")
    graph.add_edge("timing", "motion")
    graph.add_edge("motion", "vision")
    graph.add_edge("vision", "render")
    graph.add_edge("render", "qa")
    graph.add_edge("qa", END)
    return graph.compile()
