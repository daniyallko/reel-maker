import asyncio
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.events import EventBus
from app.studio.harvest import harvest
from app.studio.motion import fallback_motion_html, generate_motion_html, select_brand_accent
from app.studio.research import research_url
from app.studio.renderer import MotionRenderer, verify_studio_video
from app.studio.schemas import HarvestResult, SourceCitation, Storyboard, StudioAsset, StudioAudio, StudioOutput
from app.studio.vision import MAX_REVISIONS, capture_keyframes, require_passing_audit


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
    style: str
    voice: str
    events: EventBus
    harvest: HarvestResult
    sources: list[SourceCitation]
    storyboard: Storyboard
    assets: list[StudioAsset]
    visuals: list[StudioAsset]
    audio: StudioAudio
    html: str
    output: StudioOutput
    critique_scores: dict[str, int]


def build_studio_graph(provider, renderer: MotionRenderer, vision_director=None, sample: bool = False):
    async def research(state: StudioState) -> dict[str, Any]:
        events = state["events"]
        await events.emit("harvester", "running", "Capturing the live page and brand system…", 8)
        await events.emit("researcher", "running", "Finding the story beyond the landing page…", 10)
        if sample:
            harvested = await emit_heartbeat(events, "harvester", "Capturing the live page and brand system…", 8, harvest(state["source_url"], state["project_dir"]))
            sources: list[SourceCitation] = []
        else:
            harvested, sources = await asyncio.gather(
                emit_heartbeat(events, "harvester", "Capturing the live page and brand system…", 8, harvest(state["source_url"], state["project_dir"])),
                emit_heartbeat(events, "researcher", "Finding the story beyond the landing page…", 10, research_url(state["source_url"], state["source_url"])),
            )
        await events.emit("harvester", "complete", f"{len(harvested.assets)} real source assets captured.", 20, assets=harvested.assets)
        await events.emit("researcher", "complete", f"{len(sources)} external sources indexed.", 24)
        return {"harvest": harvested, "sources": sources, "assets": harvested.assets}

    async def write(state: StudioState) -> dict[str, Any]:
        events = state["events"]
        await events.emit("scriptwriter", "running", "Writing the four-act beat map…", 32)
        storyboard = await provider.write_storyboard(state["harvest"], state["sources"], state["style"], state["voice"])
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
        await events.emit("voice_studio", "running", "Synthesizing narration and word timings…", 50)
        audio = await provider.synthesize(state["storyboard"], state["project_dir"])
        await events.emit("voice_studio", "complete", "Narration and captions are synced.", 60, payload={"preview_url": audio.preview_url})
        return {"audio": audio}

    async def motion(state: StudioState) -> dict[str, Any]:
        events = state["events"]
        await events.emit("motion_coder", "running", "Programming deterministic motion scenes…", 66)
        html = await generate_motion_html(state["storyboard"], state["visuals"], None if sample else provider, state["project_dir"], palette=state["harvest"].palette)
        await events.emit("motion_coder", "complete", "Every frame is locked to seekTo(t).", 72)
        return {"html": html}

    async def vision(state: StudioState) -> dict[str, Any]:
        events = state["events"]
        await events.emit("vision_director", "running", "Auditing six director stills…", 78)
        html = state["html"]
        audit = None
        for attempt in range(MAX_REVISIONS + 1):
            contact = await capture_keyframes(html, state["project_dir"], [0.6, 3.5, 8, 14, 21, 27])
            if vision_director is None:
                break
            audit = await vision_director.safe_audit(contact, html)
            try:
                require_passing_audit(audit)
            except RuntimeError:
                if attempt == MAX_REVISIONS:
                    raise
                html = audit.patched_html or fallback_motion_html(state["storyboard"], state["visuals"], accent=select_brand_accent(state["harvest"].palette))
            else:
                break
        asset = StudioAsset(id="critique", kind="critique", label="Director contact sheet", url=f"/media/{state['project_id']}/audit/contact-sheet.png", mime_type="image/png", local_path=contact)
        message = audit.issues[0] if audit and audit.issues else ("Six stills passed the director audit." if audit and audit.passed else "Six director stills captured for offline review.")
        await events.emit("vision_director", "complete", message, 84, assets=[asset], payload={"critique_scores": {score.criterion: score.score for score in audit.scores} if audit else {}})
        return {"html": html, "assets": state["assets"] + [asset], "critique_scores": {score.criterion: score.score for score in audit.scores} if audit else {}}

    async def render(state: StudioState) -> dict[str, Any]:
        events = state["events"]
        await events.emit("renderer", "running", "Capturing 30fps motion frames and mixing audio…", 90)
        output = await renderer.render(state["html"], state["storyboard"], state["visuals"], state["audio"], state["project_dir"], source_url=state["source_url"], critique_scores=state.get("critique_scores", {}))
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
    graph.add_node("motion", motion)
    graph.add_node("vision", vision)
    graph.add_node("render", render)
    graph.add_node("qa", qa)
    graph.add_edge(START, "research")
    graph.add_edge("research", "write")
    graph.add_edge("write", "visuals")
    graph.add_edge("write", "audio")
    graph.add_edge("visuals", "motion")
    graph.add_edge("audio", "motion")
    graph.add_edge("motion", "vision")
    graph.add_edge("vision", "render")
    graph.add_edge("render", "qa")
    graph.add_edge("qa", END)
    return graph.compile()
