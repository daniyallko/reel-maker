from pathlib import Path

import pytest

from app.studio.providers import mock_storyboard
from app.studio.renderer import (
    SAMPLE_OUTPUT,
    build_mix_command,
    frame_count,
    is_light_color,
    verify_studio_video,
    write_ass_captions,
)
from app.studio.timeline import retime_storyboard
from tests.studio.directed_fixtures import directed_storyboard


def _ass_seconds(timestamp: str) -> float:
    hours, minutes, seconds = timestamp.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def test_frame_count_is_30fps():
    assert frame_count(mock_storyboard("launch", "Fenrir")) == 960


def test_word_level_ass_captions(tmp_path: Path):
    measured = [1.2, 4.0, 5.0, 2.0]
    storyboard = retime_storyboard(mock_storyboard("launch", "Fenrir"), measured)
    output = write_ass_captions(storyboard, measured, tmp_path / "captions.ass")
    text = output.read_text()
    assert "Dialogue" in text
    assert "Your" in text
    assert "0:00:03.30" in text

    events = []
    for line in text.splitlines():
        if line.startswith("Dialogue:"):
            fields = line.split(",", 9)
            events.append((_ass_seconds(fields[1]), _ass_seconds(fields[2]), fields[9]))

    cursor = 0
    for index, scene in enumerate(storyboard.scenes):
        words = scene.narration.split()
        scene_events = events[cursor:cursor + len(words)]
        cursor += len(words)
        assert [event[2] for event in scene_events] == words
        assert scene_events[0][0] == pytest.approx(scene.start, abs=0.0051)
        narration_end = scene.start + measured[index]
        for start, end, _word in scene_events:
            assert start >= scene.start - 0.0051
            assert end >= start
            assert end <= narration_end
            assert end <= scene.end
    assert cursor == len(events)


def test_caption_events_stay_inside_non_centisecond_scene_bounds(tmp_path: Path):
    measured = [1.2, 3.5, 2.0, 4.5, 3.0, 2.2]
    storyboard = retime_storyboard(directed_storyboard(), measured)
    assert storyboard.scenes[1].start == pytest.approx(2.7375)
    output = write_ass_captions(storyboard, measured, tmp_path / "captions.ass")

    events = []
    for line in output.read_text().splitlines():
        if line.startswith("Dialogue:"):
            fields = line.split(",", 9)
            events.append((_ass_seconds(fields[1]), _ass_seconds(fields[2]), fields[9]))

    cursor = 0
    for index, scene in enumerate(storyboard.scenes):
        words = scene.narration.split()
        scene_events = events[cursor:cursor + len(words)]
        cursor += len(words)
        assert [event[2] for event in scene_events] == words
        narration_end = min(scene.end, scene.start + measured[index])
        for start, end, _word in scene_events:
            assert start >= scene.start
            assert end <= narration_end
            assert end <= scene.end
            assert start < end
    assert events[len(storyboard.scenes[0].narration.split())][0] == 2.74
    assert cursor == len(events)


def test_ffmpeg_mix_has_ducking_and_memory_limits(tmp_path: Path):
    storyboard = mock_storyboard("launch", "Fenrir")
    command = build_mix_command(tmp_path, storyboard, tmp_path / "voice.wav", tmp_path / "music.wav", tmp_path / "captions.ass", tmp_path / "trailer.mp4")
    graph = next(part for part in command if "sidechaincompress" in part)
    assert "sidechaincompress" in graph
    assert "loudnorm=I=-16:TP=-1.5:LRA=11" in graph
    assert "amix=inputs=5:duration=first:normalize=0" in graph
    assert command[command.index("-threads") + 1] == "2"
    assert command[command.index("-filter_complex_threads") + 1] == "1"
    assert any("whoosh" in part for part in command)
    assert any("pop" in part for part in command)
    assert any("drop" in part for part in command)
    assert "MarginV" not in command[-1]


def test_prebaked_sample_media_qa():
    result = verify_studio_video(SAMPLE_OUTPUT / "trailer.mp4")
    assert result.valid, result.errors
    assert 30 <= result.duration <= 40
    assert (SAMPLE_OUTPUT / "visuals" / "thumbnail-03.png").exists()


def test_video_qa_rejects_wrong_streams_and_duration(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("app.studio.renderer.probe_media", lambda _: {
        "format": {"duration": "32.0"},
        "streams": [
            {"codec_type": "video", "codec_name": "vp9", "width": 1080, "height": 1920, "r_frame_rate": "24/1", "duration": "32.0"},
            {"codec_type": "audio", "codec_name": "mp3", "duration": "31.8"},
        ],
    })
    class Result:
        def __init__(self, stderr):
            self.returncode = 0
            self.stderr = stderr
    monkeypatch.setattr("app.studio.renderer.subprocess.run", lambda *args, **__: Result("mean_volume: -16.0 dB" if "volumedetect" in args[0] else ""))
    result = verify_studio_video(tmp_path / "bad.mp4")
    assert not result.valid
    assert "Expected H.264 video, received vp9" in result.errors
    assert "Expected 30fps video, received 24/1" in result.errors
    assert "Expected AAC audio, received mp3" in result.errors
    assert "Audio/video duration mismatch: 0.20s" in result.errors


def test_adaptive_caption_style_switches_for_light_backgrounds(tmp_path: Path):
    assert is_light_color("#f2efe7") is True
    assert is_light_color("#0e1117") is False
    measured = [1.2, 4.0, 5.0, 2.0]
    storyboard = retime_storyboard(mock_storyboard("launch", "Fenrir"), measured)
    light_ass = write_ass_captions(storyboard, measured, tmp_path / "light.ass", light_bg=True).read_text()
    dark_ass = write_ass_captions(storyboard, measured, tmp_path / "dark.ass", light_bg=False).read_text()
    assert "&H001C1B18" in light_ass
    assert "&H00FFFFFF" in dark_ass


def test_video_qa_rejects_silent_audio(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("app.studio.renderer.probe_media", lambda _: {
        "format": {"duration": "32.0"},
        "streams": [
            {"codec_type": "video", "codec_name": "h264", "width": 1080, "height": 1920, "r_frame_rate": "30/1", "duration": "32.0"},
            {"codec_type": "audio", "codec_name": "aac", "duration": "32.0"},
        ],
    })
    class Result:
        def __init__(self, stderr):
            self.returncode = 0
            self.stderr = stderr
    monkeypatch.setattr("app.studio.renderer.subprocess.run", lambda *args, **__: Result("mean_volume: -91.0 dB" if "volumedetect" in args[0] else ""))
    result = verify_studio_video(tmp_path / "silent.mp4")
    assert not result.valid
    assert "Audio is silent or below -50 dB" in result.errors
