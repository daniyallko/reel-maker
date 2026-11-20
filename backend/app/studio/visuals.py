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
    canvas = Image.new("RGBA", (1080, 1920), (5, 6, 10, 255))
    draw = ImageDraw.Draw(canvas)
    accent = (94, 106, 210, 180)
    for line in range(7):
        y = 260 + line * 190 + index * 36
        draw.line((72, y, 1008 - line * 72, y - 120), fill=accent, width=3)
    draw.rectangle((72 + index * 36, 300, 620 + index * 36, 980), outline=(255, 255, 255, 45), width=2)
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
    elif scene.visual_type in {"source_image", "generated_art"}:
        source = _source_image(harvest, index)
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
    _save_source_or_procedural(_source_image(harvest, len(assets)), cover_path, len(assets))
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
        _save_source_or_procedural(_source_image(harvest, len(assets)), cover_path, len(assets))
    assets.append(_asset(project_dir, cover_path, "thumbnail", "thumbnail", "Cover"))
    return assets
