import asyncio
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from app.media.audio import AudioProducer
from app.media.qa import verify_trailer
from app.media.text import fit_text, load_font, wrap_to_width
from app.providers.mock import MockScreenwriterProvider
from app.schemas import VibeProfile


def test_long_unbroken_text_is_split_and_measured():
    image = Image.new("RGB", (800, 400))
    draw = ImageDraw.Draw(image)
    font = load_font(48)
    lines = wrap_to_width(draw, "SUPERCALIFRAGILISTICEXPIALIDOCIOUS", font, 240)
    assert len(lines) > 1
    assert all(draw.textbbox((0, 0), line, font=font)[2] <= 240 for line in lines)
    _, fitted = fit_text(draw, "A VERY LONG TITLE FOR A VERTICAL POSTER", 300, 100, 30, 2)
    assert len(fitted) <= 2


def test_sample_trailer_passes_media_qa():
    trailer = Path(__file__).parents[1] / "assets" / "sample" / "output" / "trailer.mp4"
    result = verify_trailer(trailer)
    assert result.valid, result.errors
    assert (result.width, result.height) == (1080, 1920)
    assert result.has_audio
    assert 20 <= result.duration <= 25


def test_edge_tts_failure_uses_offline_narration(curated_asset, tmp_path, monkeypatch):
    async def scenario():
        edl = await MockScreenwriterProvider().write(
            [curated_asset],
            VibeProfile(destination="Testville"),
            ["Maya"],
            "comedy",
            "A joke",
        )
        def fail(*_):
            raise RuntimeError("Network unavailable")
        monkeypatch.setattr(AudioProducer, "_neural_voice", staticmethod(fail))
        timeline = AudioProducer().render(tmp_path, edl, sample=False)
        assert timeline.cues
        assert timeline.voice_path.exists()
        assert timeline.voice_path.stat().st_size > 0
    asyncio.run(scenario())
