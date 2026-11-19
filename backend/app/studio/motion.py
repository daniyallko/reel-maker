import asyncio
import colorsys
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

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
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", accent):
        accent = "#d4a853"
    scene_data = []
    for index, scene in enumerate(storyboard.scenes):
        asset = assets[min(index, len(assets) - 1)]
        scene_data.append({
            "start": scene.start,
            "end": scene.end,
            "headline": scene.headline,
            "narration": scene.narration,
            "image": asset.local_path.as_uri(),
        })
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
:root {{ --enter:400ms; --exit:200ms; --stagger:60ms; }}
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ width:1080px; height:1920px; overflow:hidden; background:#05060a; color:#fff; font-family:Arial,Helvetica,sans-serif; }}
.stage {{ position:relative; width:100%; height:100%; perspective:1400px; background:radial-gradient(circle at 50% 30%,#171b2a,#05060a 70%); }}
.stage::after {{ content:""; position:absolute; inset:0; pointer-events:none; opacity:.03; background-image:radial-gradient(#fff 1px,transparent 1px); background-size:5px 5px; }}
.scene {{ position:absolute; inset:0; opacity:0; transform-style:preserve-3d; }}
.layout-0 {{ --media-x:168px; --media-y:300px; --media-w:744px; --media-h:640px; --headline-y:1040px; --caption-y:1330px; }}
.layout-1 {{ --media-x:72px; --media-y:480px; --media-w:936px; --media-h:480px; --headline-y:1060px; --caption-y:1340px; }}
.layout-2 {{ --media-x:300px; --media-y:220px; --media-w:708px; --media-h:650px; --headline-y:1060px; --caption-y:1340px; }}
.layout-3 {{ --media-x:72px; --media-y:260px; --media-w:936px; --media-h:560px; --headline-y:920px; --caption-y:1240px; }}
.browser {{ position:absolute; left:var(--media-x); top:var(--media-y); width:var(--media-w); height:var(--media-h); object-fit:cover; border:1px solid #ffffff30; border-radius:22px; box-shadow:0 40px 100px #000b; transform-origin:50% 50%; }}
.chrome {{ position:absolute; left:72px; top:180px; color:#ffffff70; font:18px monospace; letter-spacing:.18em; }}
.scene-number {{ position:absolute; right:72px; top:160px; color:#ffffff12; font-size:96px; font-weight:600; line-height:.92; letter-spacing:-.04em; }}
.headline {{ position:absolute; left:72px; right:72px; top:var(--headline-y); font-size:66px; font-weight:600; line-height:1.06; letter-spacing:-.04em; text-shadow:0 4px 30px #000; }}
.word {{ display:inline-block; margin-right:.22em; opacity:0; }}
.caption {{ position:absolute; left:72px; right:72px; top:var(--caption-y); color:#ffffffb0; font-size:24px; line-height:1.45; }}
.beat {{ position:absolute; left:72px; top:1510px; color:{accent}; font:18px monospace; letter-spacing:.14em; }}
</style></head><body><div class="stage" id="stage"></div><script>
const scenes = {json.dumps(scene_data)};
const phaseLayouts = [
  [{{x:168,y:320,w:744,h:600}}, {{x:72,y:340,w:936,h:520}}, {{x:220,y:300,w:640,h:660}}, {{x:72,y:300,w:936,h:600}}],
  [{{x:72,y:500,w:936,h:420}}, {{x:180,y:340,w:720,h:600}}, {{x:300,y:300,w:500,h:650}}, {{x:72,y:360,w:936,h:560}}],
  [{{x:300,y:300,w:708,h:560}}, {{x:72,y:360,w:936,h:500}}, {{x:180,y:300,w:720,h:620}}, {{x:72,y:320,w:936,h:540}}],
  [{{x:72,y:300,w:936,h:520}}, {{x:160,y:320,w:760,h:540}}, {{x:260,y:300,w:560,h:600}}, {{x:72,y:300,w:936,h:520}}]
];
const stage = document.getElementById('stage');
const enterMs = 400, exitMs = 200, staggerMs = 60;
const easeOut = t => 1 - Math.pow(1 - t, 3);
const easeIn = t => t * t * t;
function build() {{
  scenes.forEach((scene, sceneIndex) => {{
    const root = document.createElement('section');
    root.className = `scene layout-${{sceneIndex}}`;
    root.innerHTML = `<div class="chrome">LINK2REEL / SCENE ${{String(sceneIndex + 1).padStart(2,'0')}}</div><div class="scene-number">0${{sceneIndex + 1}}</div><img class="browser" src="${{scene.image}}"><h1 class="headline">${{scene.headline.split(' ').map(word => `<span class="word">${{word}}</span>`).join('')}}</h1><p class="caption">${{scene.narration}}</p><div class="beat">128 BPM / 30 FPS</div>`;
    stage.appendChild(root);
    scene.root = root;
  }});
}}
build();
window.seekTo = function(t) {{
  scenes.forEach((scene, index) => {{
    const duration = scene.end - scene.start;
    const local = Math.max(0, Math.min(duration, t - scene.start));
    const enter = Math.min(1, local * 1000 / enterMs);
    const exit = Math.min(1, (duration - local) * 1000 / exitMs);
    const active = t >= scene.start && t < scene.end;
    const enterEase = easeOut(enter);
    const exitEase = easeIn(exit);
    const opacity = active ? Math.min(enterEase, exitEase) : 0;
    const tilt = (1 - enterEase) * (index === 0 ? 58 : 18);
    const travel = (1 - enterEase) * 140 + (1 - exitEase) * -70;
    scene.root.style.opacity = opacity;
    scene.root.style.transform = `translate3d(0,${{travel}}px,0) rotateX(${{tilt}}deg) scale(${{0.88 + enterEase * 0.12}})`;
    const phaseDuration = 60 / 128 * 5;
    const phase = Math.min(3, Math.floor(local / phaseDuration));
    const phaseProgress = Math.min(1, (local % phaseDuration) / phaseDuration);
    const drift = 1 + phaseProgress * 0.025;
    const direction = phase % 2 === 0 ? -1 : 1;
    const frame = phaseLayouts[index][phase];
    const image = scene.root.querySelector('.browser');
    image.style.left = `${{frame.x}}px`;
    image.style.top = `${{frame.y}}px`;
    image.style.width = `${{frame.w}}px`;
    image.style.height = `${{frame.h}}px`;
    image.style.transform = `scale(${{drift}})`;
    image.style.objectPosition = `${{50 + direction * phase * 8}}% ${{35 + phase * 10}}%`;
    const words = scene.root.querySelectorAll('.word');
    words.forEach((word, wordIndex) => {{
      const wordProgress = Math.max(0, Math.min(1, (local * 1000 - wordIndex * staggerMs) / enterMs));
      word.style.opacity = easeOut(wordProgress);
      word.style.clipPath = `inset(${{(1 - easeOut(wordProgress)) * 100}}% 0 0 0)`;
      word.style.transform = `translateY(${{(1 - easeOut(wordProgress)) * 44}}px)`;
    }});
  }});
}};
window.seekTo(0);
</script></body></html>"""


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
        await browser.close()
        server.close()


async def generate_motion_html(storyboard: Storyboard, assets: list[StudioAsset], provider=None, project_dir: Path | None = None, palette: list[str] | None = None) -> str:
    if provider is not None:
        try:
            from google.genai import types
            from app.studio.providers import CORE_MODEL
            prompt = f"""
Write one self-contained HTML/CSS/JS motion scene for 1080x1920 at 30fps.
Every element must be a deterministic function of t through window.seekTo(t), with no wall-clock timers, setInterval, requestAnimationFrame loops, or CSS transitions.
Use a Swiss 12-column editorial grid with 72px margins, brand-extracted color tokens, left/grid-aligned headlines, clip-path typography reveals, 3D-tilted real scraped website screenshots, and layered shadows. Keep all critical text/logos/graphics in y:160px–1580px and reserve the bottom caption zone. First 2 seconds: 3D browser slab and clip-path headline wipe plus a rapid metric roll-up. Fresh state
changes every 1.8–3.0 seconds at 128 BPM. Entrances use cubic ease-out 400ms, exits ease-in 200ms, words stagger 60–100ms. Change the actual media composition between portrait and landscape crops, not just scale. Do not render duplicate headlines inside images. Use the real asset file URLs below,
never draw fake UI. No external scripts, images, fonts, or network calls.
Brand tokens: {palette or []}
Storyboard: {storyboard.model_dump_json()}\nAssets: {[asset.local_path.as_uri() for asset in assets]}
Return only HTML.
"""
            config = types.GenerateContentConfig(thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.HIGH))
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
            pass
    return fallback_motion_html(storyboard, assets, accent=select_brand_accent(palette or []))
