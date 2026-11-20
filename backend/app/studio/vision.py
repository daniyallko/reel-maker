import asyncio
from math import ceil
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.async_api import async_playwright
from pydantic import BaseModel

from app.studio.motion import sanitize_motion_html
from app.studio.schemas import Storyboard
from app.studio.urls import configure_offline_page, localize_motion_html

MAX_REVISIONS = 1


class CriterionScore(BaseModel):
    criterion: str
    score: int


class VisionAudit(BaseModel):
    passed: bool
    issues: list[str]
    scores: list[CriterionScore] = []
    patched_html: str | None = None


REQUIRED_CRITERIA = frozenset({
    "typography/contrast",
    "safe-zone compliance",
    "editorial craft",
    "visual momentum",
    "narrative alignment",
    "asset relevance",
})


def director_review_times(storyboard: Storyboard) -> list[float]:
    midpoints = sorted({round((scene.start + scene.end) / 2, 3) for scene in storyboard.scenes})
    extras = sorted({0.6, 1.0, round(storyboard.duration - 0.5, 3)} - set(midpoints))
    return sorted((midpoints + extras)[:12])


def validate_vision_audit(audit: VisionAudit) -> VisionAudit:
    criteria = [score.criterion for score in audit.scores]
    if len(criteria) != 6 or set(criteria) != REQUIRED_CRITERIA or len(set(criteria)) != 6:
        raise ValueError("Vision response must contain exactly six unique criteria")
    if any(score.score < 1 or score.score > 10 for score in audit.scores):
        raise ValueError("Vision scores must be between 1 and 10")
    return audit.model_copy(update={"passed": all(score.score >= 8 for score in audit.scores)})


def require_passing_audit(audit: VisionAudit, quality_mode: str = "strict") -> None:
    threshold = 7 if quality_mode == "draft" else 8
    try:
        audit = validate_vision_audit(audit)
    except ValueError as error:
        raise RuntimeError(f"Visual audit did not pass the six-criterion {threshold}/10 render gate: {{}}") from error
    scores = {score.criterion: score.score for score in audit.scores}
    if any(score < threshold for score in scores.values()):
        raise RuntimeError(f"Visual audit did not pass the six-criterion {threshold}/10 render gate: {scores}")


def require_unaudited_allowed(quality_mode: str) -> None:
    if quality_mode != "draft":
        raise RuntimeError("AI visual review is required in strict quality mode")


def should_use_unaudited_fallback(quality_mode: str, attempt: int) -> bool:
    return quality_mode == "draft" and attempt >= MAX_REVISIONS


def review_label_for(audit: VisionAudit | None, quality_mode: str) -> str | None:
    if quality_mode != "draft":
        return None
    if audit is None or not audit.scores or any(score.score < 8 for score in audit.scores):
        return "Unreviewed draft"
    return None


async def capture_keyframes(html: str, project_dir: Path, times: list[float]) -> Path:
    audit_dir = project_dir / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    frames: list[Path] = []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page(viewport={"width": 1080, "height": 1920})
        server = await configure_offline_page(page, project_dir)
        await page.set_content(localize_motion_html(html, project_dir, server.base_url), wait_until="load")
        for timestamp in times:
            await page.evaluate(f"window.seekTo({timestamp})")
            path = audit_dir / f"frame-{timestamp:.1f}.png"
            await page.screenshot(path=str(path))
            frames.append(path)
        await browser.close()
        server.close()
    contact = Image.new("RGB", (1080, ceil(len(times) / 3) * 640), "#05060a")
    draw = ImageDraw.Draw(contact)
    for index, path in enumerate(frames):
        image = Image.open(path).convert("RGB").resize((360, 640), Image.Resampling.LANCZOS)
        x = (index % 3) * 360
        y = (index // 3) * 640
        contact.paste(image, (x, y))
        draw.text((x + 20, y + 18), f"t={times[index]:.1f}s", fill="#d4a853")
    path = audit_dir / "contact-sheet.png"
    contact.save(path, "PNG", optimize=True)
    return path


class VisionDirector:
    def __init__(self, client, router=None):
        self.client = client
        self.router = router

    async def audit(self, contact_sheet: Path, html: str) -> VisionAudit:
        if self.router is not None:
            return await self.router.audit(contact_sheet, html)
        from google.genai import types
        from app.studio.providers import CORE_MODEL
        prompt = """
Score typography/contrast, safe-zone compliance, editorial craft, visual momentum,
narrative alignment, and asset relevance from 1-10. Return passed only if every score
is at least 8, plus scores and issues.
Keep text razor-sharp, left/grid-aligned, inside y:160-1580,
with no overlap or broken images. Check for distinct layouts and no static slideshow.
Check that scenes form a coherent narrative and every visible asset supports its scene.
Flag irrelevant screenshots and abstract placeholders.
Do not return patched HTML; a separate repair agent handles code changes.
"""
        config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.HIGH),
            response_mime_type="application/json",
            response_schema=VisionAudit,
        )
        for model in (CORE_MODEL, "gemini-3.5-flash-lite"):
            try:
                response = await asyncio.wait_for(asyncio.to_thread(
                    self.client.models.generate_content,
                    model=model,
                    contents=[prompt, types.Part.from_bytes(data=contact_sheet.read_bytes(), mime_type="image/png")],
                    config=config,
                ), timeout=120)
                break
            except Exception:
                continue
        else:
            raise RuntimeError("Vision providers are unavailable")
        audit = response.parsed if getattr(response, "parsed", None) else VisionAudit.model_validate_json(response.text)
        if not isinstance(audit, VisionAudit):
            audit = VisionAudit.model_validate(audit)
        if not audit.passed and audit.patched_html:
            try:
                audit.patched_html = sanitize_motion_html(audit.patched_html)
            except (ValueError, TypeError):
                audit.patched_html = None
        return audit

    async def repair(self, contact_sheet: Path, html: str, audit: VisionAudit, project_dir: Path) -> str:
        from google.genai import types
        from app.studio.motion import validate_motion_clock
        from app.studio.providers import CORE_MODEL

        prompt = f"""
Repair this deterministic 1080x1920 motion document using these visual audit issues:
{audit.issues}
Return only complete HTML. Keep every animation driven by window.seekTo(t), use no
network calls, timers, external assets, or CSS wall-clock transitions. Preserve real
local image URLs, safe zones y:160-1580, and distinct beat-phase compositions.
Original HTML:
{html}
"""
        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model=CORE_MODEL,
            contents=[prompt, types.Part.from_bytes(data=contact_sheet.read_bytes(), mime_type="image/png")],
        )
        cleaned = sanitize_motion_html(response.text.removeprefix("```html").removesuffix("```").strip())
        await validate_motion_clock(cleaned, project_dir)
        return cleaned

    async def safe_audit(self, contact_sheet: Path, html: str) -> VisionAudit:
        try:
            return await self.audit(contact_sheet, html)
        except Exception:
            return VisionAudit(
                passed=False,
                issues=["AI visual review is unavailable."],
                patched_html=None,
            )
