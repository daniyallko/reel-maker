from pathlib import Path

from PIL import ImageDraw, ImageFont

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
DISPLAY_FONT = BACKEND_DIR / "assets" / "fonts" / "Oswald-Bold.ttf"
UI_FONT = BACKEND_DIR / "assets" / "fonts" / "PlusJakartaSans-Regular.ttf"
SYSTEM_DISPLAY = Path("/usr/share/fonts/truetype/liberation/LiberationSansNarrow-Bold.ttf")
SYSTEM_UI = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")


def font_path(display: bool = True) -> str:
    candidates = (DISPLAY_FONT, SYSTEM_DISPLAY) if display else (UI_FONT, SYSTEM_UI)
    return str(next(path for path in candidates if path.exists()))


def load_font(size: int, display: bool = True) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(font_path(display), size=size)


def text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> int:
    return draw.textbbox((0, 0), text, font=font)[2]


def split_word(draw: ImageDraw.ImageDraw, word: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    pieces: list[str] = []
    current = ""
    for character in word:
        candidate = current + character
        if current and text_width(draw, candidate, font) > width:
            pieces.append(current)
            current = character
        else:
            current = candidate
    if current:
        pieces.append(current)
    return pieces


def wrap_to_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        if text_width(draw, word, font) > width:
            if current:
                lines.append(current)
                current = ""
            pieces = split_word(draw, word, font, width)
            lines.extend(pieces[:-1])
            current = pieces[-1] if pieces else ""
            continue
        candidate = f"{current} {word}".strip()
        if current and text_width(draw, candidate, font) > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def ellipsize(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, width: int) -> str:
    result = text
    while result and text_width(draw, f"{result}…", font) > width:
        result = result[:-1]
    return f"{result}…" if result else "…"


def fit_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    max_size: int,
    min_size: int,
    max_lines: int,
    display: bool = True,
) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    for size in range(max_size, min_size - 1, -2):
        candidate = load_font(size, display)
        lines = wrap_to_width(draw, text, candidate, max_width)
        if len(lines) <= max_lines and all(text_width(draw, line, candidate) <= max_width for line in lines):
            return candidate, lines
    fallback = load_font(min_size, display)
    lines = wrap_to_width(draw, text, fallback, max_width)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = ellipsize(draw, lines[-1], fallback, max_width)
    return fallback, lines


def draw_centered_lines(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    font: ImageFont.FreeTypeFont,
    center_x: int,
    top: int,
    fill: str,
    spacing: int,
) -> int:
    y = top
    for line in lines:
        box = draw.textbbox((0, 0), line, font=font)
        width = box[2] - box[0]
        draw.text((center_x - width / 2, y), line, font=font, fill=fill)
        y += box[3] - box[1] + spacing
    return y
