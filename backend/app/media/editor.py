from pathlib import Path

import ffmpeg

from app.media.poster import render_cast_cards
from app.media.text import font_path
from app.schemas import AudioTimeline, CuratedAsset, PressKitOutput, TrailerEDL


class RenderError(RuntimeError):
    pass


class VideoEditor:
    def render(
        self,
        project_dir: Path,
        project_id: str,
        edl: TrailerEDL,
        assets: list[CuratedAsset],
        poster_path: Path,
        audio: AudioTimeline,
    ) -> PressKitOutput:
        output_dir = project_dir / "output"
        title_dir = project_dir / "titles"
        output_dir.mkdir(parents=True, exist_ok=True)
        title_dir.mkdir(parents=True, exist_ok=True)
        asset_map = {asset.id: asset for asset in assets}
        streams = []

        for index, segment in enumerate(edl.segments):
            asset = asset_map[segment.asset_id]
            duration = segment.end - segment.start
            if asset.kind == "photo":
                source = ffmpeg.input(
                    str(asset.source_path), loop=1, framerate=24, t=duration + 0.25
                ).video
            else:
                source = ffmpeg.input(str(asset.source_path), ss=0, t=duration + 0.25).video
                source = source.filter("tpad", stop_mode="clone", stop_duration=duration)
            source = source.filter(
                "scale", 1080, 1920, force_original_aspect_ratio="increase"
            ).filter("crop", 1080, 1920).filter("setsar", 1).filter("fps", 24)
            frame_count = max(1, round(duration * 24))
            if segment.ken_burns == "zoom_in":
                zoom = "min(1.0+on*0.00035,1.09)"
                x, y = "(iw-iw/zoom)/2", "(ih-ih/zoom)/2"
            elif segment.ken_burns == "zoom_out":
                zoom = "max(1.09-on*0.00035,1.0)"
                x, y = "(iw-iw/zoom)/2", "(ih-ih/zoom)/2"
            elif segment.ken_burns == "pan_left":
                zoom = "1.08"
                x, y = f"(iw-iw/zoom)*(1-on/{frame_count})", "(ih-ih/zoom)/2"
            else:
                zoom = "1.08"
                x, y = f"(iw-iw/zoom)*(on/{frame_count})", "(ih-ih/zoom)/2"
            source = source.filter(
                "zoompan", z=zoom, x=x, y=y, d=1, s="1080x1920", fps=24
            ).filter("trim", duration=duration).filter("setpts", "PTS-STARTPTS")
            if segment.title_card:
                text_path = title_dir / f"title-{index:02d}.txt"
                text_path.write_text(segment.title_card, encoding="utf-8")
                source = source.filter(
                    "drawtext",
                    fontfile=font_path(),
                    textfile=str(text_path),
                    fontsize=74,
                    fontcolor="#F3F0E8",
                    borderw=2,
                    bordercolor="#0A0A0C",
                    line_spacing=10,
                    x="(w-text_w)/2",
                    y="h*0.20",
                    enable=f"between(t,0.12,{min(2.3, duration)})",
                )
            streams.append(source)

        video = ffmpeg.concat(*streams, v=1, a=0)
        flashes = [marker for marker in edl.beat_markers if 0.1 < marker < edl.duration]
        if flashes:
            enable = "+".join(f"between(t,{marker},{marker + 0.055})" for marker in flashes)
            video = video.filter("drawbox", x=0, y=0, w="iw", h="ih", color="white@0.32", t="fill", enable=enable)
        video = video.filter("noise", alls=3, allf="t").filter("format", "yuv420p")

        voice_input = ffmpeg.input(str(audio.voice_path)).audio.filter(
            "aresample", 48000
        ).filter("atrim", duration=edl.duration)
        voice_split = voice_input.filter_multi_output("asplit", 2)
        voice_sidechain, voice_mix = voice_split[0], voice_split[1]
        music = ffmpeg.input(str(audio.music_path)).audio.filter("aresample", 48000).filter(
            "atrim", duration=edl.duration
        ).filter("volume", 0.58)
        ducked = ffmpeg.filter(
            [music, voice_sidechain],
            "sidechaincompress",
            threshold=0.025,
            ratio=8,
            attack=20,
            release=350,
        )
        mixed = ffmpeg.filter(
            [ducked, voice_mix], "amix", inputs=2, duration="first", normalize=0
        ).filter("loudnorm", I=-16, TP=-1.5, LRA=11)

        trailer_path = output_dir / "trailer.mp4"
        try:
            ffmpeg.output(
                video,
                mixed,
                str(trailer_path),
                t=edl.duration,
                vcodec="libx264",
                preset="veryfast",
                crf=23,
                pix_fmt="yuv420p",
                acodec="aac",
                audio_bitrate="192k",
                ar=48000,
                movflags="+faststart",
                threads=2,
            ).overwrite_output().global_args("-filter_complex_threads", "1", "-hide_banner", "-loglevel", "error").run(
                capture_stdout=True, capture_stderr=True
            )
        except ffmpeg.Error as error:
            details = error.stderr.decode("utf-8", errors="replace") if error.stderr else str(error)
            raise RenderError(details[-5000:]) from error

        cast_cards = render_cast_cards(project_dir, project_id, edl, assets)
        (output_dir / "edl.json").write_text(edl.model_dump_json(indent=2), encoding="utf-8")
        return PressKitOutput(
            trailer_url=f"/media/{project_id}/output/trailer.mp4",
            poster_url=f"/media/{project_id}/output/poster.png",
            cast_cards=cast_cards,
            edl=edl,
            duration=edl.duration,
            beat_markers=edl.beat_markers,
        )
