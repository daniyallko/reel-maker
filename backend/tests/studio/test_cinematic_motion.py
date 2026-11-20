from pathlib import Path

import pytest
from playwright.async_api import async_playwright

from app.studio.sources import ingest_text
from app.studio.urls import configure_offline_page, localize_motion_html
from app.studio.visuals import build_scene_visuals
from tests.studio.directed_fixtures import directed_storyboard


async def cinematic_page(tmp_path: Path):
    from app.studio.cinematic import cinematic_motion_html

    storyboard = directed_storyboard()
    assets = await build_scene_visuals(storyboard, ingest_text("Ocean robots"), tmp_path)
    html = cinematic_motion_html(storyboard, assets)
    return storyboard, assets, html


async def seek_and_settle(page, timestamp: float) -> None:
    await page.evaluate("""
        timestamp => {
          window.seekTo(timestamp);
          return new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
        }
    """, timestamp)


async def active_scene_state(page):
    return await page.evaluate("""
        () => {
          const active = [...document.querySelectorAll('.scene[data-active="true"]')];
          if (active.length !== 1) return {activeCount: active.length};
          const scene = active[0];
          const critical = [...scene.querySelectorAll('[data-critical]')].map(element => {
            const rect = element.getBoundingClientRect();
            return {top: rect.top, bottom: rect.bottom, left: rect.left, right: rect.right};
          });
          return {
            activeCount: active.length,
            sceneId: scene.dataset.sceneId,
            visualType: scene.dataset.visualType,
            template: scene.dataset.template,
            phase: scene.dataset.phase,
            critical,
            imagesLoaded: [...scene.querySelectorAll('img')].every(
              image => image.complete && image.naturalWidth > 0
            ),
            assetUrl: scene.querySelector('.scene-asset').src,
            narration: document.querySelector('.narration')?.textContent || '',
            bodyText: document.body.innerText,
            overflow: document.documentElement.scrollWidth > 1080,
          };
        }
    """)


def assert_safe_state(state):
    assert state["activeCount"] == 1
    assert state["imagesLoaded"] is True
    assert state["overflow"] is False
    for rect in state["critical"]:
        assert rect["top"] >= 160
        assert rect["bottom"] <= 1580


@pytest.mark.asyncio
async def test_every_visual_type_has_a_distinct_template(tmp_path):
    _, _, html = await cinematic_page(tmp_path)
    for visual_type in (
        "screenshot",
        "source_image",
        "generated_art",
        "kinetic_type",
        "diagram",
        "data",
    ):
        assert f'data-visual-type="{visual_type}"' in html
    for template in ("media", "kinetic", "diagram", "data"):
        assert f'data-template="{template}"' in html


@pytest.mark.asyncio
async def test_cinematic_scenes_stay_deterministic_and_inside_safe_zones(tmp_path):
    storyboard, assets, html = await cinematic_page(tmp_path)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page(viewport={"width": 1080, "height": 1920})
        server = await configure_offline_page(page, tmp_path)
        try:
            await page.set_content(
                localize_motion_html(html, tmp_path, server.base_url),
                wait_until="load",
            )
            for index, scene in enumerate(storyboard.scenes):
                midpoint = (scene.start + scene.end) / 2
                later = midpoint + 0.5
                await seek_and_settle(page, midpoint)
                first = await page.screenshot()
                state = await active_scene_state(page)
                assert_safe_state(state)
                assert state["sceneId"] == scene.id
                assert state["visualType"] == scene.visual_type
                assert state["assetUrl"].endswith(f"/visuals/scene-{index:02d}.png")
                assert assets[index].id == f"scene-{scene.id}"
                assert state["narration"] == ""
                assert scene.narration not in state["bodyText"]

                await seek_and_settle(page, later)
                later_state = await active_scene_state(page)
                assert_safe_state(later_state)
                assert later_state["sceneId"] == scene.id
                assert later_state["visualType"] == scene.visual_type
                await seek_and_settle(page, midpoint)
                second = await page.screenshot()
                if second != first:
                    (tmp_path / f"{scene.id}-first.png").write_bytes(first)
                    (tmp_path / f"{scene.id}-second.png").write_bytes(second)
                assert second == first, scene.id

                if scene.end - scene.start > 3:
                    early = scene.start + 0.8
                    after_phase = early + 2.5
                    await page.evaluate(f"window.seekTo({early})")
                    early_state = await page.locator(".scene[data-active='true']").evaluate(
                        "scene => ({phase: scene.dataset.phase, transform: scene.querySelector('.composition').style.transform})"
                    )
                    await page.evaluate(f"window.seekTo({after_phase})")
                    later_state = await page.locator(".scene[data-active='true']").evaluate(
                        "scene => ({phase: scene.dataset.phase, transform: scene.querySelector('.composition').style.transform})"
                    )
                    assert later_state["phase"] != early_state["phase"]
                    assert later_state["transform"] != early_state["transform"]

            diagram = storyboard.scenes[4]
            await page.evaluate(f"window.seekTo({diagram.start + 0.5})")
            early_offset = await page.locator('.scene[data-active="true"] .diagram-path').evaluate(
                "path => path.style.strokeDashoffset"
            )
            await page.evaluate(f"window.seekTo({diagram.start + 1.2})")
            later_offset = await page.locator('.scene[data-active="true"] .diagram-path').evaluate(
                "path => path.style.strokeDashoffset"
            )
            assert later_offset != early_offset

            data = storyboard.scenes[5]
            await page.evaluate(f"window.seekTo({data.start + 0.3})")
            early_counter = await page.locator('.scene[data-active="true"] .metric-value').inner_text()
            await page.evaluate(f"window.seekTo({data.start + 1.1})")
            later_counter = await page.locator('.scene[data-active="true"] .metric-value').inner_text()
            assert later_counter != early_counter
            await page.evaluate(f"window.seekTo({data.end - 0.01})")
            assert await page.locator('.scene[data-active="true"] .metric-value').inner_text() == "1,200 kg"
        finally:
            await browser.close()
            server.close()


@pytest.mark.asyncio
async def test_callouts_and_metrics_render_as_escaped_text(tmp_path):
    from app.studio.cinematic import cinematic_motion_html

    storyboard = directed_storyboard()
    scenes = [scene.model_copy(deep=True) for scene in storyboard.scenes]
    scenes[4].callouts = ["Collect <img src=x onerror=alert(1)>", "Sort </script>"]
    scenes[5].metrics[0].label = "Collected <b>now</b>"
    scenes[5].metrics[0].display = "1,200 kg <svg onload=alert(1)>"
    storyboard = storyboard.model_copy(update={"scenes": scenes})
    assets = await build_scene_visuals(storyboard, ingest_text("Ocean robots"), tmp_path)
    html = cinematic_motion_html(storyboard, assets)
    assert "Sort </script>" not in html
    assert "Sort &lt;/script&gt;" in html

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page(viewport={"width": 1080, "height": 1920})
        server = await configure_offline_page(page, tmp_path)
        try:
            await page.set_content(
                localize_motion_html(html, tmp_path, server.base_url),
                wait_until="load",
            )
            await page.evaluate("window.seekTo(20)")
            assert await page.locator(".diagram-node img").count() == 0
            assert "<img src=x onerror=alert(1)>" in await page.locator(".diagram-node").first.inner_text()
            await page.evaluate("window.seekTo(31.9)")
            assert await page.locator(".metric-card b, .metric-card svg").count() == 0
            assert await page.locator(".metric-value").inner_text() == "1,200 kg <svg onload=alert(1)>"
            assert "<b>now</b>" in (await page.locator(".metric-label").inner_text()).lower()
        finally:
            await browser.close()
            server.close()
