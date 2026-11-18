import re
import warnings
from pathlib import Path

import cv2
import imagehash
import numpy as np
from PIL import Image, ImageOps

from app.schemas import AssetInput, AssetKind, AssetStatus, CuratedAsset

cv2.setNumThreads(1)

MAX_PERCEPTION_EDGE = 768
BLUR_THRESHOLD = 70
DUPLICATE_DISTANCE = 5


def _asset_id(index: int, filename: str) -> str:
    stem = re.sub(r"[^a-zA-Z0-9_-]+", "-", Path(filename).stem).strip("-")[:28]
    return f"{index:02d}-{stem or 'shot'}"


def _thumbnail(image: Image.Image, path: Path) -> None:
    preview = image.copy()
    preview.thumbnail((420, 420), Image.Resampling.LANCZOS)
    preview.save(path, "JPEG", quality=82, optimize=True)


def _perception(image: Image.Image, path: Path) -> Image.Image:
    resized = image.copy()
    resized.thumbnail((MAX_PERCEPTION_EDGE, MAX_PERCEPTION_EDGE), Image.Resampling.LANCZOS)
    resized.save(path, "JPEG", quality=86, optimize=True)
    return resized


def _blur_score(image: Image.Image) -> float:
    pixels = np.asarray(image.convert("L"))
    return float(cv2.Laplacian(pixels, cv2.CV_64F).var())


def prefilter_assets(project_dir: Path, inputs: list[AssetInput]) -> list[CuratedAsset]:
    derived = project_dir / "derived"
    derived.mkdir(parents=True, exist_ok=True)
    seen_hashes: list[imagehash.ImageHash] = []
    curated: list[CuratedAsset] = []

    for index, item in enumerate(inputs, start=1):
        asset_id = _asset_id(index, item.filename)
        kind = validate_kind(item.content_type)
        url = f"/media/{project_dir.name}/uploads/{item.path.name}"
        thumbnail_path = derived / f"{asset_id}_thumb.jpg"
        thumbnail_url = f"/media/{project_dir.name}/derived/{thumbnail_path.name}"
        asset = CuratedAsset(
            id=asset_id,
            filename=item.filename,
            kind=kind,
            source_path=item.path,
            thumbnail_path=thumbnail_path,
            thumbnail_url=thumbnail_url,
            url=url,
        )

        try:
            if kind == AssetKind.PHOTO:
                with warnings.catch_warnings():
                    warnings.simplefilter("error", Image.DecompressionBombWarning)
                    with Image.open(item.path) as opened:
                        image = ImageOps.exif_transpose(opened).convert("RGB")
                asset.width, asset.height = image.size
                digest = imagehash.phash(image)
                if any(digest - previous <= DUPLICATE_DISTANCE for previous in seen_hashes):
                    asset.status = AssetStatus.REJECTED
                    asset.rejection_reason = "Duplicate burst frame"
                else:
                    seen_hashes.append(digest)
                    if _blur_score(image) < BLUR_THRESHOLD:
                        asset.status = AssetStatus.REJECTED
                        asset.rejection_reason = "Too soft to survive the edit"
                perception_path = derived / f"{asset_id}_perception.jpg"
                _perception(image, perception_path)
                _thumbnail(image, thumbnail_path)
                asset.perception_path = perception_path
            else:
                capture = cv2.VideoCapture(str(item.path))
                if not capture.isOpened():
                    raise ValueError("Video could not be decoded")
                fps = capture.get(cv2.CAP_PROP_FPS) or 24
                frames = capture.get(cv2.CAP_PROP_FRAME_COUNT)
                asset.duration = float(frames / fps) if frames else None
                keyframes: list[Path] = []
                images: list[Image.Image] = []
                for keyframe_index, position in enumerate((0.25, 0.65), start=1):
                    capture.set(cv2.CAP_PROP_POS_MSEC, (asset.duration or 2) * position * 1000)
                    ok, frame = capture.read()
                    if not ok:
                        continue
                    frame_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    keyframe_path = derived / f"{asset_id}_keyframe_{keyframe_index}.jpg"
                    _perception(frame_image, keyframe_path)
                    keyframes.append(keyframe_path)
                    images.append(frame_image)
                capture.release()
                if not images:
                    raise ValueError("No video keyframes could be extracted")
                asset.width, asset.height = images[0].size
                asset.keyframe_paths = keyframes
                asset.perception_path = keyframes[0]
                _thumbnail(images[0], thumbnail_path)
                if asset.duration and asset.duration > 20:
                    asset.status = AssetStatus.REJECTED
                    asset.rejection_reason = "Clip exceeds the 20 second source limit"
                elif max(_blur_score(image) for image in images) < BLUR_THRESHOLD / 2:
                    asset.status = AssetStatus.REJECTED
                    asset.rejection_reason = "Clip is too soft to survive the edit"
        except (
            OSError,
            ValueError,
            cv2.error,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ) as error:
            asset.status = AssetStatus.REJECTED
            asset.rejection_reason = str(error)
            with Image.new("RGB", (640, 360), "#131317") as placeholder:
                _thumbnail(placeholder, thumbnail_path)

        curated.append(asset)
    return curated


def validate_kind(content_type: str) -> AssetKind:
    return AssetKind.VIDEO if content_type.startswith("video/") else AssetKind.PHOTO
