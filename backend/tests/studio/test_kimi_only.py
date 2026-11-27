import json

import httpx
import pytest

from app.studio.kimi_only import _unwrap_shot_body, ask, compose_film_html
from app.studio.motion import sanitize_motion_html
from app.studio.schemas import SourceCitation, Storyboard, StoryScene


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


def test_compose_film_html_and_unwrap_shot_body():
    body_a = "function drawShot(ctx) {\n  ctx.fillStyle = P.accent;\n  ctx.fillRect(100, 400, 100, 100);\n}"
    body_b = "ctx.fillStyle = P.ink;\nctx.fillRect(200, 500, 80, 80);"
    assert _unwrap_shot_body(body_a).startswith("ctx.fillStyle = P.accent;")
    board = Storyboard(
        title="Test Film",
        style="deep_dive",
        voice="Fenrir",
        duration=32,
        speech_style="Conversational documentary",
        scenes=[
            StoryScene(id=f"shot-{i+1}", start=i*8, end=(i+1)*8, headline=f"Beat {i+1}", narration="One short line of narration.", visual_prompt="motion", source_refs=[0], layout="full_bleed")
            for i in range(4)
        ],
        sources=[SourceCitation(url="inline://brief", title="Brief", claim="Test")],
        directed_motion=True,
    )
    html = sanitize_motion_html(compose_film_html(board, {"palette": {"bg": "#101820", "accent": "#00d4ff"}}, [body_a, body_b, body_a, body_b]))
    assert "window.seekTo" in html
    assert "#101820" in html
    assert "#00d4ff" in html
    assert "drawShot_0" in html and "drawShot_3" in html
