import base64
import asyncio
import json
import mimetypes
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Literal, TypeVar

import httpx
from PIL import Image, ImageDraw
from pydantic import BaseModel, Field, model_validator

Schema = TypeVar("Schema", bound=BaseModel)

COLOR = r"^#[0-9a-fA-F]{6}$"


class VectorShape(BaseModel):
    kind: Literal["rect", "circle", "polygon", "line"]
    x: float = 0
    y: float = 0
    width: float = 0
    height: float = 0
    radius: float = 0
    points: list[list[float]] = Field(default_factory=list)
    fill: str = Field(pattern=COLOR)
    opacity: int = Field(default=220, ge=0, le=255)
    stroke_width: int = Field(default=4, ge=1, le=100)

    @model_validator(mode="before")
    @classmethod
    def open_polygon_is_line(cls, data):
        if isinstance(data, dict) and data.get("kind") == "polygon" and len(data.get("points", [])) == 2:
            return {**data, "kind": "line"}
        return data

    @model_validator(mode="after")
    def valid_geometry(self):
        if self.kind == "circle" and self.radius <= 0:
            raise ValueError("Circle requires positive radius")
        if self.kind == "rect" and (self.width <= 0 or self.height <= 0):
            raise ValueError("Rectangle requires positive size")
        if self.kind == "polygon" and len(self.points) < 3:
            raise ValueError("Polygon requires three points")
        if self.kind == "line" and len(self.points) != 2:
            raise ValueError("Line requires two points")
        return self


class VectorArtwork(BaseModel):
    background: str = Field(default="#05060a", pattern=COLOR)
    shapes: list[VectorShape] = Field(default_factory=list, max_length=12)


class OpenAIStudioFallback:
    """Text and SVG generation fallback for unavailable Gemini studio models."""

    def __init__(self, settings, client: httpx.AsyncClient | None = None):
        self.settings = settings
        self.client = client or httpx.AsyncClient(timeout=90)
        self.history: list[str] = []

    def _providers(self):
        if self.settings.openrouter_api_key:
            yield (
                "openrouter",
                self.settings.openrouter_vision_model,
                self.settings.openrouter_api_key,
                "https://openrouter.ai/api/v1/chat/completions",
            )
        if self.settings.groq_api_key:
            yield (
                "groq",
                self.settings.groq_vision_model,
                self.settings.groq_api_key,
                "https://api.groq.com/openai/v1/chat/completions",
            )

    @staticmethod
    def _image_parts(image_paths: list[Path]) -> list[dict]:
        parts = []
        for path in image_paths[:4]:
            mime_type = mimetypes.guess_type(path.name)[0] or "image/png"
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
            parts.append({"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded}"}})
        return parts

    @staticmethod
    def _error_detail(response: httpx.Response) -> str:
        try:
            payload = response.json()
            detail = payload.get("error", {}).get("message") or payload.get("message") or response.text
        except json.JSONDecodeError:
            detail = response.text
        return str(detail)[:200]

    async def _request(self, prompt: str, image_paths: list[Path], schema=None, max_tokens: int = 8000):
        for name, model, api_key, url in self._providers():
            response_format = None
            if schema is not None:
                response_format = {
                    "type": "json_schema",
                    "json_schema": {"name": schema.__name__.lower(), "strict": True, "schema": schema.model_json_schema()},
                } if name == "openrouter" else {"type": "json_object"}
            text = f"{prompt}\nReturn only valid JSON." if schema is not None else prompt
            payload = {
                "model": model,
                "messages": [{
                    "role": "user",
                    "content": [{"type": "text", "text": text}, *self._image_parts(image_paths)],
                }],
                "max_tokens": max_tokens,
            }
            if response_format is not None:
                payload["response_format"] = response_format
            for attempt in (1, 2):
                try:
                    response = await self.client.post(url, headers={"Authorization": f"Bearer {api_key}"}, json=payload)
                    if response.status_code >= 400:
                        self.history.append(f"{name}/{model}: HTTP {response.status_code} - {self._error_detail(response)}")
                        if response.status_code == 429 and attempt == 1:
                            try:
                                delay = min(60.0, float(response.headers.get("retry-after", "10")))
                            except ValueError:
                                delay = 10.0
                            self.history.append(f"{name}/{model}: retrying in {delay:.2f}s")
                            await asyncio.sleep(max(0, delay))
                            continue
                        break
                    content = response.json()["choices"][0]["message"]["content"]
                    if isinstance(content, list):
                        content = "".join(part.get("text", "") for part in content)
                    if not isinstance(content, str) or not content.strip():
                        self.history.append(f"{name}/{model}: empty response")
                        break
                    self.history.append(f"{name}/{model}: response accepted")
                    return content, name
                except (httpx.HTTPError, KeyError, IndexError, TypeError, json.JSONDecodeError):
                    self.history.append(f"{name}/{model}: request failed")
                    break
        return None

    async def generate_json(self, prompt: str, schema: type[Schema], image_paths: list[Path]) -> tuple[Schema, str] | None:
        repair_prompt = prompt
        for attempt in (1, 2):
            result = await self._request(repair_prompt, image_paths, schema=schema)
            if result is None:
                return None
            content, provider = result
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.IGNORECASE)
            try:
                parsed = schema.model_validate_json(cleaned)
                return parsed, provider
            except (ValueError, TypeError) as error:
                self.history.append(f"{provider}: invalid structured response")
                if attempt == 1:
                    repair_prompt = f"{prompt}\nPrevious response failed schema validation: {error}\nReturn only corrected valid JSON."
        return None

    @staticmethod
    def _validated_svg(content: str) -> str:
        cleaned = re.sub(r"^```(?:svg|xml)?\s*|\s*```$", "", content.strip(), flags=re.IGNORECASE)
        document = re.search(r"<svg\b[\s\S]*</svg>", cleaned, flags=re.IGNORECASE)
        if document:
            cleaned = document.group(0)
        root = ET.fromstring(cleaned)
        if root.tag.rsplit("}", 1)[-1].lower() != "svg":
            raise ValueError("Artwork is not SVG")
        if "@import" in cleaned.lower() or re.search(r"url\(\s*['\"]?\s*(?:https?:|//)", cleaned, flags=re.IGNORECASE):
            raise ValueError("External SVG stylesheet")
        for element in root.iter():
            if element.tag.rsplit("}", 1)[-1].lower() in {"script", "foreignobject", "iframe", "object", "embed"}:
                raise ValueError("Unsafe SVG element")
            for name, value in element.attrib.items():
                if name.rsplit("}", 1)[-1].lower().startswith("on"):
                    raise ValueError("SVG event handler")
                if name.rsplit("}", 1)[-1].lower() in {"href", "src"} and not value.startswith("data:"):
                    raise ValueError("External SVG resource")
        return cleaned

    @staticmethod
    def _rgba(hex_color: str, opacity: int) -> tuple[int, int, int, int]:
        return (
            int(hex_color[1:3], 16),
            int(hex_color[3:5], 16),
            int(hex_color[5:7], 16),
            opacity,
        )

    @classmethod
    def _render_vector(cls, content: str, output: Path) -> None:
        artwork = VectorArtwork.model_validate_json(content)
        image = Image.new("RGBA", (1080, 1920), cls._rgba(artwork.background, 255))
        draw = ImageDraw.Draw(image)
        for shape in artwork.shapes:
            fill = cls._rgba(shape.fill, shape.opacity)
            if shape.kind == "circle":
                draw.ellipse((shape.x - shape.radius, shape.y - shape.radius, shape.x + shape.radius, shape.y + shape.radius), fill=fill)
            elif shape.kind == "rect":
                draw.rounded_rectangle((shape.x, shape.y, shape.x + shape.width, shape.y + shape.height), radius=min(40, shape.height / 4), fill=fill)
            elif shape.kind == "polygon":
                draw.polygon([tuple(point) for point in shape.points], fill=fill)
            else:
                draw.line([tuple(point) for point in shape.points], fill=fill, width=shape.stroke_width)
        output.parent.mkdir(parents=True, exist_ok=True)
        image.convert("RGB").save(output, "PNG", optimize=True)

    async def _generate_vector_art(self, prompt: str, references: list[Path], output: Path) -> bool:
        result = await self._request(
            f"""{prompt}
Return JSON with background (#RRGGBB) and at most 12 shapes. Each shape has kind
rect|circle|polygon|line, fill (#RRGGBB), opacity 0-255, and geometry:
rect x/y/width/height; circle x/y/radius; polygon or line points [[x,y],...].
Make a meaningful, scene-specific editorial illustration, not generic lines.
""",
            references,
            schema=VectorArtwork,
            max_tokens=1000,
        )
        if result is None:
            return False
        content, provider = result
        try:
            self._render_vector(content, output)
            self.history.append(f"{provider}: vector artwork rendered")
            return True
        except (ValueError, TypeError, OSError) as error:
            self.history.append(f"{provider}: invalid vector artwork - {error}")
            return False

    async def generate_svg(self, prompt: str, references: list[Path], output: Path) -> bool:
        result = await self._request(
            f"""{prompt}
Create one original, scene-specific 1080x1920 vertical SVG artwork. Use rich layered
vector shapes, meaningful editorial composition, depth, masks, and a restrained palette.
Use at most 12 SVG elements so the response stays compact and complete.
Do not copy a website screenshot, use abstract line placeholders, render words/letters/
numbers, load external resources, or include scripts. Return only valid SVG with an
explicit width="1080" height="1920" and matching viewBox.
""",
            references,
            max_tokens=1000,
        )
        if result is None:
            return False
        content, provider = result
        try:
            svg = self._validated_svg(content)
            output.parent.mkdir(parents=True, exist_ok=True)
            from playwright.async_api import async_playwright

            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch()
                page = await browser.new_page(viewport={"width": 1080, "height": 1920})
                await page.set_content(f"<!doctype html><html><body style='margin:0'>{svg}</body></html>", wait_until="load")
                await page.screenshot(path=str(output))
                await browser.close()
            return output.exists()
        except (ET.ParseError, ValueError, OSError, RuntimeError) as error:
            self.history.append(f"{provider}: invalid or unrasterizable SVG - {error}; preview={content[:200]!r}")
            return await self._generate_vector_art(prompt, references, output)
