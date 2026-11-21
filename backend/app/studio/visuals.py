from collections.abc import Awaitable, Callable
from pathlib import Path

from PIL import Image, ImageDraw

from app.media.poster import cover
from app.studio.harvest import media_url
from app.studio.schemas import SourceBundle, Storyboard, StoryScene, StudioAsset

ArtGenerator = Callable[[str, list[Path], Path], Awaitable[bool]]


def build_visual_prompt(prompt: str) -> str:
    return f"""{prompt}
Do not render words, headlines, captions, letters, numbers, or fake UI copy.
Leave calm negative space for a separate motion typography layer. Use the supplied
screenshots only as brand, material, lighting, and product-interface references.
"""


def _asset(project_dir: Path, path: Path, asset_id: str, kind: str, label: str) -> StudioAsset:
    return StudioAsset(
        id=asset_id,
        kind=kind,
        label=label,
        url=media_url(project_dir, path),
        mime_type="image/png",
        local_path=path,
    )


def _save_procedural(path: Path, index: int) -> None:
    accents = ((72, 96, 190), (22, 128, 118), (160, 88, 54), (116, 72, 160))
    accent = accents[index % len(accents)]
    canvas = Image.new("RGBA", (1080, 1920), (5, 6, 10, 255))
    draw = ImageDraw.Draw(canvas)
    for band in range(12):
        shade = 12 + band * 3
        draw.rectangle((0, band * 160, 1080, (band + 1) * 160), fill=(shade // 3, shade // 2, shade + 8, 255))
    for step in range(4):
        offset = (index % 3) * 52 + step * 138
        draw.rounded_rectangle(
            (72 + offset, 280 + step * 190, 620 + offset, 390 + step * 190),
            radius=24,
            fill=(*accent, 70 + step * 25),
            outline=(255, 255, 255, 45),
            width=2,
        )
    draw.ellipse((650, 180, 1180, 710), outline=(*accent, 180), width=12)
    canvas.convert("RGB").save(path, "PNG", optimize=True)


def _save_source(source: Path, path: Path, index: int) -> None:
    with Image.open(source) as opened:
        image = opened.convert("RGB")
    canvas = cover(image, (1080, 1920), focus_y=0.25 + (index % 4) * 0.12)
    canvas.save(path, "PNG", optimize=True)


def _save_source_or_procedural(source: Path | None, path: Path, index: int) -> None:
    if source is not None:
        try:
            _save_source(source, path, index)
            return
        except (OSError, ValueError):
            pass
    _save_procedural(path, index)


def _save_cover(harvest: SourceBundle | None, path: Path) -> None:
    primary = _source_image(harvest, 0) or _screenshot(harvest, 0)
    secondary = _screenshot(harvest, 0) or _source_image(harvest, 1)
    if primary is None:
        _save_procedural(path, 3)
        return
    try:
        with Image.open(primary) as opened:
            top = cover(opened.convert("RGB"), (1080, 960), focus_y=0.3)
        if secondary is not None:
            with Image.open(secondary) as opened:
                bottom = cover(opened.convert("RGB"), (1080, 960), focus_y=0.65)
        else:
            with Image.open(primary) as opened:
                bottom = cover(opened.convert("RGB"), (1080, 960), focus_y=0.8)
        canvas = Image.new("RGB", (1080, 1920))
        canvas.paste(top, (0, 0))
        canvas.paste(bottom, (0, 960))
        ImageDraw.Draw(canvas).rectangle((0, 954, 1080, 966), fill=(5, 6, 10))
        canvas.save(path, "PNG", optimize=True)
    except (OSError, ValueError):
        _save_procedural(path, 3)


def _source_image(harvest: SourceBundle | None, index: int) -> Path | None:
    paths = harvest.image_paths if harvest else []
    return paths[index % len(paths)] if paths else None


def _screenshot(harvest: SourceBundle | None, index: int) -> Path | None:
    paths = harvest.screenshots if harvest else []
    return paths[index % len(paths)] if paths else None


def _scene_kind(scene: StoryScene) -> str:
    if scene.visual_type == "screenshot":
        return "screenshot"
    if scene.visual_type == "source_image":
        return "image"
    return "art"


def _save_scene_fallback(scene: StoryScene, harvest: SourceBundle | None, path: Path, index: int) -> None:
    source = None
    if scene.visual_type == "screenshot":
        source = _screenshot(harvest, index)
    elif scene.visual_type == "source_image":
        source = _source_image(harvest, index)
    elif scene.visual_type == "generated_art":
        source = _source_image(harvest, index) or _screenshot(harvest, index)
    _save_source_or_procedural(source, path, index)


def _scene_asset(scene: StoryScene, project_dir: Path, path: Path) -> StudioAsset:
    return _asset(project_dir, path, f"scene-{scene.id}", _scene_kind(scene), scene.headline)


def _references(harvest: SourceBundle | None) -> list[Path]:
    return [*harvest.image_paths, *harvest.screenshots] if harvest else []


def build_fallback_visuals(storyboard: Storyboard, harvest: SourceBundle | None, project_dir: Path) -> list[StudioAsset]:
    output = project_dir / "visuals"
    output.mkdir(parents=True, exist_ok=True)
    assets = []
    for index, scene in enumerate(storyboard.scenes):
        path = output / f"scene-{index:02d}.png"
        _save_scene_fallback(scene, harvest, path, index)
        assets.append(_scene_asset(scene, project_dir, path))
    cover_path = output / "thumbnail.png"
    _save_cover(harvest, cover_path)
    assets.append(_asset(project_dir, cover_path, "thumbnail", "thumbnail", "Cover"))
    return assets


async def build_scene_visuals(
    storyboard: Storyboard,
    harvest: SourceBundle | None,
    project_dir: Path,
    generate_art: ArtGenerator | None = None,
) -> list[StudioAsset]:
    output = project_dir / "visuals"
    output.mkdir(parents=True, exist_ok=True)
    references = _references(harvest)
    assets = []
    for index, scene in enumerate(storyboard.scenes):
        path = output / f"scene-{index:02d}.png"
        generated = False
        if scene.visual_type == "generated_art" and generate_art is not None:
            try:
                generated = await generate_art(build_visual_prompt(scene.visual_prompt), references, path)
            except Exception:
                generated = False
        if not generated or not path.exists():
            _save_scene_fallback(scene, harvest, path, index)
        assets.append(_scene_asset(scene, project_dir, path))

    cover_path = output / "thumbnail.png"
    generated = False
    if generate_art is not None:
        try:
            prompt = build_visual_prompt(f"Vertical cover artwork for {storyboard.title}")
            generated = await generate_art(prompt, references, cover_path)
        except Exception:
            generated = False
    if not generated or not cover_path.exists():
        _save_cover(harvest, cover_path)
    assets.append(_asset(project_dir, cover_path, "thumbnail", "thumbnail", "Cover"))
    return assets
