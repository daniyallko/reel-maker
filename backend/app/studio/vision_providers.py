import asyncio
import base64
import json
from pathlib import Path
from typing import Protocol

import httpx

from app.studio.vision import VisionAudit, validate_vision_audit

AUDIT_PROMPT = """
Score typography/contrast, safe-zone compliance, editorial craft, visual momentum,
narrative alignment, and asset relevance from 1-10. Return passed only if every score
is at least 8, plus scores and issues.
Keep text razor-sharp, left/grid-aligned, inside y:160-1580, with no overlap or broken
images. Check for distinct layouts and no static slideshow.
Check that scenes form a coherent narrative and every visible asset supports its scene.
Penalize irrelevant screenshots, abstract placeholder subjects, generic website copy, and repeated compositions.
Return only valid JSON.
"""


class ProviderError(RuntimeError):
    pass


class RetryableProviderError(ProviderError):
    def __init__(self, retry_after: float = 0):
        super().__init__("Provider temporarily unavailable")
        self.retry_after = max(0, retry_after)


class VisionProvider(Protocol):
    name: str

    async def audit(self, contact_sheet: Path, html: str) -> VisionAudit:
        ...


def _audit_from_text(text: str) -> VisionAudit:
    cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return validate_vision_audit(VisionAudit.model_validate_json(cleaned))
    except Exception as error:
        raise ProviderError("Provider returned an invalid audit") from error


def _retryable_status(status: int, retry_after: str | None) -> ProviderError:
    try:
        delay = float(retry_after or 0)
    except ValueError:
        delay = 0
    if status == 429 or status >= 500:
        return RetryableProviderError(delay)
    return ProviderError("Provider rejected the request")


class GeminiVisionProvider:
    def __init__(self, client, model: str):
        self.client = client
        self.model = model
        self.name = "gemini"

    async def audit(self, contact_sheet: Path, html: str) -> VisionAudit:
        from google.genai import types

        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model,
                contents=[AUDIT_PROMPT, types.Part.from_bytes(data=contact_sheet.read_bytes(), mime_type="image/png")],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=VisionAudit,
                ),
            )
            parsed = response.parsed if getattr(response, "parsed", None) else VisionAudit.model_validate_json(response.text)
            return validate_vision_audit(parsed if isinstance(parsed, VisionAudit) else VisionAudit.model_validate(parsed))
        except Exception as error:
            status = getattr(error, "code", None) or getattr(error, "status_code", None) or 0
            raise _retryable_status(status, None) from error


class OpenAICompatibleVisionProvider:
    def __init__(self, name: str, model: str, api_key: str, base_url: str, client: httpx.AsyncClient | None = None):
        self.name = name
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.client = client or httpx.AsyncClient(timeout=60)

    async def audit(self, contact_sheet: Path, html: str) -> VisionAudit:
        image = base64.b64encode(contact_sheet.read_bytes()).decode("ascii")
        response_format = {
            "type": "json_schema",
            "json_schema": {"name": "vision_audit", "strict": True, "schema": VisionAudit.model_json_schema()},
        } if self.name == "openrouter" else {"type": "json_object"}
        try:
            response = await self.client.post(
                self.base_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": AUDIT_PROMPT},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image}"}},
                        ],
                    }],
                    "response_format": response_format,
                    "max_tokens": 2000,
                },
            )
            if response.status_code >= 400:
                raise _retryable_status(response.status_code, response.headers.get("retry-after"))
            content = response.json()["choices"][0]["message"]["content"]
            if isinstance(content, list):
                content = "".join(part.get("text", "") for part in content)
            return _audit_from_text(content)
        except (httpx.TimeoutException, httpx.RequestError) as error:
            raise RetryableProviderError() from error
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
            raise ProviderError("Provider returned an invalid response") from error


class AnthropicVisionProvider:
    name = "anthropic"

    def __init__(self, model: str, api_key: str):
        self.model = model
        self.api_key = api_key

    async def audit(self, contact_sheet: Path, html: str) -> VisionAudit:
        try:
            import anthropic
        except ImportError as error:
            raise ProviderError("Anthropic SDK is not installed") from error
        client = anthropic.Anthropic(api_key=self.api_key)
        try:
            response = await asyncio.to_thread(
                client.messages.create,
                model=self.model,
                max_tokens=2000,
                output_config={"format": {"type": "json_schema", "schema": VisionAudit.model_json_schema()}},
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": base64.b64encode(contact_sheet.read_bytes()).decode("ascii"),
                            },
                        },
                        {"type": "text", "text": AUDIT_PROMPT},
                    ],
                }],
            )
            text = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
            return _audit_from_text(text)
        except anthropic.RateLimitError as error:
            raise RetryableProviderError() from error
        except anthropic.APIConnectionError as error:
            raise RetryableProviderError() from error
        except anthropic.APIStatusError as error:
            raise _retryable_status(error.status_code, None) from error
        except Exception as error:
            raise ProviderError("Anthropic audit failed") from error


class VisionProviderRouter:
    def __init__(self, providers: list[VisionProvider], timeout: float = 60):
        self.providers = providers
        self.timeout = timeout
        self.history: list[str] = []

    async def audit(self, contact_sheet: Path, html: str) -> VisionAudit:
        failures: list[str] = []
        for provider in self.providers:
            for attempt in (1, 2):
                try:
                    audit = validate_vision_audit(await asyncio.wait_for(provider.audit(contact_sheet, html), timeout=self.timeout))
                    self.history.append(f"{provider.name}/{getattr(provider, 'model', 'configured')} attempt {attempt}: audit accepted")
                    return audit
                except RetryableProviderError as error:
                    failures.append(provider.name)
                    self.history.append(f"{provider.name}/{getattr(provider, 'model', 'configured')} attempt {attempt}: retryable failure")
                    if attempt == 1:
                        await asyncio.sleep(error.retry_after)
                except Exception:
                    failures.append(provider.name)
                    self.history.append(f"{provider.name}/{getattr(provider, 'model', 'configured')} attempt {attempt}: invalid or unavailable response")
                    break
        raise RuntimeError(f"All configured vision providers failed: {', '.join(failures)}")


def build_vision_router(settings, gemini_client) -> VisionProviderRouter:
    from app.studio.providers import CORE_MODEL, FALLBACK_MODEL

    providers: list[VisionProvider] = []
    for name in settings.vision_provider_order.split(","):
        name = name.strip().lower()
        if name == "gemini" and settings.gemini_api_key:
            providers.extend([
                GeminiVisionProvider(gemini_client, CORE_MODEL),
                GeminiVisionProvider(gemini_client, FALLBACK_MODEL),
            ])
        elif name == "openrouter" and settings.openrouter_api_key:
            providers.append(OpenAICompatibleVisionProvider(
                "openrouter",
                settings.openrouter_vision_model,
                settings.openrouter_api_key,
                "https://openrouter.ai/api/v1/chat/completions",
            ))
        elif name == "groq" and settings.groq_api_key:
            providers.append(OpenAICompatibleVisionProvider(
                "groq",
                settings.groq_vision_model,
                settings.groq_api_key,
                "https://api.groq.com/openai/v1/chat/completions",
            ))
        elif name == "anthropic" and settings.anthropic_api_key:
            providers.append(AnthropicVisionProvider(settings.anthropic_vision_model, settings.anthropic_api_key))
    return VisionProviderRouter(providers)
