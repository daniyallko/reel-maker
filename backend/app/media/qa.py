import subprocess
from pathlib import Path

from app.media.probe import probe_media
from app.schemas import QAResult


def verify_trailer(path: Path) -> QAResult:
    errors: list[str] = []
    try:
        data = probe_media(path)
        video = next(stream for stream in data["streams"] if stream["codec_type"] == "video")
        duration = float(data["format"]["duration"])
        width, height = int(video["width"]), int(video["height"])
        has_audio = any(stream["codec_type"] == "audio" for stream in data["streams"])
        if not 20 <= duration <= 25:
            errors.append(f"Duration {duration:.2f}s is outside 20–25 seconds")
        if (width, height) != (1080, 1920):
            errors.append(f"Expected 1080×1920, received {width}×{height}")
        if not has_audio:
            errors.append("Audio stream is missing")
        decode = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"],
            capture_output=True,
            text=True,
        )
        if decode.returncode or decode.stderr.strip():
            errors.append(decode.stderr.strip() or "Frame decode failed")
    except (KeyError, StopIteration, ValueError, RuntimeError) as error:
        duration, width, height, has_audio = 0, 0, 0, False
        errors.append(str(error))
    return QAResult(
        valid=not errors,
        duration=duration,
        width=width,
        height=height,
        has_audio=has_audio,
        errors=errors,
    )
