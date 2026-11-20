import io
from pathlib import Path

import pytest
from PIL import Image
from playwright.async_api import async_playwright

from app.studio.motion import fallback_motion_html, sanitize_motion_html, validate_motion_clock
from app.studio.providers import mock_storyboard, fallback_visuals
from app.studio.schemas import HarvestResult
from app.studio.sources import ingest_text
from app.studio.urls import configure_offline_page, localize_motion_html
from app.studio.vision import MAX_REVISIONS, capture_keyframes


def test_motion_html_is_deterministic_and_asset_driven(tmp_path: Path):
    storyboard = mock_storyboard("launch", "Fenrir")
    assets = fallback_visuals(storyboard, None, tmp_path)
    html = fallback_motion_html(storyboard, assets)
    assert "window.seekTo" in html
    assert "400ms" in html
    assert "200ms" in html
    assert "60ms" in html
    assert "file://" in html
    assert "3d" in html.lower() or "perspective" in html.lower()


def test_sanitizer_removes_external_code_and_requires_seek_to():
    html = "<html><script src='https://evil.example/x.js'></script><img src='https://evil.example/x.png'><script>window.seekTo = t => t;</script></html>"
    cleaned = sanitize_motion_html(html)
    assert "evil.example" not in cleaned
    assert "window.seekTo" in cleaned
    with pytest.raises(ValueError):
        sanitize_motion_html("<html><body>No animation clock</body></html>")


def test_vision_revision_limit_is_one():
    assert MAX_REVISIONS == 1


@pytest.mark.asyncio
async def test_six_audit_frames_are_captured(tmp_path: Path):
    storyboard = mock_storyboard("launch", "Fenrir")
    assets = fallback_visuals(storyboard, None, tmp_path)
    html = fallback_motion_html(storyboard, assets)
    contact_sheet = await capture_keyframes(html, tmp_path, [0.6, 3.5, 8, 14, 21, 27])
    assert contact_sheet.exists()
    frames = sorted((tmp_path / "audit").glob("frame-*.png"))
    assert len(frames) == 6


async def motion_geometry(tmp_path: Path, timestamps: list[float]) -> list[dict]:
    storyboard = mock_storyboard("launch", "Fenrir")
    assets = fallback_visuals(storyboard, None, tmp_path)
    html = fallback_motion_html(storyboard, assets)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page(viewport={"width": 1080, "height": 1920})
        server = await configure_offline_page(page, tmp_path)
        try:
            await page.set_content(localize_motion_html(html, tmp_path, server.base_url), wait_until="load")
            frames = []
            for timestamp in timestamps:
                await page.evaluate(f"window.seekTo({timestamp})")
                frames.append(await page.evaluate("""
                    () => {
                      const scene = [...document.querySelectorAll('.scene')].find(
                        element => Number(getComputedStyle(element).opacity) > 0.9
                      );
                      return Object.fromEntries(['chrome', 'browser', 'headline', 'caption', 'beat'].map(name => {
                        const rect = scene.querySelector(`.${name}`).getBoundingClientRect();
                        return [name, {left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom,
                          width: rect.width, height: rect.height}];
                      }));
                    }
                """))
            return frames
        finally:
            await browser.close()
            server.close()


@pytest.mark.asyncio
async def test_motion_regions_do_not_overlap(tmp_path: Path):
    frames = await motion_geometry(tmp_path, [0.6, 3.5, 8, 14, 21, 27])
    for frame in frames:
        assert frame["browser"]["bottom"] <= frame["headline"]["top"]
        assert frame["headline"]["bottom"] <= frame["caption"]["top"]
        assert frame["caption"]["bottom"] <= frame["beat"]["top"]


@pytest.mark.asyncio
async def test_critical_text_stays_inside_safe_zone(tmp_path: Path):
    frames = await motion_geometry(tmp_path, [0.6, 3.5, 8, 14, 21, 27])
    for frame in frames:
        for name in ("chrome", "headline", "caption", "beat"):
            assert frame[name]["top"] >= 160
            assert frame[name]["bottom"] <= 1580


@pytest.mark.asyncio
async def test_scenes_use_distinct_compositions(tmp_path: Path):
    frames = await motion_geometry(tmp_path, [0.6, 3.5, 14, 27])
    signatures = {
        tuple(round(frame["browser"][key]) for key in ("left", "top", "width", "height"))
        for frame in frames
    }
    assert len(signatures) == len(frames)


@pytest.mark.asyncio
async def test_beat_phases_change_media_composition(tmp_path: Path):
    early, late = await motion_geometry(tmp_path, [3.5, 8])
    assert abs(late["browser"]["width"] - early["browser"]["width"]) >= 100
    assert abs(late["browser"]["height"] - early["browser"]["height"]) >= 100


def test_source_visuals_do_not_bake_in_headlines(tmp_path: Path):
    source = tmp_path / "solid.png"
    Image.new("RGB", (1080, 1920), "#182030").save(source)
    harvest = HarvestResult(
        source_url="https://example.com",
        title="Example",
        palette=["#182030"],
        fonts=[],
        dom_copy="Example source",
        assets=[],
        screenshots=[source],
        scroll_video=source,
    )
    assets = fallback_visuals(mock_storyboard("launch", "Fenrir"), harvest, tmp_path)
    screenshot = next(asset for asset in assets if asset.id == "scene-hook")
    with Image.open(screenshot.local_path) as image:
        low, high = image.convert("L").getextrema()
        assert low == high


def test_fallback_visuals_preserve_source_brightness(tmp_path: Path):
    source = tmp_path / "solid.png"
    Image.new("RGB", (1080, 1920), "#808080").save(source)
    harvest = HarvestResult(
        source_url="https://example.com",
        title="Example",
        palette=["#808080"],
        fonts=[],
        dom_copy="Example source",
        assets=[],
        screenshots=[source],
        scroll_video=source,
    )
    assets = fallback_visuals(mock_storyboard("launch", "Fenrir"), harvest, tmp_path)
    screenshot = next(asset for asset in assets if asset.id == "scene-hook")
    with Image.open(screenshot.local_path) as image:
        red, _, _ = image.getpixel((540, 960))
        assert red >= 100


def test_motion_uses_harvested_brand_accent(tmp_path: Path):
    from app.studio.motion import select_brand_accent

    accent = select_brand_accent(["rgb(8, 9, 10)", "rgb(255, 255, 255)", "rgb(94, 106, 210)"])
    assert accent == "#5e6ad2"
    storyboard = mock_storyboard("launch", "Fenrir")
    assets = fallback_visuals(storyboard, None, tmp_path)
    html = fallback_motion_html(storyboard, assets, accent=accent)
    assert "color:#5e6ad2" in html


def test_fallback_visuals_prefer_uploaded_images(tmp_path: Path):
    uploaded = tmp_path / "upload.png"
    Image.new("RGB", (1080, 1920), "#204060").save(uploaded)
    bundle = ingest_text("A cinematic story with a user image.")
    bundle = bundle.model_copy(update={"image_paths": [uploaded]})
    assets = fallback_visuals(mock_storyboard("launch", "Fenrir"), bundle, tmp_path)
    source_image = next(asset for asset in assets if asset.id == "scene-takeaway")
    with Image.open(source_image.local_path) as image:
        blue = image.getpixel((540, 960))[2]
    assert blue > 70


def test_text_only_visuals_do_not_reuse_orbit_image(tmp_path: Path):
    from app.media.poster import cover

    bundle = ingest_text("A story with no website or image assets.")
    assets = fallback_visuals(mock_storyboard("launch", "Fenrir"), bundle, tmp_path)
    orbit_path = Path(__file__).resolve().parents[2] / "assets/link2reel/sample-site/orbit-hero.jpg"
    expected = cover(Image.open(orbit_path).convert("RGB"), (1080, 1920), focus_y=0.37).convert("RGBA")
    expected = Image.alpha_composite(expected, Image.new("RGBA", expected.size, (4, 6, 14, 30)))
    output = io.BytesIO()
    expected.convert("RGB").save(output, "PNG", optimize=True)
    assert assets[0].local_path.read_bytes() != output.getvalue()


@pytest.mark.asyncio
async def test_source_markup_cannot_break_motion_clock_or_inject_html(tmp_path: Path):
    from app.studio.providers import fallback_storyboard

    bundle = ingest_text("Hello </script><img src=x onerror=alert(1)> world. Second sentence. Third sentence. Fourth sentence.")
    storyboard = fallback_storyboard(bundle, bundle.citations, "launch", "Fenrir")
    assets = fallback_visuals(storyboard, bundle, tmp_path)
    html = fallback_motion_html(storyboard, assets)
    assert "\\u003c/script\\u003e" in html
    await validate_motion_clock(html, tmp_path)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page(viewport={"width": 1080, "height": 1920})
        server = await configure_offline_page(page, tmp_path)
        await page.set_content(localize_motion_html(html, tmp_path, server.base_url), wait_until="load")
        await page.evaluate("window.seekTo(0.6)")
        assert await page.locator(".headline img").count() == 0
        assert "<img" in await page.locator(".caption").first.inner_text()
        await browser.close()
        server.close()
