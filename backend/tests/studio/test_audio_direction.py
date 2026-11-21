import io
import wave
from pathlib import Path

import pytest

from app.studio import audio
from app.studio.renderer import build_mix_command
from app.studio.timeline import retime_storyboard
from tests.studio.directed_fixtures import directed_storyboard


def _mix_command(tmp_path, storyboard):
    return build_mix_command(
        tmp_path,
        storyboard,
        tmp_path / "voice.wav",
        tmp_path / "music.wav",
        tmp_path / "captions.ass",
        tmp_path / "trailer.mp4",
    )


def _wav_bytes(duration: float = 0.1) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(48000)
        wav.writeframes(b"\x00\x00" * 2 * round(duration * 48000))
    return output.getvalue()


def test_every_style_selects_its_music():
    assert audio.music_for_style("launch").name == "action.wav"
    assert audio.music_for_style("tech_launch").name == "scifi.wav"
    assert audio.music_for_style("deep_dive").name == "indie.wav"
    assert audio.music_for_style("founder").name == "indie.wav"
    assert audio.music_for_style("roast").name == "comedy.wav"


@pytest.mark.asyncio
async def test_produce_audio_uses_storyboard_style_music(tmp_path):
    payloads = iter(_wav_bytes() for _ in directed_storyboard().scenes)

    async def tts_call(*_args):
        return next(payloads)

    result = await audio.produce_audio(directed_storyboard(), tmp_path, tts_call)

    assert result.music_path.name == "indie.wav"


def test_sfx_follow_retimed_scene_starts(tmp_path):
    storyboard = retime_storyboard(directed_storyboard(), [1.2, 3.5, 2.0, 4.5, 3.0, 2.2])
    command = _mix_command(tmp_path, storyboard)
    graph = next(part for part in command if "sidechaincompress" in part)
    for scene in storyboard.scenes:
        if scene.sfx != "none":
            delay = round(scene.start * 1000)
            assert f"adelay={delay}|{delay}" in graph
    assert "adelay=25000|25000" not in graph


def test_sfx_inputs_are_unique_and_none_cues_are_omitted(tmp_path):
    scenes = [scene.model_copy(update={"sfx": "none"}) for scene in directed_storyboard().scenes]
    scenes[0] = scenes[0].model_copy(update={"sfx": "whoosh"})
    scenes[1] = scenes[1].model_copy(update={"sfx": "whoosh"})
    scenes[2] = scenes[2].model_copy(update={"sfx": "bass_drop"})
    storyboard = directed_storyboard().model_copy(update={"scenes": scenes})

    command = _mix_command(tmp_path, storyboard)
    graph = next(part for part in command if "sidechaincompress" in part)
    inputs = [Path(command[index + 1]) for index, part in enumerate(command) if part == "-i"]

    assert [path.name for path in inputs[3:]] == ["whoosh.wav", "drop.wav"]
    assert graph.count("adelay=") == 3
    assert "[3:a]adelay=0|0,volume=0.35[sfx0]" in graph
    assert "[3:a]adelay=2000|2000,volume=0.35[sfx1]" in graph
    assert "[4:a]adelay=7000|7000,volume=0.45[sfx2]" in graph
    assert "amix=inputs=5:duration=first:normalize=0" in graph


def test_no_sfx_cues_mix_only_voice_and_music(tmp_path):
    storyboard = directed_storyboard().model_copy(
        update={
            "scenes": [scene.model_copy(update={"sfx": "none"}) for scene in directed_storyboard().scenes]
        }
    )

    command = _mix_command(tmp_path, storyboard)
    graph = next(part for part in command if "sidechaincompress" in part)

    assert command.count("-i") == 3
    assert "adelay=" not in graph
    assert "[ducked][vo]amix=inputs=2:duration=first:normalize=0" in graph
