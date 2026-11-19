import asyncio
import json
from pathlib import Path

from app.config import get_settings
from app.studio.graph import merge_source_bundle
from app.studio.harvest import harvest
from app.studio.motion import fallback_motion_html, select_brand_accent
from app.studio.providers import GeminiStudioProvider, MockStudioProvider, fallback_visuals, portfolio_storyboard
from app.studio.renderer import MotionRenderer, SAMPLE_OUTPUT
from app.studio.schemas import StudioAsset
from app.studio.sources import ingest_text
from app.studio.vision import VisionDirector, capture_keyframes, require_passing_audit, require_unaudited_allowed, review_label_for
from app.studio.vision_providers import build_vision_router

ROOT = Path(__file__).resolve().parent.parent
PORTFOLIO_URL = "https://daniyal.pro"
CV_PATH = ROOT / "assets/link2reel/portfolio/cv.txt"


async def main():
    settings = get_settings()
    SAMPLE_OUTPUT.mkdir(parents=True, exist_ok=True)
    harvested = await harvest(PORTFOLIO_URL, SAMPLE_OUTPUT)
    cv_bundle = ingest_text(CV_PATH.read_text(encoding="utf-8"), title="Mohd Daniyal — Full Stack AI Engineer")
    harvested = merge_source_bundle(harvested, cv_bundle)
    storyboard = portfolio_storyboard()
    provider = GeminiStudioProvider(settings.gemini_api_key or "") if settings.gemini_api_key else MockStudioProvider()
    visuals = fallback_visuals(storyboard, harvested, SAMPLE_OUTPUT)
    audio = await provider.synthesize(storyboard, SAMPLE_OUTPUT)
    html = fallback_motion_html(storyboard, visuals, accent=select_brand_accent(harvested.palette))
    critique = await capture_keyframes(html, SAMPLE_OUTPUT, [0.6, 3.5, 8, 14, 21, 27])
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
            if audit.scores:
                require_passing_audit(audit, "draft")
            else:
                require_unaudited_allowed("draft")
            quality_mode = "draft"
            review_label = review_label_for(audit, "draft")
        scores = {score.criterion: score.score for score in audit.scores}
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
