from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class AssetKind(StrEnum):
    PHOTO = "photo"
    VIDEO = "video"


class AssetStatus(StrEnum):
    PENDING = "pending"
    KEPT = "kept"
    REJECTED = "rejected"


class Genre(StrEnum):
    ACTION = "action"
    INDIE = "indie"
    COMEDY = "comedy"
    SCIFI = "scifi"


class ProjectStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class AssetInput(BaseModel):
    filename: str
    content_type: str
    path: Path
    size: int


class CuratedAsset(BaseModel):
    id: str
    filename: str
    kind: AssetKind
    status: AssetStatus = AssetStatus.PENDING
    score: float = 0
    emotion: int = 0
    lighting: int = 0
    action: int = 0
    kept: bool = False
    hero: bool = False
    rejection_reason: str | None = None
    url: str = ""
    thumbnail_url: str = ""
    duration: float | None = None
    width: int | None = None
    height: int | None = None
    source_path: Path = Field(exclude=True)
    perception_path: Path | None = Field(default=None, exclude=True)
    thumbnail_path: Path | None = Field(default=None, exclude=True)
    keyframe_paths: list[Path] = Field(default_factory=list, exclude=True)


class VibeProfile(BaseModel):
    transcript: str = ""
    destination: str = "Somewhere off the map"
    inside_jokes: list[str] = Field(default_factory=list)
    plot_twists: list[str] = Field(default_factory=list)
    energy: str = "chaotic"


class CastCredit(BaseModel):
    name: str
    role: str
    asset_id: str | None = None
    card_url: str | None = None
    card_path: Path | None = Field(default=None, exclude=True)


class EDLSegment(BaseModel):
    asset_id: str
    act: Literal[1, 2, 3]
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    ken_burns: Literal["zoom_in", "zoom_out", "pan_left", "pan_right"] = "zoom_in"
    title_card: str | None = None
    voiceover: str | None = None

    @model_validator(mode="after")
    def valid_range(self):
        if self.end <= self.start:
            raise ValueError("Segment end must be after its start")
        return self


class TrailerEDL(BaseModel):
    title: str
    tagline: str
    duration: float = Field(ge=20, le=25)
    genre: Genre
    segments: list[EDLSegment]
    cast: list[CastCredit]
    beat_markers: list[float] = Field(default_factory=list)

    @model_validator(mode="after")
    def coherent_timeline(self):
        ordered = sorted(self.segments, key=lambda segment: segment.start)
        if not ordered:
            raise ValueError("EDL needs at least one segment")
        cursor = 0.0
        for segment in ordered:
            if abs(segment.start - cursor) > 0.05:
                raise ValueError("EDL segments must be contiguous")
            cursor = segment.end
        if abs(cursor - self.duration) > 0.05:
            raise ValueError("EDL segments must fill the declared duration")
        return self


class AgentStatusEvent(BaseModel):
    id: int = 0
    project_id: str
    agent: str
    status: Literal["pending", "running", "complete", "failed"]
    message: str
    progress: float = Field(ge=0, le=100)
    timestamp: float
    assets: list[Any] | None = None
    payload: dict | None = None


class PressKitOutput(BaseModel):
    trailer_url: str
    poster_url: str
    cast_cards: list[CastCredit]
    edl: TrailerEDL
    duration: float
    beat_markers: list[float]


class ProjectSnapshot(BaseModel):
    id: str
    status: ProjectStatus
    genre: Genre
    created_at: float
    assets: list[CuratedAsset] = Field(default_factory=list)
    events: list[AgentStatusEvent] = Field(default_factory=list)
    output: PressKitOutput | None = None
    error: str | None = None


class AssetScore(BaseModel):
    id: str
    score: float = Field(ge=1, le=10)
    emotion: int = Field(ge=1, le=10)
    lighting: int = Field(ge=1, le=10)
    action: int = Field(ge=1, le=10)
    kept: bool
    hero: bool = False
    rejection_reason: str | None = None


class PerceptionResult(BaseModel):
    assets: list[AssetScore]
    vibe: VibeProfile

    @field_validator("assets")
    @classmethod
    def one_hero(cls, assets: list[AssetScore]):
        if sum(asset.hero for asset in assets) > 1:
            raise ValueError("Only one hero shot is allowed")
        return assets


class VoiceCue(BaseModel):
    start: float
    end: float
    text: str


class AudioTimeline(BaseModel):
    voice_path: Path = Field(exclude=True)
    music_path: Path = Field(exclude=True)
    cues: list[VoiceCue]


class QAResult(BaseModel):
    valid: bool
    duration: float
    width: int
    height: int
    has_audio: bool
    errors: list[str] = Field(default_factory=list)
