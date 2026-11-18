from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from app.media.text import draw_centered_lines, fit_text, load_font, wrap_to_width
from app.schemas import CastCredit, CuratedAsset, TrailerEDL

PAPER = "#F3F0E8"
GOLD = "#D4A853"
CRIMSON = "#E5484D"


def cover(image: Image.Image, size: tuple[int, int], focus_y: float = 0.45) -> Image.Image:
    target_w, target_h = size
    scale = max(target_w / image.width, target_h / image.height)
    resized = image.resize(
        (round(image.width * scale), round(image.height * scale)), Image.Resampling.LANCZOS
    )
    left = max(0, (resized.width - target_w) // 2)
    top = max(0, min(resized.height - target_h, round((resized.height - target_h) * focus_y)))
    return resized.crop((left, top, left + target_w, top + target_h))


def cinematic_grade(image: Image.Image) -> Image.Image:
    pixels = np.asarray(image.convert("RGB")).astype(np.float32) / 255
    luminance = pixels.mean(axis=2, keepdims=True)
    shadows = np.clip(1 - luminance * 2, 0, 1)
    highlights = np.clip(luminance * 2 - 0.55, 0, 1)
    pixels += shadows * np.array([-0.035, 0.035, 0.055])
    pixels += highlights * np.array([0.055, 0.018, -0.035])
    pixels = np.clip(pixels * 1.06, 0, 1)
    rng = np.random.default_rng(42)
    pixels += rng.normal(0, 0.012, pixels.shape)
    return Image.fromarray((np.clip(pixels, 0, 1) * 255).astype(np.uint8))


def source_image(asset: CuratedAsset) -> Image.Image:
    path = asset.source_path if asset.kind == "photo" else asset.perception_path
    if path is None:
        raise ValueError(f"Asset {asset.id} has no renderable frame")
    return Image.open(path).convert("RGB")


class PosterArtDirector:
    def __init__(self, use_rembg: bool = True):
        self.use_rembg = use_rembg

    def render(
        self,
        project_dir: Path,
        project_id: str,
        edl: TrailerEDL,
        assets: list[CuratedAsset],
    ) -> Path:
        output_dir = project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        hero = next((asset for asset in assets if asset.hero), None) or next(
            asset for asset in assets if asset.kept
        )
        source = source_image(hero)
        background = cover(source, (1080, 1920))
        background = background.filter(ImageFilter.GaussianBlur(3))
        background = ImageEnhance.Brightness(background).enhance(0.72)

        if self.use_rembg:
            try:
                import onnxruntime
                from rembg import new_session, remove

                options = onnxruntime.SessionOptions()
                options.intra_op_num_threads = 1
                options.inter_op_num_threads = 1
                options.enable_cpu_mem_arena = False
                session = new_session(
                    "u2net",
                    sess_opts=options,
                    providers=["CPUExecutionProvider"],
                )
                subject_source = source.copy()
                subject_source.thumbnail((768, 768), Image.Resampling.LANCZOS)
                subject = remove(subject_source, session=session)
                subject = cover(subject.convert("RGBA"), (1080, 1500))
                background = background.convert("RGBA")
                background.alpha_composite(subject, (0, 260))
                background = background.convert("RGB")
            except Exception:
                background = cover(source, (1080, 1920))

        poster = cinematic_grade(background).convert("RGBA")
        shade = Image.new("RGBA", poster.size)
        shade_pixels = np.zeros((1920, 1080, 4), dtype=np.uint8)
        for y in range(1920):
            lower = max(0, (y - 930) / 990)
            upper = max(0, 1 - y / 480)
            shade_pixels[y, :, :] = (5, 5, 8, int(min(235, lower * 220 + upper * 150)))
        shade = Image.fromarray(shade_pixels, "RGBA")
        poster = Image.alpha_composite(poster, shade)
        draw = ImageDraw.Draw(poster)

        eyebrow = load_font(27, display=False)
        draw.text((64, 64), "CUTLINE PICTURES PRESENTS", font=eyebrow, fill=GOLD)
        draw.line((64, 112, 1016, 112), fill=(243, 240, 232, 100), width=1)

        title_font, title_lines = fit_text(draw, edl.title.upper(), 940, 148, 76, 3)
        title_y = 1110 if len(title_lines) < 3 else 1030
        bottom = draw_centered_lines(draw, title_lines, title_font, 540, title_y, PAPER, 4)
        tagline_font = load_font(29, display=False)
        tagline_lines = wrap_to_width(draw, edl.tagline.upper(), tagline_font, 850)[:3]
        bottom = draw_centered_lines(draw, tagline_lines, tagline_font, 540, bottom + 22, GOLD, 10)

        badge_y = bottom + 28
        draw.rounded_rectangle((336, badge_y, 744, badge_y + 58), radius=2, fill=CRIMSON)
        badge_font = load_font(25)
        badge = "98% CERTIFIED CHAOTIC"
        badge_width = draw.textbbox((0, 0), badge, font=badge_font)[2]
        draw.text((540 - badge_width / 2, badge_y + 13), badge, font=badge_font, fill=PAPER)

        names = "  ·  ".join(credit.name.upper() for credit in edl.cast)
        billing = (
            f"CUTLINE PICTURES PRESENTS A WEEKEND PRODUCTION  {names}  "
            f"CASTING BY THE GROUP CHAT  MUSIC BY THE OPEN ROAD  "
            "EDITED ON LOCATION  NO GOOD DECISIONS WERE MADE"
        )
        for billing_size in range(22, 7, -2):
            billing_font = load_font(billing_size)
            billing_lines = wrap_to_width(draw, billing, billing_font, 960)
            if len(billing_lines) <= 7:
                break
        draw_centered_lines(draw, billing_lines, billing_font, 540, 1660, PAPER, 5)
        draw.text((64, 1840), "COMING SOON TO A GROUP CHAT NEAR YOU", font=load_font(22), fill=GOLD)

        path = output_dir / "poster.png"
        poster.convert("RGB").save(path, "PNG", optimize=True)
        return path


def render_cast_cards(
    project_dir: Path,
    project_id: str,
    edl: TrailerEDL,
    assets: list[CuratedAsset],
) -> list[CastCredit]:
    output_dir = project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    asset_map = {asset.id: asset for asset in assets}
    credits: list[CastCredit] = []
    for index, credit in enumerate(edl.cast):
        asset = asset_map.get(credit.asset_id or "") or next(
            (candidate for candidate in assets if candidate.kept), None
        )
        if asset is None:
            continue
        card = cinematic_grade(cover(source_image(asset), (1080, 1350))).convert("RGBA")
        overlay = Image.new("RGBA", card.size)
        pixels = np.zeros((1350, 1080, 4), dtype=np.uint8)
        for y in range(1350):
            alpha = int(max(0, (y - 650) / 700) * 225)
            pixels[y, :, :] = (5, 5, 8, alpha)
        card = Image.alpha_composite(card, Image.fromarray(pixels, "RGBA"))
        draw = ImageDraw.Draw(card)
        draw.text((64, 58), "MEET THE CAST", font=load_font(26), fill=GOLD)
        draw.text((64, 94), f"CHARACTER {index + 1:02d}", font=load_font(20, False), fill=PAPER)
        role_lines = wrap_to_width(draw, credit.role.upper(), load_font(38), 900)[:2]
        role_y = draw_centered_lines(draw, role_lines, load_font(38), 540, 970, GOLD, 6)
        name_font, name_lines = fit_text(draw, credit.name.upper(), 940, 104, 54, 2)
        draw_centered_lines(draw, name_lines, name_font, 540, role_y + 12, PAPER, 2)
        draw.text((64, 1284), "FREEZE FRAME / CUTLINE", font=load_font(20, False), fill=PAPER)
        filename = f"cast-{index + 1:02d}.png"
        path = output_dir / filename
        card.convert("RGB").save(path, "PNG", optimize=True)
        credits.append(
            credit.model_copy(
                update={"card_path": path, "card_url": f"/media/{project_id}/output/{filename}"}
            )
        )
    return credits
