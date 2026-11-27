import json
from unittest.mock import AsyncMock

import httpx
import pytest

from app.config import Settings
from app.studio.fallback_providers import KIMI_ENDPOINT, KIMI_MODEL
from app.studio.providers import GeminiStudioProvider
from app.studio.sources import ingest_text
from app.studio.vision_providers import build_vision_router


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [200, 401])
async def test_kimi_precedes_research_and_review(status):
    settings = Settings(_env_file=None, moonshot_api_key="test")
    provider = GeminiStudioProvider("", settings)
    brief = ingest_text("How tides work")
    plan = {"topic": "Tides", "angle": "Gravity", "queries": ["tidal forces"]}
    provider._generate_research_schema = AsyncMock(return_value=None)

    def route(request):
        assert str(request.url) == KIMI_ENDPOINT
        assert request.headers["authorization"] == "Bearer test"
        assert json.loads(request.content)["model"] == KIMI_MODEL
        return httpx.Response(status, json={"choices": [{"message": {"content": json.dumps(plan)}}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(route)) as client:
        provider.kimi.client = client
        await provider.fallback.client.aclose()
        provider.fallback = None
        result = await provider.plan_research(brief, "deep_dive")
    if status == 200:
        assert result.topic == "Tides"
        provider._generate_research_schema.assert_not_awaited()
    else:
        provider._generate_research_schema.assert_awaited_once()
    assert build_vision_router(settings, None).providers[0].name == "moonshot"
