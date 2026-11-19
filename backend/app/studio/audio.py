from pathlib import Path

import ffmpeg

from app.media.audio import AudioProducer
from app.media.probe import media_duration
from app.studio.schemas import Storyboard, StudioAudio

MUSIC = Path(__file__).resolve().parents[2] / "assets" / "music" / "comedy.wav"


def _fit_tempo(stream, ratio: float):
    remaining = ratio
    while remaining > 2:
        stream = stream.filter("atempo", 2)
        remaining /= 2
    return stream.filter("atempo", max(1, remaining))


async def produce_audio(storyboard: Storyboard, project_dir: Path, tts_call=None) -> StudioAudio:
    audio_dir = project_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    segment_paths: list[Path] = []
    durations: list[float] = []
    for index, scene in enumerate(storyboard.scenes):
        target = scene.end - scene.start
        path = audio_dir / f"scene-{index:02d}.wav"
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
        except Exception:
            AudioProducer._offline_voice(scene.narration, path, audio_dir / f"scene-{index:02d}.txt")
            measured = media_duration(path)
        if measured > target:
            adjusted = audio_dir / f"scene-{index:02d}-fit.wav"
            stream = ffmpeg.input(str(path)).audio
            stream = _fit_tempo(stream, measured / target)
            ffmpeg.output(stream, str(adjusted), ac=2, ar=48000).overwrite_output().run(
                capture_stdout=True, capture_stderr=True
            )
            path = adjusted
            measured = target
        segment_paths.append(path)
        durations.append(measured)

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
        voice_path=voice_path,
        music_path=MUSIC,
        captions_path=audio_dir / "captions.ass",
        preview_url=f"/media/{project_dir.name}/audio/narration.wav",
        durations=durations,
    )
