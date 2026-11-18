from pathlib import Path
from typing import Protocol

from app.schemas import (
    AudioTimeline,
    CastCredit,
    CuratedAsset,
    Genre,
    PerceptionResult,
    PressKitOutput,
    TrailerEDL,
    VibeProfile,
)


class PerceptionProvider(Protocol):
    async def perceive(
        self,
        assets: list[CuratedAsset],
        cast: list[str],
        notes: str,
        voice_path: Path | None,
    ) -> PerceptionResult: ...


class ScreenwriterProvider(Protocol):
    async def write(
        self,
        assets: list[CuratedAsset],
        vibe: VibeProfile,
        cast: list[str],
        genre: Genre,
        notes: str,
    ) -> TrailerEDL: ...


class PosterProducer(Protocol):
    def render(
        self,
        project_dir: Path,
        project_id: str,
        edl: TrailerEDL,
        assets: list[CuratedAsset],
    ) -> Path: ...


class AudioProducerProtocol(Protocol):
    def render(
        self,
        project_dir: Path,
        edl: TrailerEDL,
        sample: bool = False,
    ) -> AudioTimeline: ...


class EditorProtocol(Protocol):
    def render(
        self,
        project_dir: Path,
        project_id: str,
        edl: TrailerEDL,
        assets: list[CuratedAsset],
        poster_path: Path,
        audio: AudioTimeline,
    ) -> PressKitOutput: ...


class ProviderError(RuntimeError):
    pass
