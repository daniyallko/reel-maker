"""Render the directed benchmark locally using the production audio and video pipeline."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import get_settings
from app.studio.audio import produce_audio
from app.studio.providers import GeminiStudioProvider
from app.studio.eclipse import eclipse_board, eclipse_motion
from app.studio.renderer import MotionRenderer, render_directed_preview, verify_studio_video
from app.studio.schemas import SourceCitation, StudioAsset
from app.studio.timeline import align_audio_timeline
from app.studio.vision import capture_keyframes


async def main():
    settings = get_settings()
    directory = settings.data_dir / "eclipsevoice"
    directory.mkdir(exist_ok=True)
    source = SourceCitation(url="https://science.nasa.gov/eclipses/types/", title="Types of eclipses",
                            claim="The Moon passes between Earth and the Sun. Observers see a partial or total eclipse depending on their position in its shadow. Totality reveals the corona.")
    board = eclipse_board([source], "deep_dive", "Fenrir")
    if settings.gemini_enabled:
        provider = GeminiStudioProvider(settings.gemini_api_key, settings)
        audio = await provider.synthesize(board, directory)
    else:
        audio = await produce_audio(board, directory)
    print("Narration:", audio.narration_voice, flush=True)
    board, audio = align_audio_timeline(board, audio, directory)
    html = eclipse_motion(board)
    await render_directed_preview(html, board, audio, directory)
    await capture_keyframes(html, directory, [30])
    cover = directory / "audit" / "frame-00-30.000.png"
    asset = StudioAsset(id="cover", kind="thumbnail", label="Eclipse", url=f"/media/{directory.name}/{cover.relative_to(directory)}",
                        mime_type="image/png", local_path=cover)
    output = await MotionRenderer().render(html, board, [asset], audio, directory, quality_mode="draft", review_label="Unreviewed draft")
    path = directory / "output" / "trailer.mp4"
    qa = verify_studio_video(path)
    if not qa.valid:
        raise RuntimeError(qa.errors)
    (path.parent / "studio-output.json").write_text(output.model_dump_json(indent=2), encoding="utf-8")
    print(path, qa)


if __name__ == "__main__":
    asyncio.run(main())
