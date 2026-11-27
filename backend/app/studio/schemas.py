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


class SourceCitation(BaseModel):
    url: str
    title: str
    claim: str
    content: str = Field(default="", exclude=True)


class SourceBundle(BaseModel):
    kind: Literal["url", "text", "mixed", "sample"] = "url"
    title: str
    source_url: str
    dom_copy: str
    palette: list[str]
    fonts: list[str]
    assets: list[StudioAsset]
    citations: list[SourceCitation] = Field(default_factory=list)
    screenshots: list[Path] = Field(default_factory=list, exclude=True)
    scroll_video: Path = Field(exclude=True)
    image_paths: list[Path] = Field(default_factory=list, exclude=True)


class ResearchPlan(BaseModel):
    topic: str
    angle: str
    queries: list[str] = Field(min_length=1, max_length=4)


class EvidenceClaim(BaseModel):
    text: str
    source_refs: list[int]


class ResearchReport(BaseModel):
    topic: str
    angle: str
    summary: str
    claims: list[EvidenceClaim]
    sources: list[SourceCitation]
    queries: list[str]
    external_research: bool
    provider: str

    @model_validator(mode="after")
    def valid_claim_references(self):
        for claim in self.claims:
            if any(ref < 0 or ref >= len(self.sources) for ref in claim.source_refs):
                raise ValueError("Claim source_refs must reference the report sources")
        return self


HarvestResult = SourceBundle


class SceneMetric(BaseModel):
    label: str
    value: float
    display: str


class StoryScene(BaseModel):
    tone: Literal["neutral", "curious", "measured", "building", "reflective"] = "neutral"
    delivery: str = ""
    id: str
    start: float
    end: float
    headline: str = Field(max_length=42)
    narration: str
    visual_prompt: str
    source_refs: list[int] = Field(default_factory=list)
    visual_type: Literal[
        "screenshot",
        "source_image",
        "generated_art",
        "kinetic_type",
        "diagram",
        "data",
    ] = "generated_art"
    layout: Literal["hero", "split", "bento", "full_bleed"] = "hero"
    camera: Literal["push_in", "pull_out", "pan_left", "pan_right", "static"] = "push_in"
    animation: Literal["clip_reveal", "stagger", "counter_roll", "path_draw", "parallax"] = "clip_reveal"
    transition: Literal["cut", "wipe", "whip", "dissolve"] = "cut"
    sfx: Literal["whoosh", "pop", "bass_drop", "none"] = "none"
    callouts: list[str] = Field(default_factory=list, max_length=4)
    metrics: list[SceneMetric] = Field(default_factory=list, max_length=3)

    @model_validator(mode="after")
    def valid_visual_payload(self):
        if self.visual_type == "diagram" and len(self.callouts) < 2:
            raise ValueError("Diagram scenes need at least two callouts")
        if self.visual_type == "data" and not self.metrics:
            raise ValueError("Data scenes need metrics")
        return self


class Storyboard(BaseModel):
    directed_motion: bool = False
    title: str
    style: str
    voice: str
    duration: float = Field(ge=30, le=40)
    bpm: int = Field(default=128, gt=0)
    scenes: list[StoryScene] = Field(min_length=4, max_length=8)
    sources: list[SourceCitation]
    speech_style: str

    @model_validator(mode="after")
    def valid_timeline(self):
        ids = [scene.id for scene in self.scenes]
        if len(ids) != len(set(ids)):
            raise ValueError("Scene IDs must be unique")
        cursor = 0.0
        for scene in self.scenes:
            if abs(scene.start - cursor) > 0.05 or scene.end <= scene.start:
                raise ValueError("Scenes must be contiguous and increasing")
            if scene.end - scene.start < 1.8:
                raise ValueError("Scenes must last at least 1.8 seconds")
            if not scene.source_refs or any(ref < 0 or ref >= len(self.sources) for ref in scene.source_refs):
                raise ValueError("Every scene needs valid source_refs")
            cursor = scene.end
        if abs(cursor - self.duration) > 0.05:
            raise ValueError("Scenes must fill the storyboard duration")
        return self


class StudioAudio(BaseModel):
    narration_voice: str | None = None
    voice_path: Path = Field(exclude=True)
    music_path: Path = Field(exclude=True)
    captions_path: Path = Field(exclude=True)
    preview_url: str
    durations: list[float]
    segment_paths: list[Path] = Field(default_factory=list, exclude=True)


class StudioOutput(BaseModel):
    narration_voice: str | None = None
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
    quality_mode: Literal["strict", "draft"] = "strict"
    review_label: str | None = None
    critique_scores: dict[str, int] = Field(default_factory=dict)


class StudioProjectSnapshot(BaseModel):
    id: str
    status: ProjectStatus
    source_url: str
    source_title: str = ""
    style: str
    voice: str
    quality_mode: Literal["strict", "draft"] = "strict"
    created_at: float
    assets: list[StudioAsset] = Field(default_factory=list)
    events: list = Field(default_factory=list)
    output: StudioOutput | None = None
    error: str | None = None
