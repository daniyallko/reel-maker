import asyncio
from pathlib import Path

import pytest

from app.studio.providers import fallback_visuals, mock_storyboard
from app.studio.renderer import MotionRenderer
from app.studio.schemas import StudioAudio


@pytest.mark.asyncio
async def test_render_runs_ffmpeg_with_timeout(tmp_path: Path, monkeypatch):
    storyboard = mock_storyboard("launch", "Fenrir")
    assets = fallback_visuals(storyboard, None, tmp_path)
    audio = StudioAudio(voice_path=tmp_path / "voice.wav", music_path=tmp_path / "music.wav", captions_path=tmp_path / "captions.ass", preview_url="/preview", durations=[2.5, 9.5, 13, 7])
    calls = []
    class Result:
        returncode = 0
        stderr = ""
    def fake_run(*args, **kwargs):
        calls.append(kwargs)
        return Result()
    monkeypatch.setattr("app.studio.renderer.subprocess.run", fake_run)
    async def no_frames(*_):
        return None
    monkeypatch.setattr("app.studio.renderer.capture_motion_frames", no_frames)
    output = await MotionRenderer().render("<html></html>", storyboard, assets, audio, tmp_path, source_url="https://acme.example", quality_mode="draft", review_label="Unreviewed draft")
    assert output.duration == 32
    assert output.source_url == "https://acme.example"
    assert output.quality_mode == "draft"
    assert output.review_label == "Unreviewed draft"
    assert calls[0]["timeout"] == 600
