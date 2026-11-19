from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator

from app.schemas import ProjectStatus


class StudioAsset(BaseModel):
    id: str
    kind: Literal["screenshot", "image", "video", "art", "thumbnail", "audio", "critique"]
    label: str
    url: str
    mime_type: str
    local_path: Path = Field(exclude=True)


class HarvestResult(BaseModel):
    source_url: str
    title: str
    palette: list[str]
    fonts: list[str]
    dom_copy: str
    assets: list[StudioAsset]
    screenshots: list[Path] = Field(default_factory=list, exclude=True)
    scroll_video: Path = Field(exclude=True)
    image_paths: list[Path] = Field(default_factory=list, exclude=True)


class SourceCitation(BaseModel):
    url: str
    title: str
    claim: str


class StoryScene(BaseModel):
    id: str
    start: float
    end: float
    headline: str
    narration: str
    visual_prompt: str
    source_refs: list[int] = Field(default_factory=list)


class Storyboard(BaseModel):
    title: str
    style: str
    voice: str
    duration: float = Field(ge=30, le=40)
    bpm: int = 128
    scenes: list[StoryScene]
    sources: list[SourceCitation]
    speech_style: str

    @model_validator(mode="after")
    def valid_timeline(self):
        if len(self.scenes) != 4:
            raise ValueError("Storyboard needs exactly four scenes")
        cursor = 0.0
        for scene in self.scenes:
            if abs(scene.start - cursor) > 0.05 or scene.end <= scene.start:
                raise ValueError("Scenes must be contiguous and increasing")
            cursor = scene.end
        if abs(cursor - self.duration) > 0.05:
            raise ValueError("Scenes must fill the storyboard duration")
        return self


class StudioAudio(BaseModel):
    voice_path: Path = Field(exclude=True)
    music_path: Path = Field(exclude=True)
    captions_path: Path = Field(exclude=True)
    preview_url: str
    durations: list[float]


class StudioOutput(BaseModel):
    title: str
    trailer_url: str
    thumbnail_url: str
    preview_url: str
    duration: float
    bpm: int
    scenes: list[StoryScene]
    sources: list[SourceCitation]
    script: str
    source_url: str | None = None
    style: str = "launch"
    voice: str = "Fenrir"
    critique_scores: dict[str, int] = Field(default_factory=dict)


class StudioProjectSnapshot(BaseModel):
    id: str
    status: ProjectStatus
    source_url: str
    style: str
    voice: str
    created_at: float
    assets: list[StudioAsset] = Field(default_factory=list)
    events: list = Field(default_factory=list)
    output: StudioOutput | None = None
    error: str | None = None
