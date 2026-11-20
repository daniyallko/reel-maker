import io
import wave
from pathlib import Path

import pytest

from app.media.probe import media_duration
from app.studio.audio import produce_audio
from app.studio.graph import build_studio_graph
from app.studio.schemas import StudioAudio
from app.studio.timeline import align_audio_timeline, retime_storyboard
from tests.studio.directed_fixtures import directed_storyboard

MEASURED = [1.2, 3.5, 2.0, 4.5, 3.0, 2.2]


def _wav_bytes(duration: float) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(48000)
        wav.writeframes(b"\x00\x00" * 2 * round(duration * 48000))
    return output.getvalue()


def _write_wav(path: Path, duration: float) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_wav_bytes(duration))
    return path


def test_retime_contains_measured_narration():
    storyboard = directed_storyboard()
    measured = [1.2, 3.5, 2.0, 4.5, 3.0, 2.2]
    retimed = retime_storyboard(storyboard, measured)
    assert retimed.duration == storyboard.duration == 32
    assert retimed.scenes[0].start == 0
    assert abs(retimed.scenes[-1].end - 32) < 0.001
    for scene, duration in zip(retimed.scenes, measured, strict=True):
        assert scene.end - scene.start >= duration
    for previous, current in zip(retimed.scenes, retimed.scenes[1:], strict=False):
        assert current.start == previous.end


def test_retime_distributes_remaining_hold_by_initial_scene_length():
    retimed = retime_storyboard(directed_storyboard(), MEASURED)
    durations = [scene.end - scene.start for scene in retimed.scenes]
    assert durations == pytest.approx([2.7375, 5.84375, 4.34375, 7.3125, 6.28125, 5.48125])


@pytest.mark.parametrize("measured", [MEASURED[:-1], [*MEASURED, 1.0]])
def test_retime_requires_one_measurement_per_scene(measured: list[float]):
    with pytest.raises(ValueError, match="one measured duration per scene"):
        retime_storyboard(directed_storyboard(), measured)


@pytest.mark.parametrize("invalid", [0.0, -0.1, float("nan"), float("inf"), float("-inf")])
def test_retime_rejects_invalid_measurements(invalid: float):
    measured = [*MEASURED]
    measured[2] = invalid
    with pytest.raises(ValueError, match="positive and finite"):
        retime_storyboard(directed_storyboard(), measured)


def test_retime_rejects_narration_longer_than_initial_slot():
    measured = [*MEASURED]
    measured[0] = 2.001
    with pytest.raises(ValueError, match="exceeds initial scene slot"):
        retime_storyboard(directed_storyboard(), measured)


def test_retime_supports_very_short_and_slot_filling_narration():
    measured = [0.01, 5.0, 5.0, 6.0, 7.0, 7.0]
    retimed = retime_storyboard(directed_storyboard(), measured)
    assert retimed.scenes[-1].end == pytest.approx(32)
    for scene, duration in zip(retimed.scenes, measured, strict=True):
        assert scene.end - scene.start >= 1.8
        assert scene.end - scene.start >= duration


def test_aligned_audio_matches_storyboard_duration(tmp_path: Path):
    storyboard = directed_storyboard()
    paths = [
        _write_wav(tmp_path / "audio" / f"source-{index}.wav", duration)
        for index, duration in enumerate(MEASURED)
    ]
    audio = StudioAudio(
        voice_path=tmp_path / "audio" / "narration.wav",
        music_path=tmp_path / "music.wav",
        captions_path=tmp_path / "audio" / "captions.ass",
        preview_url="/media/test/audio/narration.wav",
        durations=[*MEASURED],
        segment_paths=paths,
    )

    retimed, aligned = align_audio_timeline(storyboard, audio, tmp_path)

    assert media_duration(aligned.voice_path) == pytest.approx(32, abs=0.001)
    assert aligned.durations == MEASURED
    assert len(aligned.segment_paths) == len(retimed.scenes)
    for scene, path, narration_duration in zip(
        retimed.scenes, aligned.segment_paths, aligned.durations, strict=True
    ):
        assert path.exists()
        assert media_duration(path) == pytest.approx(scene.end - scene.start, abs=0.001)
        assert narration_duration <= scene.end - scene.start


@pytest.mark.asyncio
async def test_produce_audio_exposes_measured_segment_paths(tmp_path: Path):
    payloads = iter(_wav_bytes(duration) for duration in MEASURED)

    async def tts_call(*_args):
        return next(payloads)

    audio = await produce_audio(directed_storyboard(), tmp_path, tts_call)

    assert len(audio.segment_paths) == len(MEASURED)
    assert audio.durations == pytest.approx(MEASURED, abs=0.001)
    for path, duration in zip(audio.segment_paths, MEASURED, strict=True):
        assert path.exists()
        assert media_duration(path) == pytest.approx(duration, abs=0.001)


def test_timing_node_follows_visuals_and_audio_before_motion():
    graph = build_studio_graph(object(), object()).get_graph()
    edges = {(edge.source, edge.target) for edge in graph.edges}
    assert {("visuals", "timing"), ("audio", "timing"), ("timing", "motion")} <= edges
    assert ("visuals", "motion") not in edges
    assert ("audio", "motion") not in edges
