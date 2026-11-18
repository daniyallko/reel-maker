import asyncio
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from app.providers.base import ProviderError
from app.schemas import CastCredit, CuratedAsset, EDLSegment, Genre, PerceptionResult, TrailerEDL, VibeProfile

GEMINI_MODEL = "gemini-3.5-flash-lite"
GEMINI_MODELS = (GEMINI_MODEL, "gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.1-flash-lite")


class GeminiCastCredit(BaseModel):
    name: str
    role: str
    asset_id: str | None = None


class GeminiEDLSegment(BaseModel):
    asset_id: str
    act: Literal["1", "2", "3"]
    start: float
    end: float
    ken_burns: Literal["zoom_in", "zoom_out", "pan_left", "pan_right"] = "zoom_in"
    title_card: str | None = None
    voiceover: str | None = None


class GeminiTrailerEDL(BaseModel):
    title: str
    tagline: str
    duration: float
    genre: Genre
    segments: list[GeminiEDLSegment]
    cast: list[GeminiCastCredit]
    beat_markers: list[float]


class GeminiProvider:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def perceive(
        self,
        assets: list[CuratedAsset],
        cast: list[str],
        notes: str,
        voice_path: Path | None,
    ) -> PerceptionResult:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            eligible = [asset for asset in assets if asset.rejection_reason is None]
            prompt = (
                "You are CUTLINE's Memory Curator and Voice & Vibe Analyst. "
                "Score every supplied asset ID from 1-10 for emotion, lighting, and action. "
                "Keep the strongest 8-10 shots and choose exactly one hero group shot. "
                "Transcribe the optional voice note, find the destination, inside jokes, and plot twists. "
                f"Cast: {cast}. Director notes: {notes or 'None'}. Asset IDs, in order: "
                + ", ".join(asset.id for asset in eligible)
            )
            contents: list = [prompt]
            for asset in eligible:
                for path in asset.keyframe_paths or ([asset.perception_path] if asset.perception_path else []):
                    contents.append(types.Part.from_text(text=f"Asset ID: {asset.id}"))
                    contents.append(
                        types.Part.from_bytes(data=path.read_bytes(), mime_type="image/jpeg")
                    )
            if voice_path:
                voice_mimes = {
                    ".webm": "audio/webm",
                    ".mp4": "audio/mp4",
                    ".mp3": "audio/mpeg",
                    ".ogg": "audio/ogg",
                    ".wav": "audio/wav",
                }
                contents.append(
                    types.Part.from_bytes(
                        data=voice_path.read_bytes(),
                        mime_type=voice_mimes.get(voice_path.suffix.lower(), "application/octet-stream"),
                    )
                )
            response = await self._generate(
                client,
                types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=PerceptionResult,
                ),
                contents,
            )
            return self._parsed(response, PerceptionResult)
        except Exception as error:
            raise ProviderError(f"Gemini perception failed: {error}") from error

    async def write(
        self,
        assets: list[CuratedAsset],
        vibe: VibeProfile,
        cast: list[str],
        genre: Genre,
        notes: str,
    ) -> TrailerEDL:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            kept = [asset for asset in assets if asset.kept]
            prompt = f"""
Create a strict three-act movie-trailer EDL for a {genre.value} weekend trip.
Duration must be 22 seconds. Segments must be contiguous from 0 to 22, use only these
asset IDs: {[asset.id for asset in kept]}, and include 8-10 shots. Assign zoom_in,
zoom_out, pan_left, or pan_right to each shot. Add brief dramatic title cards and
sparse voiceover. Give every cast member a funny cinematic role. Title and tagline
must feel specific to this destination and these jokes, not generic.
Vibe: {vibe.model_dump_json()}. Cast: {cast}. Notes: {notes}.
Use beat markers [0, 3, 6, 11, 14, 17, 20].
"""
            response = await self._generate(
                client,
                types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GeminiTrailerEDL,
                ),
                prompt,
            )
            return self._to_edl(self._parsed(response, GeminiTrailerEDL))
        except Exception as error:
            raise ProviderError(f"Gemini screenwriting failed: {error}") from error

    @staticmethod
    def _to_edl(parsed: GeminiTrailerEDL) -> TrailerEDL:
        return TrailerEDL(
            title=parsed.title,
            tagline=parsed.tagline,
            duration=parsed.duration,
            genre=parsed.genre,
            segments=[
                EDLSegment(
                    asset_id=segment.asset_id,
                    act=int(segment.act),
                    start=segment.start,
                    end=segment.end,
                    ken_burns=segment.ken_burns,
                    title_card=segment.title_card,
                    voiceover=segment.voiceover,
                )
                for segment in parsed.segments
            ],
            cast=[CastCredit(**credit.model_dump()) for credit in parsed.cast],
            beat_markers=parsed.beat_markers,
        )

    async def _generate(self, client, config, contents, timeout=90):
        last_error: Exception | None = None
        for model in GEMINI_MODELS:
            for attempt in range(3):
                try:
                    return await asyncio.wait_for(
                        asyncio.to_thread(
                            client.models.generate_content,
                            model=model,
                            contents=contents,
                            config=config,
                        ),
                        timeout=timeout,
                    )
                except Exception as error:
                    transient = isinstance(error, TimeoutError) or any(code in str(error) for code in ("429", "503", "UNAVAILABLE", "RESOURCE_EXHAUSTED"))
                    if not transient:
                        raise
                    last_error = error
                    if attempt < 2:
                        await asyncio.sleep(2 ** attempt)
        if last_error:
            raise last_error
        raise RuntimeError("Gemini retry loop exhausted")

    @staticmethod
    def _parsed(response, schema):
        parsed = getattr(response, "parsed", None)
        if parsed is None:
            parsed = schema.model_validate_json(response.text)
        return parsed
