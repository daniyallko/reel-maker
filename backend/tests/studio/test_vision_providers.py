import json
from pathlib import Path

import httpx
import pytest

from app.studio.vision import CriterionScore, VisionAudit
from app.studio.vision_providers import (
    AUDIT_PROMPT,
    OpenAICompatibleVisionProvider,
    RetryableProviderError,
    VisionProviderRouter,
    build_vision_router,
)

CRITERIA = (
    "typography/contrast",
    "safe-zone compliance",
    "editorial craft",
    "visual momentum",
    "narrative alignment",
    "asset relevance",
)


def audit(score: int = 8) -> VisionAudit:
    return VisionAudit(
        passed=score >= 8,
        issues=[],
        scores=[CriterionScore(criterion=name, score=score) for name in CRITERIA],
    )


class FakeProvider:
    def __init__(self, name, results):
        self.name = name
        self.results = list(results)
        self.calls = 0

    async def audit(self, contact_sheet, html):
        self.calls += 1
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


@pytest.mark.asyncio
async def test_router_retries_provider_failure_but_not_valid_low_score(tmp_path: Path):
    gemini = FakeProvider("gemini", [RetryableProviderError(retry_after=0), RetryableProviderError(retry_after=0)])
    openrouter = FakeProvider("openrouter", [audit(7)])
    groq = FakeProvider("groq", [audit(9)])
    router = VisionProviderRouter([gemini, openrouter, groq])
    result = await router.audit(tmp_path / "contact.png", "html")
    assert result.passed is False
    assert gemini.calls == 2
    assert openrouter.calls == 1
    assert groq.calls == 0


@pytest.mark.asyncio
async def test_router_uses_configured_provider_order_and_redacts_errors(tmp_path: Path):
    providers = [
        FakeProvider("gemini", [RuntimeError("secret-key")]),
        FakeProvider("openrouter", [RuntimeError("secret-key")]),
        FakeProvider("groq", [RuntimeError("secret-key")]),
        FakeProvider("anthropic", [audit(9)]),
    ]
    result = await VisionProviderRouter(providers).audit(tmp_path / "contact.png", "html")
    assert result.passed is True
    assert [provider.calls for provider in providers] == [1, 1, 1, 1]
    empty = VisionProviderRouter([])
    with pytest.raises(RuntimeError) as error:
        await empty.audit(tmp_path / "contact.png", "html")
    assert "secret-key" not in str(error.value)


@pytest.mark.asyncio
async def test_malformed_or_incomplete_audit_falls_back(tmp_path: Path):
    malformed = FakeProvider("gemini", [VisionAudit(passed=True, issues=[], scores=[])])
    fallback = FakeProvider("openrouter", [audit(8)])
    result = await VisionProviderRouter([malformed, fallback]).audit(tmp_path / "contact.png", "html")
    assert result.passed is True
    assert fallback.calls == 1


@pytest.mark.asyncio
async def test_retry_after_is_honored(tmp_path: Path, monkeypatch):
    sleeps = []
    async def fake_sleep(seconds):
        sleeps.append(seconds)
    monkeypatch.setattr("app.studio.vision_providers.asyncio.sleep", fake_sleep)
    provider = FakeProvider("gemini", [RetryableProviderError(retry_after=0.01), audit(8)])
    result = await VisionProviderRouter([provider]).audit(tmp_path / "contact.png", "html")
    assert result.passed is True
    assert sleeps == [0.01]


def test_shared_provider_prompt_covers_storyboard_relevance():
    for term in ("narrative alignment", "asset relevance", "irrelevant screenshots", "abstract placeholders"):
        assert term in AUDIT_PROMPT


@pytest.mark.asyncio
async def test_openai_compatible_provider_sends_model_image_and_schema(tmp_path: Path):
    contact = tmp_path / "contact.png"
    contact.write_bytes(b"png-data")
    captured = {}

    async def handler(request):
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={
            "choices": [{"message": {"content": json.dumps({
                "passed": True,
                "issues": [],
                "scores": [{"criterion": name, "score": 8} for name in CRITERIA],
            })}}],
        })

    provider = OpenAICompatibleVisionProvider(
        name="groq",
        model="qwen/qwen3.8-27b",
        api_key="secret",
        base_url="https://api.groq.com/openai/v1/chat/completions",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    result = await provider.audit(contact, "html")
    assert result.passed is True
    assert captured["body"]["model"] == "qwen/qwen3.8-27b"
    assert captured["body"]["messages"][0]["content"][0]["text"] == AUDIT_PROMPT
    assert captured["body"]["messages"][0]["content"][1]["image_url"]["url"].startswith("data:image/png;base64,")
    assert captured["body"]["response_format"]["type"] == "json_object"
    await provider.client.aclose()


def test_router_only_builds_configured_providers():
    from app.config import Settings

    settings = Settings(
        gemini_api_key=None,
        openrouter_api_key="openrouter",
        groq_api_key="groq",
        anthropic_api_key=None,
        vision_provider_order="gemini,openrouter,groq,anthropic",
    )
    router = build_vision_router(settings, gemini_client=object())
    assert [provider.name for provider in router.providers] == ["openrouter", "groq"]
