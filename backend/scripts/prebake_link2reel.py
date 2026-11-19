import asyncio
from pathlib import Path

from app.studio.harvest import harvest
from app.studio.motion import fallback_motion_html
from app.studio.providers import MockStudioProvider, fallback_visuals, mock_storyboard
from app.studio.renderer import MotionRenderer, SAMPLE_OUTPUT
from app.studio.schemas import StudioAsset
from app.studio.urls import sample_site_url
from app.studio.vision import capture_keyframes

ROOT = Path(__file__).resolve().parent.parent


async def main():
    SAMPLE_OUTPUT.mkdir(parents=True, exist_ok=True)
    harvested = await harvest(sample_site_url(), SAMPLE_OUTPUT)
    storyboard = mock_storyboard("launch", "Fenrir")
    provider = MockStudioProvider()
    visuals = fallback_visuals(storyboard, harvested, SAMPLE_OUTPUT)
    audio = await provider.synthesize(storyboard, SAMPLE_OUTPUT)
    html = fallback_motion_html(storyboard, visuals)
    critique = await capture_keyframes(html, SAMPLE_OUTPUT, [0.6, 3.5, 8, 14, 21, 27])
    output = await MotionRenderer().render(html, storyboard, visuals, audio, SAMPLE_OUTPUT, output_dir=SAMPLE_OUTPUT, source_url=sample_site_url())
    payload = {
        "output": output.model_dump(),
        "assets": [asset.model_dump() for asset in [
            *harvested.assets,
            *visuals,
            StudioAsset(id="critique", kind="critique", label="Director contact sheet", url="/media/sample-output/audit/contact-sheet.png", mime_type="image/png", local_path=critique),
        ]],
        "critique": str(critique),
    }
    (SAMPLE_OUTPUT / "sample.json").write_text(__import__("json").dumps(payload, indent=2), encoding="utf-8")
    print(f"Pre-baked LINK2REEL sample at {SAMPLE_OUTPUT}")


if __name__ == "__main__":
    asyncio.run(main())
