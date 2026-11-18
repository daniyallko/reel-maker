import asyncio
import subprocess
from pathlib import Path

import ffmpeg

from app.media.probe import media_duration
from app.schemas import AudioTimeline, TrailerEDL, VoiceCue

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
VOICE = "en-US-ChristopherNeural"


class AudioProducer:
    def render(self, project_dir: Path, edl: TrailerEDL, sample: bool = False) -> AudioTimeline:
        audio_dir = project_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        cues: list[VoiceCue] = []
        delayed_streams = []
        for index, segment in enumerate(segment for segment in edl.segments if segment.voiceover):
            text = segment.voiceover or ""
            available = segment.end - segment.start
            line_path = audio_dir / f"voice-{index:02d}.{'wav' if sample else 'mp3'}"
            try:
                if sample:
                    self._offline_voice(text, line_path, audio_dir / f"voice-{index:02d}.txt")
                else:
                    self._neural_voice(text, line_path)
                measured = media_duration(line_path)
                if measured <= 0:
                    raise RuntimeError("Narration is empty")
            except Exception:
                line_path = audio_dir / f"voice-{index:02d}-fallback.wav"
                self._offline_voice(text, line_path, audio_dir / f"voice-{index:02d}-fallback.txt")
                try:
                    measured = media_duration(line_path)
                    if measured <= 0:
                        raise RuntimeError("Offline narration is empty")
                except Exception:
                    self._silent(line_path, available)
                    measured = available
            cues.append(
                VoiceCue(start=segment.start, end=min(segment.end, segment.start + min(measured, available)), text=text)
            )
            stream = ffmpeg.input(str(line_path)).audio.filter("aresample", 48000)
            if measured > available:
                stream = self._fit_tempo(stream, measured / available)
            stream = stream.filter("apad").filter("atrim", duration=available)
            delay = round(segment.start * 1000)
            delayed_streams.append(stream.filter("adelay", delays=f"{delay}|{delay}"))

        voice_path = audio_dir / "voiceover.wav"
        if delayed_streams:
            voice = ffmpeg.filter(delayed_streams, "amix", inputs=len(delayed_streams), duration="longest", normalize=0)
            voice = voice.filter("apad").filter("atrim", duration=edl.duration)
            try:
                ffmpeg.output(voice, str(voice_path), ac=2, ar=48000).overwrite_output().run(
                    capture_stdout=True, capture_stderr=True
                )
            except ffmpeg.Error as error:
                details = error.stderr.decode("utf-8", errors="replace") if error.stderr else str(error)
                raise RuntimeError(f"Voiceover mix failed: {details[-3000:]}") from error
        else:
            self._silent(voice_path, edl.duration)

        music_path = BACKEND_DIR / "assets" / "music" / f"{edl.genre.value}.wav"
        if not music_path.exists():
            music_path = audio_dir / "music-fallback.wav"
            self._silent(music_path, edl.duration)
        return AudioTimeline(voice_path=voice_path, music_path=music_path, cues=cues)

    @staticmethod
    def _fit_tempo(stream, ratio: float):
        remaining = ratio
        while remaining > 2:
            stream = stream.filter("atempo", 2)
            remaining /= 2
        return stream.filter("atempo", max(1, remaining))

    @staticmethod
    def _silent(path: Path, duration: float) -> None:
        subprocess.run(
            [
                "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                "-t", str(duration), str(path),
            ],
            check=True,
            capture_output=True,
        )

    @staticmethod
    def _offline_voice(text: str, path: Path, text_path: Path) -> None:
        text_path.write_text(text, encoding="utf-8")
        command = [
            "ffmpeg", "-y", "-f", "lavfi", "-i",
            f"flite=textfile={text_path}:voice=slt", "-ar", "48000", "-ac", "2", str(path),
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode:
            AudioProducer._silent(path, 2.5)

    @staticmethod
    def _neural_voice(text: str, path: Path) -> None:
        import edge_tts

        async def save() -> None:
            await edge_tts.Communicate(text, VOICE, rate="-8%").save(str(path))

        asyncio.run(save())
