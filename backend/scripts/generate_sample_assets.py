from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
DESTINATION = ROOT / "assets" / "sample" / "uploads"
W, H = 1080, 1350

SCENES = [
    ("01-coast-road.jpg", "THE WRONG TURN", (28, 50, 66), (216, 153, 92)),
    ("02-motel-arrival.jpg", "ARRIVAL / 21:47", (22, 20, 34), (181, 82, 66)),
    ("03-cabin-crew.jpg", "THE WHOLE CREW", (42, 56, 49), (218, 177, 104)),
    ("04-cliff-swim.jpg", "NO ONE DRIVES HOME", (20, 55, 69), (95, 169, 169)),
    ("05-diner-stop.jpg", "COFFEE / 03:12", (38, 28, 30), (206, 103, 71)),
    ("06-gas-station.jpg", "LAST EXIT", (19, 24, 40), (211, 163, 75)),
    ("07-sunset-toast.jpg", "ONE MORE NIGHT", (60, 35, 49), (231, 142, 80)),
    ("08-sunday-silence.jpg", "SUNDAY, EVENTUALLY", (42, 47, 54), (178, 157, 124)),
]


def font(size: int):
    path = "/usr/share/fonts/truetype/liberation/LiberationSansNarrow-Bold.ttf"
    return ImageFont.truetype(path, size)


def person(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float, color: tuple[int, int, int]):
    draw.ellipse((x - 28 * scale, y - 185 * scale, x + 28 * scale, y - 129 * scale), fill=color)
    draw.polygon([(x - 46 * scale, y - 125 * scale), (x + 46 * scale, y - 125 * scale), (x + 66 * scale, y), (x - 66 * scale, y)], fill=color)


def main():
    DESTINATION.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(17)
    for index, (filename, caption, dark, light) in enumerate(SCENES):
        y = np.linspace(0, 1, H)[:, None, None]
        top = np.array(dark)[None, None, :]
        bottom = np.array(light)[None, None, :]
        pixels = np.broadcast_to(top * (1 - y) + bottom * y, (H, W, 3)).copy()
        pixels += rng.normal(0, 4.5, pixels.shape)
        image = Image.fromarray(np.clip(pixels, 0, 255).astype(np.uint8))
        draw = ImageDraw.Draw(image)
        draw.ellipse((770 - index * 37, 210 + index * 16, 920 - index * 37, 360 + index * 16), fill=(239, 193, 115))
        draw.polygon([(0, 780), (180, 490 + index * 18), (410, 750), (650, 420 + index * 8), (1080, 790), (1080, 1350), (0, 1350)], fill=tuple(max(0, channel - 15) for channel in dark))
        draw.polygon([(0, 910), (280, 690), (510, 870), (820, 610), (1080, 880), (1080, 1350), (0, 1350)], fill=tuple(max(0, channel - 28) for channel in dark))
        if index in (0, 5):
            draw.polygon([(390, 1350), (490, 760), (610, 760), (810, 1350)], fill=(35, 35, 39))
            for road_y in range(830, 1320, 130):
                draw.rectangle((552, road_y, 566, road_y + 62), fill=(220, 189, 119))
        if index in (1, 4, 5):
            draw.rectangle((160, 600, 890, 950), fill=(18, 19, 23), outline=(216, 168, 82), width=6)
            for window in range(5):
                draw.rectangle((210 + window * 135, 690, 290 + window * 135, 790), fill=(218, 149, 73))
        if index in (2, 6, 7):
            for person_index in range(4):
                person(draw, 300 + person_index * 155, 1030 + (person_index % 2) * 24, 1.2, (10, 12, 15))
        if index == 3:
            draw.rectangle((0, 890, 1080, 1350), fill=(17, 65, 77))
            for wave in range(12):
                draw.arc((wave * 110 - 80, 940 + wave % 3 * 55, wave * 110 + 210, 1010 + wave % 3 * 55), 5, 175, fill=(116, 173, 170), width=4)
        draw.rectangle((48, 54, 64, 72), fill=(229, 72, 77))
        draw.text((82, 50), f"CUTLINE ARCHIVE / FRAME {index + 1:02d}", font=font(25), fill=(243, 240, 232))
        draw.text((48, 1210), caption, font=font(54), fill=(243, 240, 232))
        draw.text((50, 1280), "BIG SUR / SUMMER 2026", font=font(22), fill=(212, 168, 83))
        image = image.filter(ImageFilter.UnsharpMask(radius=1, percent=70, threshold=3))
        image.save(DESTINATION / filename, "JPEG", quality=91, optimize=True)
    print(f"Generated {len(SCENES)} sample frames in {DESTINATION}")


if __name__ == "__main__":
    main()
