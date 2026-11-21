from pathlib import Path

import pytest
from PIL import Image

from app.studio.sources import ingest_text
from app.studio.visuals import build_scene_visuals
from tests.studio.directed_fixtures import directed_storyboard


def media_bundle(tmp_path: Path, *, uploaded: bool = True, screenshot: bool = True):
    bundle = ingest_text("Ocean robots")
    image_paths = []
    screenshots = []
    if uploaded:
        upload = tmp_path / "upload.png"
        Image.new("RGB", (1080, 1920), "#204060").save(upload)
        image_paths.append(upload)
    if screenshot:
        capture = tmp_path / "capture.png"
        Image.new("RGB", (1080, 1920), "#602040").save(capture)
        screenshots.append(capture)
    return bundle.model_copy(update={"image_paths": image_paths, "screenshots": screenshots})


def center_pixel(asset) -> tuple[int, int, int]:
    with Image.open(asset.local_path) as image:
        return image.convert("RGB").getpixel((540, 960))


@pytest.mark.asyncio
async def test_scene_assets_are_unique_and_cover_is_separate(tmp_path):
    calls = []

    async def generate(prompt, references, path):
        calls.append(prompt)
        Image.new("RGB", (1080, 1920), "#204060").save(path)
        return True

    storyboard = directed_storyboard()
    assets = await build_scene_visuals(storyboard, ingest_text("Ocean robots"), tmp_path, generate)
    assert len(assets) == 7
    assert [asset.id for asset in assets[:-1]] == [f"scene-{scene.id}" for scene in storyboard.scenes]
    assert assets[-1].kind == "thumbnail"
    assert len({asset.local_path for asset in assets}) == 7
    assert len(calls) == 2  # one generated_art scene plus cover


@pytest.mark.asyncio
async def test_failed_art_uses_local_procedural_fallback(tmp_path):
    async def fail(*_):
        return False

    assets = await build_scene_visuals(directed_storyboard(), ingest_text("No source images"), tmp_path, fail)
    assert len(assets) == 7
    assert all(asset.local_path.exists() for asset in assets)
    assert all("orbit-hero" not in str(asset.local_path) for asset in assets)


@pytest.mark.asyncio
async def test_source_image_prefers_uploaded_image_over_screenshot(tmp_path):
    bundle = media_bundle(tmp_path)
    assets = await build_scene_visuals(directed_storyboard(), bundle, tmp_path)
    source_image = next(asset for asset in assets if asset.id == "scene-collect")
    assert center_pixel(source_image) == (32, 64, 96)


@pytest.mark.asyncio
async def test_screenshots_are_not_reused_for_source_image_scenes(tmp_path):
    bundle = media_bundle(tmp_path, uploaded=False)
    assets = await build_scene_visuals(directed_storyboard(), bundle, tmp_path)
    screenshot = next(asset for asset in assets if asset.id == "scene-hook")
    source_image = next(asset for asset in assets if asset.id == "scene-collect")
    assert center_pixel(screenshot) == (96, 32, 64)
    assert center_pixel(source_image) != (96, 32, 64)


@pytest.mark.asyncio
async def test_procedural_scenes_do_not_call_art_provider(tmp_path):
    storyboard = directed_storyboard()
    scenes = [scene.model_copy(update={"visual_type": "kinetic_type"}) for scene in storyboard.scenes]
    storyboard = storyboard.model_copy(update={"scenes": scenes})
    calls = []

    async def generate(prompt, references, path):
        calls.append(prompt)
        Image.new("RGB", (1080, 1920), "#204060").save(path)
        return True

    assets = await build_scene_visuals(storyboard, ingest_text("Ocean robots"), tmp_path, generate)
    assert len(assets) == 7
    assert len(calls) == 1  # cover only


@pytest.mark.asyncio
async def test_cover_failure_does_not_replace_successful_scene_art(tmp_path):
    calls = []

    async def fail_cover(prompt, references, path):
        calls.append(prompt)
        if len(calls) == 1:
            Image.new("RGB", (1080, 1920), "#204060").save(path)
            return True
        return False

    assets = await build_scene_visuals(directed_storyboard(), ingest_text("Ocean robots"), tmp_path, fail_cover)
    generated = next(asset for asset in assets if asset.id == "scene-sort")
    assert center_pixel(generated) == (32, 64, 96)
    assert center_pixel(assets[-1]) != (32, 64, 96)
    assert all(asset.local_path.exists() for asset in assets)


@pytest.mark.asyncio
async def test_generated_art_failure_uses_screenshot_when_no_upload_exists(tmp_path):
    async def fail(*_):
        return False

    bundle = media_bundle(tmp_path, uploaded=False, screenshot=True)
    assets = await build_scene_visuals(directed_storyboard(), bundle, tmp_path, fail)
    generated = next(asset for asset in assets if asset.id == "scene-sort")
    assert center_pixel(generated) == (96, 32, 64)


@pytest.mark.asyncio
async def test_cover_uses_distinct_source_composition(tmp_path):
    bundle = media_bundle(tmp_path, uploaded=True, screenshot=True)
    assets = await build_scene_visuals(directed_storyboard(), bundle, tmp_path)
    with Image.open(assets[-1].local_path) as image:
        top = image.convert("RGB").getpixel((540, 240))
        bottom = image.convert("RGB").getpixel((540, 1680))
    assert top == (32, 64, 96)
    assert bottom == (96, 32, 64)
