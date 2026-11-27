import math
import subprocess
from pathlib import Path

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
    inputs: list[str] = []
    filters: list[str] = []
    concat_labels: list[str] = []
    outputs: list[str] = []
    for index, (scene, source) in enumerate(zip(retimed.scenes, audio.segment_paths, strict=True)):
        target = scene.end - scene.start
        path = audio_dir / f"scene-{index:02d}-aligned.wav"
        aligned_paths.append(path)
        inputs.extend(["-i", str(source)])
        if len(retimed.scenes) == 1:
            filters.append(f"[{index}:a]aresample=48000,aformat=sample_fmts=s16:channel_layouts=stereo,apad,atrim=duration={target},asplit=2[a{index}][all]")
        else:
            filters.append(f"[{index}:a]aresample=48000,aformat=sample_fmts=s16:channel_layouts=stereo,apad,atrim=duration={target},asplit=2[a{index}][c{index}]")
            concat_labels.append(f"[c{index}]")
        outputs.extend(["-map", f"[a{index}]", "-ac", "2", "-ar", "48000", str(path)])

    voice_path = audio.voice_path
    voice_path.parent.mkdir(parents=True, exist_ok=True)
    if len(retimed.scenes) > 1:
        filters.append(f"{''.join(concat_labels)}concat=n={len(retimed.scenes)}:v=0:a=1[all]")
    command = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", ";".join(filters),
        *outputs,
        "-map", "[all]", "-ac", "2", "-ar", "48000", str(voice_path),
    ]
    subprocess.run(command, check=True, capture_output=True)
    return retimed, audio.model_copy(update={"voice_path": voice_path, "segment_paths": aligned_paths})
