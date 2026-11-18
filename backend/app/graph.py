import asyncio
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.events import EventBus
from app.media.qa import verify_trailer
from app.providers.mock import MockScreenwriterProvider
from app.providers.base import (
    AudioProducerProtocol,
    EditorProtocol,
    PerceptionProvider,
    PosterProducer,
    ProviderError,
    ScreenwriterProvider,
)
from app.schemas import (
    AssetStatus,
    AudioTimeline,
    CuratedAsset,
    Genre,
    PerceptionResult,
    PressKitOutput,
    TrailerEDL,
    VibeProfile,
)


class CutlineState(TypedDict, total=False):
    project_id: str
    project_dir: Path
    assets: list[CuratedAsset]
    cast: list[str]
    genre: Genre
    notes: str
    voice_path: Path | None
    vibe: VibeProfile
    edl: TrailerEDL
    poster_path: Path
    audio: AudioTimeline
    output: PressKitOutput
    events: EventBus


def build_graph(
    perception: PerceptionProvider,
    screenwriter: ScreenwriterProvider,
    poster: PosterProducer,
    audio_producer: AudioProducerProtocol,
    editor: EditorProtocol,
    sample: bool = False,
):
    async def perceive(state: CutlineState) -> dict[str, Any]:
        events = state["events"]
        await events.emit("memory_curator", "running", "Reading the contact sheet…", 12)
        await events.emit("voice_analyst", "running", "Listening for the real story…", 14)
        result: PerceptionResult = await perception.perceive(
            state["assets"], state["cast"], state["notes"], state.get("voice_path")
        )
        score_map = {score.id: score for score in result.assets}
        updated: list[CuratedAsset] = []
        for asset in state["assets"]:
            score = score_map.get(asset.id)
            if score is None:
                updated.append(
                    asset.model_copy(
                        update={
                            "status": AssetStatus.REJECTED,
                            "kept": False,
                            "rejection_reason": asset.rejection_reason or "Outside the final cut",
                        }
                    )
                )
                continue
            updated.append(
                asset.model_copy(
                    update={
                        "score": score.score,
                        "emotion": score.emotion,
                        "lighting": score.lighting,
                        "action": score.action,
                        "kept": score.kept,
                        "hero": score.hero,
                        "status": AssetStatus.KEPT if score.kept else AssetStatus.REJECTED,
                        "rejection_reason": score.rejection_reason,
                    }
                )
            )
        if not any(asset.kept for asset in updated):
            raise ProviderError("No shots survived perception. Try a less blurry contact sheet.")
        if not any(asset.hero for asset in updated):
            hero = max((asset for asset in updated if asset.kept), key=lambda asset: asset.score)
            updated = [asset.model_copy(update={"hero": asset.id == hero.id}) for asset in updated]
        await events.emit(
            "memory_curator",
            "complete",
            f"{sum(asset.kept for asset in updated)} shots made the cut.",
            26,
            assets=updated,
        )
        await events.emit(
            "voice_analyst",
            "complete",
            f"Destination locked: {result.vibe.destination}.",
            30,
            payload={"vibe": result.vibe.model_dump()},
        )
        return {"assets": updated, "vibe": result.vibe}

    async def write_edl(state: CutlineState) -> dict[str, Any]:
        events = state["events"]
        await events.emit("screenwriter", "running", "Cutting three acts from the chaos…", 36)
        try:
            edl = await screenwriter.write(
                state["assets"], state["vibe"], state["cast"], state["genre"], state["notes"]
            )
        except ProviderError:
            edl = await MockScreenwriterProvider().write(
                state["assets"], state["vibe"], state["cast"], state["genre"], state["notes"]
            )
        kept_ids = {asset.id for asset in state["assets"] if asset.kept}
        used_ids = {segment.asset_id for segment in edl.segments} | {
            credit.asset_id for credit in edl.cast if credit.asset_id
        }
        if len(kept_ids) < 8 or not used_ids.issubset(kept_ids):
            edl = await MockScreenwriterProvider().write(
                state["assets"], state["vibe"], state["cast"], state["genre"], state["notes"]
            )
        await events.emit(
            "screenwriter",
            "complete",
            f"EDL locked at {edl.duration:.1f} seconds.",
            46,
            payload={"edl": edl.model_dump()},
        )
        return {"edl": edl}

    async def make_poster(state: CutlineState) -> dict[str, Any]:
        events = state["events"]
        await events.emit("poster_director", "running", "Grading the hero frame…", 52)
        path = await asyncio.to_thread(
            poster.render, state["project_dir"], state["project_id"], state["edl"], state["assets"]
        )
        await events.emit("poster_director", "complete", "Theatrical one-sheet printed.", 64)
        return {"poster_path": path}

    async def make_audio(state: CutlineState) -> dict[str, Any]:
        events = state["events"]
        await events.emit("audio_producer", "running", "Recording narration and ducking the score…", 54)
        timeline = await asyncio.to_thread(
            audio_producer.render, state["project_dir"], state["edl"], sample
        )
        await events.emit("audio_producer", "complete", f"{len(timeline.cues)} narration cues locked.", 66)
        return {"audio": timeline}

    async def render_edit(state: CutlineState) -> dict[str, Any]:
        events = state["events"]
        await events.emit("editor", "running", "Printing 1080×1920 frames…", 74)
        output = await asyncio.to_thread(
            editor.render,
            state["project_dir"],
            state["project_id"],
            state["edl"],
            state["assets"],
            state["poster_path"],
            state["audio"],
        )
        await events.emit("editor", "complete", "Final cut exported.", 91)
        return {"output": output}

    async def quality_check(state: CutlineState) -> dict[str, Any]:
        events = state["events"]
        await events.emit("qa_critic", "running", "Checking frames, duration, and audio…", 95)
        result = await asyncio.to_thread(
            verify_trailer, state["project_dir"] / "output" / "trailer.mp4"
        )
        if not result.valid:
            raise ProviderError("; ".join(result.errors))
        await events.emit("qa_critic", "complete", "Projection approved. Premiere is ready.", 100)
        return {}

    graph = StateGraph(CutlineState)
    graph.add_node("perceive", perceive)
    graph.add_node("screenwriter", write_edl)
    graph.add_node("poster", make_poster)
    graph.add_node("audio", make_audio)
    graph.add_node("editor", render_edit)
    graph.add_node("qa", quality_check)
    graph.add_edge(START, "perceive")
    graph.add_edge("perceive", "screenwriter")
    graph.add_edge("screenwriter", "poster")
    graph.add_edge("screenwriter", "audio")
    graph.add_edge("poster", "editor")
    graph.add_edge("audio", "editor")
    graph.add_edge("editor", "qa")
    graph.add_edge("qa", END)
    return graph.compile()
