import json

import httpx
import pytest

from app.studio.kimi_only import ask


@pytest.mark.asyncio
@pytest.mark.parametrize("finish", ["stop", "length"])
async def test_kimi_stream_returns_only_completed_visible_content(finish):
    def respond(request):
        assert request.url.host == "api.moonshot.ai"
        assert json.loads(request.content)["stream"] is True
        events = [{"delta": {"reasoning_content": "internal"}},
                  {"delta": {"content": "Visible result"}, "finish_reason": finish}]
        return httpx.Response(200, text="".join(
            "data: " + json.dumps({"choices": [event]}) + "\n\n" for event in events
        ) + "data: [DONE]\n\n")
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        if finish == "stop":
            assert await ask(client, "dummy", "test") == "Visible result"
        else:
            with pytest.raises(ValueError, match="finish_reason=length"):
                await ask(client, "dummy", "test")


@pytest.mark.asyncio
async def test_kimi_auth_failure_is_terminal():
    seen = []
    def reject(request):
        seen.append(request.url.host)
        return httpx.Response(401, json={"error": {"type": "invalid_authentication"}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(reject)) as client:
        with pytest.raises(RuntimeError, match="401"):
            await ask(client, "dummy", "test")
    assert seen == ["api.moonshot.ai"]
