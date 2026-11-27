from pathlib import Path

import ffmpeg

from app.media.audio import AudioProducer
from app.media.probe import media_duration
from app.studio.schemas import Storyboard, StudioAudio

MUSIC_DIR = Path(__file__).resolve().parents[2] / "assets" / "music"
MUSIC_BY_STYLE = {
    "launch": "action.wav",
    "tech_launch": "scifi.wav",
    "deep_dive": "indie.wav",
    "founder": "indie.wav",
    "roast": "comedy.wav",
}


def music_for_style(style: str) -> Path:
    return MUSIC_DIR / MUSIC_BY_STYLE[style]


class NarrationOverrun(ValueError):
    def __init__(self, index, measured, target):
        self.index = index
        self.ratio = measured / target
        super().__init__(f"Narration for shot {index + 1} lasts {measured:.1f}s in a {target:.1f}s slot.")


def _fit_tempo(stream, ratio: float):
    remaining = ratio
    while remaining > 2:
        stream = stream.filter("atempo", 2)
        remaining /= 2
    return stream.filter("atempo", max(1, remaining))


async def _synthesize_scene(index: int, scene, storyboard: Storyboard, audio_dir: Path, tts_call, narration_voice: str | None, strict_voice: bool) -> tuple[Path, float, str | None]:
    target = scene.end - scene.start
    path = audio_dir / f"scene-{index:02d}.wav"
    voice_label = None
    try:
        if tts_call is None:
            raise RuntimeError("Offline narration")
        payload = await tts_call(scene.narration, storyboard.voice, storyboard.speech_style)
        if not payload:
            raise RuntimeError("TTS returned no audio")
        path.write_bytes(payload)
        measured = media_duration(path)
        if measured <= 0:
            raise RuntimeError("TTS duration is zero")
        if narration_voice:
            voice_label = narration_voice
    except Exception:
        if strict_voice:
            raise
        voice_label = "Flite · offline preview"
        AudioProducer._offline_voice(scene.narration, path, audio_dir / f"scene-{index:02d}.txt")
        measured = media_duration(path)
    if measured > target:
        if storyboard.directed_motion and measured > target * 1.10:
            raise NarrationOverrun(index, measured, target)
        adjusted = audio_dir / f"scene-{index:02d}-fit.wav"
        stream = ffmpeg.input(str(path)).audio
        stream = _fit_tempo(stream, measured / target)
        ffmpeg.output(stream, str(adjusted), ac=2, ar=48000).overwrite_output().run(
            capture_stdout=True, capture_stderr=True
        )
        path = adjusted
        measured = target
    return path, measured, voice_label


async def produce_audio(storyboard: Storyboard, project_dir: Path, tts_call=None, narration_voice=None, strict_voice=False) -> StudioAudio:
    import asyncio
    audio_dir = project_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    results = await asyncio.gather(*(
        _synthesize_scene(index, scene, storyboard, audio_dir, tts_call, narration_voice, strict_voice)
        for index, scene in enumerate(storyboard.scenes)
    ))
    segment_paths = [item[0] for item in results]
    durations = [item[1] for item in results]
    voices = {item[2] for item in results if item[2]}

    voice_path = audio_dir / "narration.wav"
    if len(segment_paths) == 1:
        ffmpeg.output(ffmpeg.input(str(segment_paths[0])).audio, str(voice_path), ac=2, ar=48000).overwrite_output().run(
            capture_stdout=True, capture_stderr=True
        )
    else:
        streams = [ffmpeg.input(str(path)).audio for path in segment_paths]
        ffmpeg.concat(*streams, v=0, a=1).output(str(voice_path), ac=2, ar=48000).overwrite_output().run(
            capture_stdout=True, capture_stderr=True
        )
    return StudioAudio(
        narration_voice=" / ".join(sorted(voices)) or None,
        voice_path=voice_path,
        music_path=music_for_style(storyboard.style),
        captions_path=audio_dir / "captions.ass",
        preview_url=f"/media/{project_dir.name}/audio/narration.wav",
        durations=durations,
        segment_paths=segment_paths,
    )
