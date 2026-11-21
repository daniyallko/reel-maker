import asyncio
import json
from pathlib import Path
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.studio.graph import merge_source_bundle
from app.studio.harvest import harvest
from app.studio.motion import fallback_motion_html, select_brand_accent
from app.studio.providers import GeminiStudioProvider, MockStudioProvider, portfolio_storyboard
from app.studio.renderer import MotionRenderer, SAMPLE_OUTPUT
from app.studio.schemas import StudioAsset
from app.studio.sources import ingest_text
from app.studio.timeline import align_audio_timeline
from app.studio.vision import VisionDirector, capture_keyframes, director_review_times, require_passing_audit, require_unaudited_allowed, review_label_for
from app.studio.visuals import build_scene_visuals
from app.studio.vision_providers import build_vision_router

PORTFOLIO_URL = "https://daniyal.pro"
CV_PATH = ROOT / "assets/link2reel/portfolio/cv.txt"


async def main():
    settings = get_settings()
    SAMPLE_OUTPUT.mkdir(parents=True, exist_ok=True)
    harvested = await harvest(PORTFOLIO_URL, SAMPLE_OUTPUT)
    cv_bundle = ingest_text(CV_PATH.read_text(encoding="utf-8"), title="Mohd Daniyal — Full Stack AI Engineer")
    harvested = merge_source_bundle(harvested, cv_bundle)
    storyboard = portfolio_storyboard()
    provider = GeminiStudioProvider(settings.gemini_api_key or "", settings=settings) if settings.gemini_api_key else MockStudioProvider()
    portfolio_visuals = harvested.model_copy(update={
        "image_paths": [*harvested.screenshots, *harvested.image_paths],
    })
    visuals = await build_scene_visuals(storyboard, portfolio_visuals, SAMPLE_OUTPUT)
    legacy_cover = SAMPLE_OUTPUT / "visuals" / "thumbnail-03.png"
    visuals[-1].local_path.replace(legacy_cover)
    with Image.open(harvested.screenshots[0]) as hero, Image.open(harvested.screenshots[1]) as projects:
        cover_image = Image.new("RGB", (1080, 1920), "#05060a")
        cover_image.paste(hero.convert("RGB").crop((0, 0, 1080, 960)), (0, 0))
        cover_image.paste(projects.convert("RGB").crop((0, 960, 1080, 1920)), (0, 960))
        cover_image.save(legacy_cover, "PNG", optimize=True)
    visuals[-1] = visuals[-1].model_copy(update={
        "url": "/media/sample-output/visuals/thumbnail-03.png",
        "local_path": legacy_cover,
    })
    audio = await provider.synthesize(storyboard, SAMPLE_OUTPUT)
    storyboard, audio = align_audio_timeline(storyboard, audio, SAMPLE_OUTPUT)
    html = fallback_motion_html(storyboard, visuals, accent=select_brand_accent(harvested.palette))
    critique = await capture_keyframes(html, SAMPLE_OUTPUT, director_review_times(storyboard))
    scores = {}
    quality_mode = "strict"
    review_label = None
    if settings.gemini_api_key:
        director = VisionDirector(provider.client, router=build_vision_router(settings, provider.client))
        audit = await director.safe_audit(critique, html)
        print(json.dumps({"vision_provider_history": director.router.history}), flush=True)
        try:
            require_passing_audit(audit, "strict")
        except RuntimeError:
            quality_mode = "draft"
            try:
                require_passing_audit(audit, "draft")
            except RuntimeError:
                require_unaudited_allowed("draft")
                audit = None
            review_label = review_label_for(audit, "draft")
        scores = {score.criterion: score.score for score in audit.scores} if audit else {}
    else:
        quality_mode = "draft"
        review_label = review_label_for(None, quality_mode)
    output = await MotionRenderer().render(
        html,
        storyboard,
        visuals,
        audio,
        SAMPLE_OUTPUT,
        output_dir=SAMPLE_OUTPUT,
        source_url=PORTFOLIO_URL,
        critique_scores=scores,
        quality_mode=quality_mode,
        review_label=review_label,
    )
    payload = {
        "output": output.model_dump(),
        "assets": [asset.model_dump() for asset in [
            *harvested.assets,
            *visuals,
            StudioAsset(id="critique", kind="critique", label="Director contact sheet", url="/media/sample-output/audit/contact-sheet.png", mime_type="image/png", local_path=critique),
        ]],
        "critique": str(critique),
    }
    (SAMPLE_OUTPUT / "sample.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Pre-baked Mohd Daniyal portfolio demo at {SAMPLE_OUTPUT}")


if __name__ == "__main__":
    asyncio.run(main())
