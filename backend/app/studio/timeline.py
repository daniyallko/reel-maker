import math
from pathlib import Path

import ffmpeg

from app.studio.schemas import Storyboard, StudioAudio

MIN_SCENE_DURATION = 1.8


def retime_storyboard(storyboard: Storyboard, measured: list[float]) -> Storyboard:
    if len(measured) != len(storyboard.scenes):
        raise ValueError("Expected one measured duration per scene")

    initial_lengths = [scene.end - scene.start for scene in storyboard.scenes]
    for duration, initial_length in zip(measured, initial_lengths, strict=True):
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError("Measured narration durations must be positive and finite")
        if duration > initial_length:
            raise ValueError("Measured narration exceeds initial scene slot")

    lengths = [max(MIN_SCENE_DURATION, duration) for duration in measured]
    remaining = storyboard.duration - sum(lengths)
    if remaining < 0:
        raise ValueError("Measured narration and minimum scene durations exceed storyboard duration")
    initial_total = sum(initial_lengths)
    lengths = [
        length + remaining * initial_length / initial_total
        for length, initial_length in zip(lengths, initial_lengths, strict=True)
    ]

    scenes = []
    cursor = 0.0
    for index, (scene, length) in enumerate(zip(storyboard.scenes, lengths, strict=True)):
        end = storyboard.duration if index == len(lengths) - 1 else cursor + length
        scenes.append(scene.model_copy(update={"start": cursor, "end": end}))
        cursor = end
    return storyboard.model_copy(update={"scenes": scenes})


def align_audio_timeline(
    storyboard: Storyboard, audio: StudioAudio, project_dir: Path
) -> tuple[Storyboard, StudioAudio]:
    retimed = retime_storyboard(storyboard, audio.durations)
    if len(audio.segment_paths) != len(retimed.scenes):
        raise ValueError("Expected one narration segment per scene")

    audio_dir = project_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    aligned_paths: list[Path] = []
    for index, (scene, source) in enumerate(zip(retimed.scenes, audio.segment_paths, strict=True)):
        target = scene.end - scene.start
        path = audio_dir / f"scene-{index:02d}-aligned.wav"
        stream = ffmpeg.input(str(source)).audio.filter("aresample", 48000)
        stream = stream.filter("apad").filter("atrim", duration=target)
        ffmpeg.output(stream, str(path), ac=2, ar=48000).overwrite_output().run(
            capture_stdout=True, capture_stderr=True
        )
        aligned_paths.append(path)

    voice_path = audio.voice_path
    voice_path.parent.mkdir(parents=True, exist_ok=True)
    streams = [ffmpeg.input(str(path)).audio for path in aligned_paths]
    ffmpeg.concat(*streams, v=0, a=1).output(str(voice_path), ac=2, ar=48000).overwrite_output().run(
        capture_stdout=True, capture_stderr=True
    )
    return retimed, audio.model_copy(update={"voice_path": voice_path, "segment_paths": aligned_paths})
