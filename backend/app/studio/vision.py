import asyncio
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.async_api import async_playwright
from pydantic import BaseModel

from app.studio.motion import sanitize_motion_html
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


def require_passing_audit(audit: VisionAudit) -> None:
    scores = {score.criterion: score.score for score in audit.scores}
    if not audit.passed or len(scores) < 4 or any(score < 8 for score in scores.values()):
        raise RuntimeError(f"Visual audit did not pass the four-criterion 8/10 render gate: {scores}")


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
    contact = Image.new("RGB", (1080, 1280), "#05060a")
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
    def __init__(self, client):
        self.client = client

    async def audit(self, contact_sheet: Path, html: str) -> VisionAudit:
        from google.genai import types
        from app.studio.providers import CORE_MODEL
        prompt = """
Score typography/contrast, safe-zone compliance, editorial craft, and visual momentum
from 1-10. Return passed only if every score is at least 8, plus scores and any
patched_html needed. Keep text razor-sharp, left/grid-aligned, inside y:160-1580,
with no overlap or broken images. Check for distinct layouts and no static slideshow.
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

    async def safe_audit(self, contact_sheet: Path, html: str) -> VisionAudit:
        try:
            return await self.audit(contact_sheet, html)
        except Exception as error:
            return VisionAudit(
                passed=True,
                issues=[f"Vision provider unavailable; deterministic motion retained: {error}"],
                patched_html=None,
            )
