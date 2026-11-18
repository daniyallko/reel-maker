import json
import subprocess
from pathlib import Path


class MediaProbeError(RuntimeError):
    pass


def probe_media(path: Path) -> dict:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_format",
        "-show_streams",
        "-of",
        "json",
        str(path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise MediaProbeError(result.stderr.strip() or f"Could not inspect {path.name}")
    return json.loads(result.stdout)


def media_duration(path: Path) -> float:
    data = probe_media(path)
    duration = data.get("format", {}).get("duration")
    if duration is not None:
        return float(duration)
    streams = data.get("streams", [])
    return max((float(stream.get("duration", 0)) for stream in streams), default=0.0)
