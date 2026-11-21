import subprocess
from pathlib import Path

import asyncio
import hashlib
import math
import re

from playwright.async_api import async_playwright

from app.media.probe import probe_media
from app.schemas import QAResult
from app.studio.schemas import Storyboard, StudioAsset, StudioAudio, StudioOutput
from app.studio.urls import configure_offline_page, localize_motion_html

SAMPLE_OUTPUT = Path(__file__).resolve().parents[2] / "assets" / "link2reel" / "sample-output"


def frame_count(storyboard: Storyboard, fps: int = 30) -> int:
    return round(storyboard.duration * fps)


def ass_time(seconds: float) -> str:
    return _ass_time_from_centiseconds(max(0, round(seconds * 100)))


def _ass_time_from_centiseconds(centiseconds: int) -> str:
    hours, remainder = divmod(centiseconds, 360000)
    minutes, remainder = divmod(remainder, 6000)
    seconds, centiseconds = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"


def write_ass_captions(storyboard: Storyboard, durations: list[float], output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Default,Liberation Sans Narrow,64,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,0,2,50,50,240,0",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for index, scene in enumerate(storyboard.scenes):
        words = scene.narration.split()
        total_characters = max(1, sum(max(1, len(word)) for word in words))
        cursor = scene.start
        scene_duration = max(0.0, durations[index]) if index < len(durations) else scene.end - scene.start
        narration_end = min(scene.end, scene.start + scene_duration)
        scene_start_cs = max(0, math.ceil(scene.start * 100 - 1e-9))
        narration_end_cs = max(scene_start_cs, math.floor(narration_end * 100 + 1e-9))
        for word in words:
            duration = scene_duration * max(1, len(word)) / total_characters
            end = min(narration_end, cursor + duration)
            if narration_end_cs > scene_start_cs:
                start_cs = min(
                    narration_end_cs - 1,
                    max(scene_start_cs, round(cursor * 100)),
                )
                end_cs = max(
                    start_cs + 1,
                    min(narration_end_cs, math.floor(end * 100 + 1e-9)),
                )
                lines.append(
                    f"Dialogue: 0,{_ass_time_from_centiseconds(start_cs)},{_ass_time_from_centiseconds(end_cs)},Default,,0,0,0,,{word}"
                )
            cursor = end
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def build_mix_command(project_dir: Path, storyboard: Storyboard, voice: Path, music: Path, captions: Path, output: Path) -> list[str]:
    frames = project_dir / "frames" / "frame-%06d.png"
    subtitle_path = str(captions).replace(":", "\\:").replace("'", "\\'")
    sfx_dir = Path(__file__).resolve().parents[2] / "assets" / "music" / "sfx"
    sfx_files = {
        "whoosh": ("whoosh.wav", 0.35),
        "pop": ("pop.wav", 0.35),
        "bass_drop": ("drop.wav", 0.45),
    }
    sfx_inputs = []
    sfx_input_indexes = {}
    sfx_filters = []
    mix_inputs = ["[ducked]", "[vo]"]
    for scene in storyboard.scenes:
        if scene.sfx == "none":
            continue
        if scene.sfx not in sfx_input_indexes:
            sfx_input_indexes[scene.sfx] = len(sfx_inputs) + 3
            sfx_inputs.append(sfx_dir / sfx_files[scene.sfx][0])
        input_index = sfx_input_indexes[scene.sfx]
        delay = round(scene.start * 1000)
        label = f"sfx{len(sfx_filters)}"
        volume = sfx_files[scene.sfx][1]
        sfx_filters.append(f"[{input_index}:a]adelay={delay}|{delay},volume={volume}[{label}]")
        mix_inputs.append(f"[{label}]")
    filter_graph = ";".join([
        f"[1:a]aresample=48000,apad,atrim=0:{storyboard.duration},asplit=2[vo][sc]",
        f"[2:a]aloop=loop=-1:size=48000*22,atrim=0:{storyboard.duration},volume=0.42[music]",
        "[music][sc]sidechaincompress=threshold=0.025:ratio=8:attack=20:release=350[ducked]",
        *sfx_filters,
        f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:duration=first:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11[aout]",
        f"[0:v]subtitles='{subtitle_path}'[vout]",
    ])
    sfx_args = [argument for path in sfx_inputs for argument in ("-i", str(path))]
    return [
        "ffmpeg", "-y",
        "-framerate", "30", "-i", str(frames),
        "-i", str(voice), "-i", str(music),
        *sfx_args,
        "-filter_complex_threads", "1", "-filter_complex", filter_graph,
        "-map", "[vout]", "-map", "[aout]",
        "-t", str(storyboard.duration), "-r", "30",
        "-c:v", "libx264", "-threads", "2", "-preset", "veryfast", "-crf", "22",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart", str(output),
    ]


async def capture_motion_frames(html: str, project_dir: Path, storyboard: Storyboard) -> Path:
    frames_dir = project_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.sha256(html.encode("utf-8")).hexdigest()
    marker = frames_dir / ".cache-key"
    if marker.exists() and marker.read_text() == cache_key and len(list(frames_dir.glob("frame-*.png"))) == frame_count(storyboard):
        return frames_dir
    for path in frames_dir.glob("frame-*.png"):
        path.unlink()
    marker.write_text(cache_key)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page(viewport={"width": 1080, "height": 1920})
        server = await configure_offline_page(page, project_dir)
        await page.set_content(localize_motion_html(html, project_dir, server.base_url), wait_until="load")
        for index in range(frame_count(storyboard)):
            timestamp = index / 30
            await page.evaluate(f"window.seekTo({timestamp})")
            await page.screenshot(path=str(frames_dir / f"frame-{index + 1:06d}.png"))
        await browser.close()
        server.close()
    return frames_dir


class MotionRenderer:
    async def render(self, html: str, storyboard: Storyboard, assets: list[StudioAsset], audio: StudioAudio, project_dir: Path, output_dir: Path | None = None, source_url: str | None = None, critique_scores: dict[str, int] | None = None, quality_mode: str = "strict", review_label: str | None = None) -> StudioOutput:
        await capture_motion_frames(html, project_dir, storyboard)
        write_ass_captions(storyboard, audio.durations, audio.captions_path)
        output_path = (output_dir or project_dir / "output") / "trailer.mp4"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        command = build_mix_command(project_dir, storyboard, audio.voice_path, audio.music_path, audio.captions_path, output_path)
        result = await asyncio.to_thread(subprocess.run, command, capture_output=True, text=True, timeout=600)
        if result.returncode:
            raise RuntimeError(result.stderr[-5000:])
        thumbnail = next((asset for asset in assets if asset.kind == "thumbnail"), assets[-1])
        script = "\n\n".join(f"{scene.headline}\n{scene.narration}" for scene in storyboard.scenes)
        output = StudioOutput(
            title=storyboard.title,
            trailer_url=f"/media/{project_dir.name}/{output_path.relative_to(project_dir)}",
            thumbnail_url=thumbnail.url,
            preview_url=audio.preview_url,
            duration=storyboard.duration,
            bpm=storyboard.bpm,
            scenes=storyboard.scenes,
            sources=storyboard.sources,
            script=script,
            source_url=source_url or (storyboard.sources[0].url if storyboard.sources else None),
            style=storyboard.style,
            voice=storyboard.voice,
            quality_mode=quality_mode,
            review_label=review_label,
            critique_scores=critique_scores or {},
        )
        (output_path.parent / "studio-output.json").write_text(output.model_dump_json(indent=2), encoding="utf-8")
        return output


def verify_studio_video(path: Path) -> QAResult:
    errors: list[str] = []
    duration = width = height = 0
    has_audio = False
    try:
        data = probe_media(path)
        video = next(stream for stream in data["streams"] if stream["codec_type"] == "video")
        audio = next((stream for stream in data["streams"] if stream["codec_type"] == "audio"), None)
        duration = float(data["format"]["duration"])
        width, height = int(video["width"]), int(video["height"])
        has_audio = audio is not None
        if not 30 <= duration <= 40:
            errors.append(f"Duration {duration:.2f}s is outside 30–40 seconds")
        if (width, height) != (1080, 1920):
            errors.append(f"Expected 1080×1920, received {width}×{height}")
        if video.get("codec_name") != "h264":
            errors.append(f"Expected H.264 video, received {video.get('codec_name')}")
        frame_rate = video.get("r_frame_rate", "0/1")
        numerator, denominator = (int(part) for part in frame_rate.split("/", 1))
        if denominator == 0 or numerator / denominator != 30:
            errors.append(f"Expected 30fps video, received {frame_rate}")
        if not has_audio:
            errors.append("Audio stream is missing")
        else:
            if audio.get("codec_name") != "aac":
                errors.append(f"Expected AAC audio, received {audio.get('codec_name')}")
            audio_duration = float(audio.get("duration", duration))
            if abs(audio_duration - duration) > 0.1:
                errors.append(f"Audio/video duration mismatch: {abs(audio_duration - duration):.2f}s")
        decode = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"], capture_output=True, text=True)
        if decode.returncode or decode.stderr.strip():
            errors.append(decode.stderr.strip() or "Frame decode failed")
        if has_audio:
            volume = subprocess.run([
                "ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-map", "0:a:0",
                "-af", "volumedetect", "-f", "null", "-",
            ], capture_output=True, text=True)
            if volume.returncode:
                errors.append(volume.stderr.strip() or "Audio volume inspection failed")
            else:
                match = re.search(r"mean_volume:\s*(-inf|-?\d+(?:\.\d+)?)\s*dB", volume.stderr)
                if not match:
                    errors.append("Audio volume could not be measured")
                elif match.group(1) == "-inf" or float(match.group(1)) < -50:
                    errors.append("Audio is silent or below -50 dB")
    except (KeyError, StopIteration, ValueError, RuntimeError, FileNotFoundError) as error:
        errors.append(str(error))
    return QAResult(valid=not errors, duration=duration, width=width, height=height, has_audio=has_audio, errors=errors)
