from pathlib import Path

import pytest
from playwright.async_api import async_playwright

from app.studio.sources import ingest_text
from app.studio.schemas import SceneMetric
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


@pytest.mark.asyncio
async def test_maximum_payloads_stay_bounded_across_phases(tmp_path):
    from app.studio.cinematic import cinematic_motion_html

    storyboard = directed_storyboard()
    scenes = [scene.model_copy(deep=True) for scene in storyboard.scenes]
    long_callouts = [f"CALL {index} " + "X" * 500 for index in range(4)]
    for scene in scenes:
        scene.callouts = long_callouts.copy()
    scenes[5].metrics = [
        SceneMetric(
            label="LABEL " + "L" * 600,
            value=1200,
            display="PREFIX " + "P" * 400 + " 1,200 " + "SUFFIX " + "S" * 400,
        )
        for _ in range(3)
    ]
    storyboard = storyboard.model_copy(update={"scenes": scenes})
    assets = await build_scene_visuals(storyboard, ingest_text("Ocean robots"), tmp_path)
    html = cinematic_motion_html(storyboard, assets)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page(viewport={"width": 1080, "height": 1920})
        server = await configure_offline_page(page, tmp_path)
        try:
            await page.set_content(localize_motion_html(html, tmp_path, server.base_url), wait_until="load")
            for scene in storyboard.scenes:
                timestamps = [scene.start + 0.7, scene.end - 0.2]
                if scene.end - scene.start > 5.8:
                    timestamps.insert(1, scene.start + 3.2)
                    timestamps.insert(2, scene.start + 5.6)
                for timestamp in timestamps:
                    await seek_and_settle(page, timestamp)
                    geometry = await page.evaluate("""
                        () => {
                          const scene = document.querySelector('.scene[data-active="true"]');
                          const rect = element => {
                            const box = element.getBoundingClientRect();
                            return {left:box.left, top:box.top, right:box.right, bottom:box.bottom};
                          };
                          const inside = (child, parent) => {
                            const a = rect(child), b = rect(parent);
                            return a.left >= b.left - 2 && a.right <= b.right + 2 &&
                              a.top >= b.top - 2 && a.bottom <= b.bottom + 2;
                          };
                          return {
                            critical: [...scene.querySelectorAll('[data-critical]')].map(rect),
                            overflow: document.documentElement.scrollWidth > 1080,
                            nodeCount: scene.querySelectorAll('.diagram-node[data-critical]').length,
                            nodesInside: [...scene.querySelectorAll('.diagram-node')].every(node =>
                              inside(node, scene.querySelector('.diagram-template')) &&
                              inside(node.querySelector('strong'), node)
                            ),
                            metricsInside: [...scene.querySelectorAll('.metric-card')].every(card =>
                              inside(card, scene.querySelector('.data-template')) &&
                              inside(card.querySelector('.metric-label'), card) &&
                              inside(card.querySelector('.metric-value'), card)
                            ),
                            calloutsInside: [...scene.querySelectorAll('.callout')].every(callout =>
                              inside(callout, scene.querySelector('.callout-rail'))
                            ),
                            kineticInside: [...scene.querySelectorAll('.kinetic-word')].every(word =>
                              inside(word, scene.querySelector('.kinetic-template')) &&
                              getComputedStyle(word).overflow === 'hidden'
                            ),
                          };
                        }
                    """)
                    assert geometry["overflow"] is False
                    for rect in geometry["critical"]:
                        assert rect["top"] >= 160, (scene.id, timestamp, rect)
                        assert rect["bottom"] <= 1580, (scene.id, timestamp, rect)
                        assert rect["left"] >= -2, (scene.id, timestamp, rect)
                        assert rect["right"] <= 1082, (scene.id, timestamp, rect)
                    assert geometry["nodesInside"] is True
                    assert geometry["metricsInside"] is True
                    assert geometry["calloutsInside"] is True
                    assert geometry["kineticInside"] is True
                    if scene.visual_type == "diagram":
                        assert geometry["nodeCount"] == 4
        finally:
            await browser.close()
            server.close()


@pytest.mark.asyncio
async def test_split_procedural_templates_do_not_overlap_headlines(tmp_path):
    from app.studio.cinematic import cinematic_motion_html

    storyboard = directed_storyboard()
    scenes = [scene.model_copy(deep=True) for scene in storyboard.scenes]
    scenes[3].layout = "split"
    scenes[4].layout = "split"
    storyboard = storyboard.model_copy(update={"scenes": scenes})
    assets = await build_scene_visuals(storyboard, ingest_text("Ocean robots"), tmp_path)
    html = cinematic_motion_html(storyboard, assets)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page(viewport={"width": 1080, "height": 1920})
        server = await configure_offline_page(page, tmp_path)
        try:
            await page.set_content(localize_motion_html(html, tmp_path, server.base_url), wait_until="load")
            for index in (3, 4):
                scene = storyboard.scenes[index]
                for timestamp in (scene.start + 0.8, scene.start + 3.3, scene.end - 0.2):
                    await seek_and_settle(page, timestamp)
                    separated = await page.evaluate("""
                        () => {
                          const scene = document.querySelector('.scene[data-active="true"]');
                          const headline = scene.querySelector('.headline').getBoundingClientRect();
                          const template = scene.querySelector('.kinetic-template, .diagram-template');
                          const elements = [template, ...scene.querySelectorAll('.diagram-node')];
                          return elements.every(element => {
                            const rect = element.getBoundingClientRect();
                            return rect.right <= headline.left || rect.left >= headline.right ||
                              rect.bottom <= headline.top || rect.top >= headline.bottom;
                          });
                        }
                    """)
                    assert separated is True, (scene.id, timestamp)
        finally:
            await browser.close()
            server.close()


@pytest.mark.asyncio
async def test_counters_animate_the_numeric_display_target(tmp_path):
    from app.studio.cinematic import cinematic_motion_html

    storyboard = directed_storyboard()
    scenes = [scene.model_copy(deep=True) for scene in storyboard.scenes]
    scenes[5].metrics = [
        SceneMetric(label="Compact", value=1200000, display="1.2M"),
        SceneMetric(label="Currency", value=999999, display="$1,200.50"),
        SceneMetric(label="Negative", value=-999, display="-42.5 units"),
    ]
    storyboard = storyboard.model_copy(update={"scenes": scenes})
    assets = await build_scene_visuals(storyboard, ingest_text("Ocean robots"), tmp_path)
    html = cinematic_motion_html(storyboard, assets)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page(viewport={"width": 1080, "height": 1920})
        server = await configure_offline_page(page, tmp_path)
        try:
            await page.set_content(localize_motion_html(html, tmp_path, server.base_url), wait_until="load")
            data = storyboard.scenes[5]
            for index, expected in enumerate(("0.8M", "$820.65", "-29.1 units")):
                await page.evaluate(f"window.seekTo({data.start + 0.35 + index * 0.12})")
                values = await page.locator('.scene[data-active="true"] .metric-value').all_inner_texts()
                assert values[index] == expected
            await page.evaluate(f"window.seekTo({data.end - 0.01})")
            assert await page.locator('.scene[data-active="true"] .metric-value').all_inner_texts() == [
                "1.2M", "$1,200.50", "-42.5 units",
            ]
        finally:
            await browser.close()
            server.close()


@pytest.mark.asyncio
async def test_procedural_primary_geometry_changes_by_phase(tmp_path):
    _, _, html = await cinematic_page(tmp_path)
    storyboard = directed_storyboard()
    cases = ((3, ".kinetic-word"), (4, ".diagram-node"), (5, ".metric-card"))
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page(viewport={"width": 1080, "height": 1920})
        server = await configure_offline_page(page, tmp_path)
        try:
            await page.set_content(localize_motion_html(html, tmp_path, server.base_url), wait_until="load")
            for index, selector in cases:
                scene = storyboard.scenes[index]
                bounds = []
                for timestamp in (scene.start + 0.8, scene.start + 3.3):
                    await seek_and_settle(page, timestamp)
                    bounds.append(await page.locator(f'.scene[data-active="true"] {selector}').first.evaluate(
                        "element => { const rect = element.getBoundingClientRect(); return {left:rect.left, top:rect.top, width:rect.width, height:rect.height}; }"
                    ))
                changes = [abs(bounds[1][key] - bounds[0][key]) for key in ("left", "top", "width", "height")]
                assert max(changes) >= 20, (scene.id, bounds)
        finally:
            await browser.close()
            server.close()
