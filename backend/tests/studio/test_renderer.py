from pathlib import Path

from app.studio.providers import mock_storyboard
from app.studio.renderer import (
    SAMPLE_OUTPUT,
    build_mix_command,
    frame_count,
    verify_studio_video,
    write_ass_captions,
)


def test_frame_count_is_30fps():
    assert frame_count(mock_storyboard("launch", "Fenrir")) == 960


def test_word_level_ass_captions(tmp_path: Path):
    storyboard = mock_storyboard("launch", "Fenrir")
    output = write_ass_captions(storyboard, [3, 11, 14, 7], tmp_path / "captions.ass")
    text = output.read_text()
    assert "Dialogue" in text
    assert "Your" in text
    assert "0:00:02.50" in text


def test_ffmpeg_mix_has_ducking_and_memory_limits(tmp_path: Path):
    storyboard = mock_storyboard("launch", "Fenrir")
    command = build_mix_command(tmp_path, storyboard, tmp_path / "voice.wav", tmp_path / "music.wav", tmp_path / "captions.ass", tmp_path / "trailer.mp4")
    assert any("sidechaincompress" in part for part in command)
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
