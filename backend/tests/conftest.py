from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from app.schemas import AssetInput, CuratedAsset


@pytest.fixture
def photo_input_factory(tmp_path: Path):
    def make(name: str, seed: int = 1, size=(1600, 900), blur: bool = False) -> AssetInput:
        rng = np.random.default_rng(seed)
        pixels = rng.integers(0, 255, (size[1], size[0], 3), dtype=np.uint8)
        image = Image.fromarray(pixels)
        if blur:
            from PIL import ImageFilter
            image = image.filter(ImageFilter.GaussianBlur(24))
        path = tmp_path / name
        image.save(path, "JPEG", quality=90)
        return AssetInput(filename=name, content_type="image/jpeg", path=path, size=path.stat().st_size)
    return make


@pytest.fixture
def curated_asset(tmp_path: Path):
    path = tmp_path / "hero.jpg"
    Image.new("RGB", (1200, 800), (80, 100, 120)).save(path)
    return CuratedAsset(
        id="01-hero",
        filename="hero.jpg",
        kind="photo",
        kept=True,
        hero=True,
        status="kept",
        source_path=path,
        perception_path=path,
    )
