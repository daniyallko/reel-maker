import asyncio
import colorsys
import re
from pathlib import Path

from bs4 import BeautifulSoup

from app.studio.cinematic import cinematic_motion_html, inline_script_json
from app.studio.schemas import Storyboard, StudioAsset
from app.studio.urls import configure_offline_page, localize_motion_html


def sanitize_motion_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["iframe", "object", "embed", "link"]):
        tag.decompose()
    for tag in soup.find_all("script"):
        if tag.get("src"):
            tag.decompose()
    for tag in soup.find_all(True):
        for attribute in ("src", "href", "action", "poster"):
            value = tag.get(attribute)
            if isinstance(value, str) and value.startswith(("http://", "https://", "//")):
                del tag[attribute]
        if tag.get("style") and "url(http" in tag["style"]:
            tag["style"] = "background-image:none"
    cleaned = str(soup)
    if "window.seekTo" not in cleaned:
        raise ValueError("Motion HTML must expose window.seekTo(t)")
    forbidden = ("fetch(", "xmlhttprequest", "websocket", "sendbeacon", "@import", "eval(", "import(", "window.open")
    if any(token in cleaned.lower() for token in forbidden):
        raise ValueError("Motion HTML must not access network or dynamic code")
    policy = soup.new_tag("meta", attrs={
        "http-equiv": "Content-Security-Policy",
        "content": "default-src 'none'; img-src 'self' file: data: blob: http://127.0.0.1:*; style-src 'self' 'unsafe-inline' file: http://127.0.0.1:*; script-src 'self' 'unsafe-inline' file: http://127.0.0.1:*; connect-src 'none'; font-src 'self' file: data:; media-src 'self' file: blob: http://127.0.0.1:*; frame-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'",
    })
    if soup.head:
        soup.head.insert(0, policy)
    else:
        soup.insert(0, policy)
    return str(soup)


def select_brand_accent(palette: list[str]) -> str:
    best_accent = ""
    best_score = 0.0
    for value in palette:
        value = value.strip()
        channels: tuple[int, int, int] | None = None
        alpha = 1.0
        if re.fullmatch(r"#[0-9a-fA-F]{6}", value):
            channels = tuple(int(value[index:index + 2], 16) for index in (1, 3, 5))
        else:
            match = re.fullmatch(r"rgba?\(\s*(\d+)[,\s]+(\d+)[,\s]+(\d+)(?:\s*[,/]\s*([\d.]+))?\s*\)", value)
            if match:
                channels = tuple(int(match.group(index)) for index in (1, 2, 3))
                alpha = float(match.group(4) or 1)
        if channels is None or alpha <= 0.2 or max(channels) > 255:
            continue
        _, lightness, saturation = colorsys.rgb_to_hls(*(channel / 255 for channel in channels))
        if saturation < 0.25 or not 0.25 <= lightness <= 0.8:
            continue
        score = saturation * (1 - abs(lightness - 0.5))
        if score > best_score:
            best_accent = "#{:02x}{:02x}{:02x}".format(*channels)
            best_score = score
    return best_accent or "#d4a853"


def fallback_motion_html(storyboard: Storyboard, assets: list[StudioAsset], accent: str = "#d4a853") -> str:
    if [s.id for s in storyboard.scenes] == [f"eclipse-{i}" for i in range(4)]:
        from app.studio.eclipse import eclipse_motion
        return eclipse_motion(storyboard)
    return cinematic_motion_html(storyboard, assets, accent)


async def validate_motion_clock(html: str, project_dir: Path) -> None:
    from playwright.async_api import async_playwright
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page(viewport={"width": 1080, "height": 1920})
        server = await configure_offline_page(page, project_dir)
        await page.set_content(localize_motion_html(html, project_dir, server.base_url), wait_until="load")
        valid = await page.evaluate("typeof window.seekTo === 'function'")
        if not valid:
            raise ValueError("Motion HTML has no callable seekTo")
        for timestamp in (1, 6, 14, 22):
            await page.evaluate(f"window.seekTo({timestamp})")
            if timestamp == 1:
                initial = await page.screenshot()
        await page.evaluate("window.seekTo(1)")
        if await page.screenshot() != initial:
            raise ValueError("Motion must reproduce the same frame when seeking backwards")
        await browser.close()
        server.close()


async def generate_motion_html(storyboard: Storyboard, assets: list[StudioAsset], provider=None, project_dir: Path | None = None, palette: list[str] | None = None) -> str:
    if [scene.id for scene in storyboard.scenes] == [f"eclipse-{i}" for i in range(4)]:
        from app.studio.eclipse import eclipse_motion
        return eclipse_motion(storyboard)
    if provider is not None:
        try:
            from google.genai import types
            from app.studio.providers import CORE_MODEL
            prompt = f"""
Write one self-contained HTML/CSS/JS motion scene for 1080x1920 at 30fps.
Every element must be a deterministic function of t through window.seekTo(t), with no wall-clock timers, setInterval, requestAnimationFrame loops, or CSS transitions.
Follow each typed scene's visual_type, layout, camera, animation, transition, callouts, and metrics exactly. Add data-scene-id, data-visual-type, and data-critical markers for browser validation.
Use screenshot assets in dimensional browser frames only for visual_type=screenshot. Use source_image for editorial photo compositions and generated_art for cinematic artwork. Render kinetic_type as procedural typography, diagram as labeled SVG paths, and data as sourced counters and bars. Never turn every subject into a website slab or invent metrics.
Use a Swiss 12-column editorial grid with 72px margins, brand-extracted color tokens, left/grid-aligned headlines, clip-path typography reveals, and layered shadows. Keep all critical text/logos/graphics in y:160px–1580px and reserve the bottom caption zone. Do not render a static full-narration paragraph.
First 2 seconds: a directed pattern interrupt with a clip-path headline wipe and a rapid metric roll-up when metrics exist. Introduce a fresh meaningful composition every 1.8–3.0 seconds at 128 BPM. Entrances use cubic ease-out 400ms, exits ease-in 200ms, words stagger 60–100ms. Honor the requested transition and camera. Change actual crops and composition between phases, not just scale. Do not render duplicate headlines inside images.
Use the real ordered per-scene asset file URLs below. No external scripts, images, fonts, or network calls.
Brand tokens: {palette or []}
Storyboard: {storyboard.model_dump_json()}\nAssets: {[asset.local_path.as_uri() for asset in assets]}
Return only HTML.
"""
            config = types.GenerateContentConfig(thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.HIGH))
            kimi = getattr(provider, "kimi", None)
            if kimi:
                first = await kimi.generate_text(prompt)
                if first:
                    try:
                        cleaned = sanitize_motion_html(first[0].removeprefix("```html").removesuffix("```").strip())
                        if project_dir is not None:
                            await validate_motion_clock(cleaned, project_dir)
                        return cleaned
                    except Exception:
                        kimi.history.append("moonshot: invalid motion, trying next provider")
            if getattr(provider, "director_model", None):
                raw = await provider.direct(prompt + "\nAnimate the specific physical objects and actions in each visual_prompt. Use the composition and pace appropriate to each shot.")
                cleaned = sanitize_motion_html(raw.removeprefix("```html").removesuffix("```").strip())
                if project_dir is not None:
                    await validate_motion_clock(cleaned, project_dir)
                return cleaned
            response = await asyncio.wait_for(asyncio.to_thread(
                provider.client.models.generate_content,
                model=CORE_MODEL,
                contents=prompt,
                config=config,
            ), timeout=120)
            html = response.text.removeprefix("```html").removesuffix("```").strip()
            cleaned = sanitize_motion_html(html)
            if project_dir is not None:
                await validate_motion_clock(cleaned, project_dir)
            return cleaned
        except Exception:
            if getattr(provider, "director_model", None):
                raise
            pass
    return fallback_motion_html(storyboard, assets, accent=select_brand_accent(palette or []))
