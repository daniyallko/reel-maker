from pathlib import Path
from types import SimpleNamespace
import json

import httpx
import pytest
from PIL import Image

from app.studio.fallback_providers import OpenAIStudioFallback
from app.studio.providers import GeminiStudioProvider, fallback_storyboard
from app.studio.research import fallback_research_plan, fallback_research_report
from app.studio.schemas import ResearchPlan, Storyboard
from app.studio.sources import ingest_text


def fallback_settings(**overrides):
    values = {
        "openrouter_api_key": "openrouter-key",
        "openrouter_vision_model": "openrouter-model",
        "groq_api_key": "groq-key",
        "groq_vision_model": "groq-model",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.mark.asyncio
async def test_openrouter_then_groq_generates_structured_research():
    calls = []

    async def handler(request):
        calls.append(request)
        if "openrouter.ai" in str(request.url):
            return httpx.Response(503, json={"error": {"message": "rate limited"}})
        return httpx.Response(200, json={
            "choices": [{"message": {"content": '{"topic":"Ocean robots","angle":"Systems","queries":["ocean robots"]}'}}]
        })

    fallback = OpenAIStudioFallback(
        fallback_settings(),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    result = await fallback.generate_json("Plan ocean research", ResearchPlan, [])
    assert result is not None
    plan, provider = result
    assert plan.queries == ["ocean robots"]
    assert provider == "groq"
    assert len(calls) == 2
    assert calls[1].content.__contains__(b"groq-model")
    groq_payload = json.loads(calls[1].content)
    assert "Return only valid JSON" in groq_payload["messages"][0]["content"][0]["text"]
    assert fallback.history == [
        "openrouter/openrouter-model: HTTP 503 - rate limited",
        "groq/groq-model: response accepted",
    ]


@pytest.mark.asyncio
async def test_rate_limit_retries_with_retry_after(monkeypatch):
    calls = []
    sleeps = []

    async def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, headers={"retry-after": "0.01"}, json={"error": {"message": "slow down"}})
        return httpx.Response(200, json={
            "choices": [{"message": {"content": '{"topic":"Ocean robots","angle":"Systems","queries":["ocean robots"]}'}}]
        })

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr("app.studio.fallback_providers.asyncio.sleep", fake_sleep)
    fallback = OpenAIStudioFallback(
        fallback_settings(groq_api_key=None),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    result = await fallback.generate_json("Plan research", ResearchPlan, [])
    assert result is not None
    assert len(calls) == 2
    assert sleeps == [0.01]
    assert "openrouter/openrouter-model: retrying in 0.01s" in fallback.history


@pytest.mark.asyncio
async def test_rate_limit_honors_long_retry_after(monkeypatch):
    calls = []
    sleeps = []

    async def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, headers={"retry-after": "45"}, json={"error": {"message": "minute quota"}})
        return httpx.Response(200, json={
            "choices": [{"message": {"content": '{"topic":"Ocean robots","angle":"Systems","queries":["ocean robots"]}'}}]
        })

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr("app.studio.fallback_providers.asyncio.sleep", fake_sleep)
    fallback = OpenAIStudioFallback(
        fallback_settings(groq_api_key=None),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    result = await fallback.generate_json("Plan research", ResearchPlan, [])
    assert result is not None
    assert sleeps == [45.0]



@pytest.mark.asyncio
async def test_invalid_structured_response_retries_once_with_validation_error():
    calls = []

    async def handler(request):
        calls.append(request)
        content = '{"title":"bad"}' if len(calls) == 1 else '{"topic":"Ocean robots","angle":"Systems","queries":["ocean robots"]}'
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    fallback = OpenAIStudioFallback(
        fallback_settings(groq_api_key=None),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    result = await fallback.generate_json("Plan research", ResearchPlan, [])
    assert result is not None
    assert len(calls) == 2
    repair_payload = json.loads(calls[1].content)
    assert "validation" in repair_payload["messages"][0]["content"][0]["text"].lower()


@pytest.mark.asyncio
async def test_null_provider_content_is_skipped():
    async def handler(request):
        if "openrouter.ai" in str(request.url):
            return httpx.Response(200, json={"choices": [{"message": {"content": None}}]})
        return httpx.Response(200, json={
            "choices": [{"message": {"content": '{"topic":"Ocean robots","angle":"Systems","queries":["ocean robots"]}'}}]
        })

    fallback = OpenAIStudioFallback(
        fallback_settings(),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    result = await fallback.generate_json("Plan research", ResearchPlan, [])
    assert result is not None
    assert result[1] == "groq"



@pytest.mark.asyncio
async def test_openrouter_svg_fallback_renders_real_png(tmp_path):
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920" viewBox="0 0 1080 1920"><rect width="1080" height="1920" fill="#000000"/><circle cx="540" cy="960" r="400" fill="#0066ff"/></svg>'

    async def handler(request):
        return httpx.Response(200, json={"choices": [{"message": {"content": f"Artwork follows:\n{svg}\nEnd of artwork"}}]})

    fallback = OpenAIStudioFallback(
        fallback_settings(groq_api_key=None),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    output = tmp_path / "scene.png"
    assert await fallback.generate_svg("Ocean cleanup robot vector artwork", [], output) is True
    with Image.open(output) as image:
        assert image.size == (1080, 1920)
        assert image.convert("RGB").getpixel((540, 960)) == (0, 102, 255)


@pytest.mark.asyncio
async def test_invalid_svg_is_rejected_without_output(tmp_path):
    async def handler(request):
        return httpx.Response(200, json={"choices": [{"message": {"content": "<svg><script>alert(1)</script></svg>"}}]})

    fallback = OpenAIStudioFallback(
        fallback_settings(groq_api_key=None),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    output = tmp_path / "invalid.png"
    assert await fallback.generate_svg("Artwork", [], output) is False
    assert not output.exists()


@pytest.mark.asyncio
async def test_svg_requests_are_bounded_to_groq_output_limit():
    requests = []

    async def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": "not svg"}}]})

    fallback = OpenAIStudioFallback(
        fallback_settings(groq_api_key=None),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    await fallback.generate_svg("Artwork", [], Path("/tmp/unused.png"))
    assert all(payload["max_tokens"] <= 1000 for payload in requests)
    assert "at most 12 SVG elements" in requests[0]["messages"][0]["content"][0]["text"]


@pytest.mark.asyncio
async def test_non_svg_response_uses_structured_vector_art(tmp_path):
    calls = []

    async def handler(request):
        calls.append(request)
        if len(calls) == 1:
            content = "I cannot produce SVG for this request."
        else:
            content = '{"background":"#000000","shapes":[{"kind":"polygon","points":[[0,800],[1000,800]],"fill":"#0066ff","opacity":255},{"kind":"circle","x":540,"y":960,"radius":400,"fill":"#0066ff","opacity":255}]}'
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    fallback = OpenAIStudioFallback(
        fallback_settings(groq_api_key=None),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    output = tmp_path / "vector.png"
    assert await fallback.generate_svg("Ocean robot artwork", [], output) is True
    assert len(calls) == 2
    with Image.open(output) as image:
        assert image.convert("RGB").getpixel((540, 960)) == (0, 102, 255)


@pytest.mark.asyncio
@pytest.mark.parametrize("svg", [
    '<svg xmlns="http://www.w3.org/2000/svg"><style>@import url("https://evil.example/x.css");</style></svg>',
    '<svg xmlns="http://www.w3.org/2000/svg"><rect width="10" height="10" onload="alert(1)"/></svg>',
])
async def test_svg_external_resources_and_handlers_are_rejected(tmp_path, svg):
    async def handler(request):
        return httpx.Response(200, json={"choices": [{"message": {"content": svg}}]})

    fallback = OpenAIStudioFallback(
        fallback_settings(groq_api_key=None),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    output = tmp_path / "unsafe.png"
    assert await fallback.generate_svg("Artwork", [], output) is False
    assert not output.exists()


@pytest.mark.asyncio
async def test_gemini_failure_uses_injected_text_and_visual_fallbacks(tmp_path):
    bundle = ingest_text("Ocean cleanup robots")
    plan = fallback_research_plan(bundle, "deep_dive")
    report = fallback_research_report(bundle, plan, [])
    storyboard = fallback_storyboard(bundle, bundle.citations, "deep_dive", "Fenrir", research=report)

    class Fallback:
        def __init__(self):
            self.json_calls = []
            self.svg_calls = []

        async def generate_json(self, prompt, schema, image_paths):
            self.json_calls.append(schema)
            if schema is ResearchPlan:
                return plan, "groq"
            if schema is Storyboard:
                return storyboard, "groq"
            return report.model_copy(update={"provider": "groq"}), "groq"

        async def generate_svg(self, prompt, references, path):
            self.svg_calls.append(prompt)
            Image.new("RGB", (1080, 1920), "#0066ff").save(path)
            return True

    fallback = Fallback()
    provider = GeminiStudioProvider("key", fallback=fallback)
    provider.client = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **_: (_ for _ in ()).throw(RuntimeError("unavailable"))))

    assert await provider.plan_research(bundle, "deep_dive") == plan
    assert (await provider.synthesize_research(bundle, plan, [])).provider == "groq"
    assert await provider.write_storyboard(bundle, bundle.citations, "deep_dive", "Fenrir", research=report) == storyboard
    output = tmp_path / "art.png"
    assert await provider._generate_one_visual("Ocean robot art", [], output) is True
    assert output.exists()
    assert ResearchPlan in fallback.json_calls
    assert Storyboard in fallback.json_calls
    assert fallback.svg_calls


def test_deterministic_storyboard_prefers_source_media_and_typed_scenes(tmp_path):
    capture = tmp_path / "capture.png"
    upload = tmp_path / "upload.png"
    Image.new("RGB", (1080, 1920), "#602040").save(capture)
    Image.new("RGB", (1080, 1920), "#204060").save(upload)
    bundle = ingest_text("Ocean robots collect plastic. They map currents. Fleets coordinate cleanup. Batteries recharge at sea.").model_copy(
        update={"screenshots": [capture], "image_paths": [upload]}
    )
    plan = fallback_research_plan(bundle, "deep_dive")
    report = fallback_research_report(bundle, plan, [])
    storyboard = fallback_storyboard(bundle, bundle.citations, "deep_dive", "Fenrir", research=report)
    types = {scene.visual_type for scene in storyboard.scenes}
    assert "generated_art" not in types
    assert "screenshot" in types
    assert "source_image" in types

    bare = ingest_text("Ocean robots collect plastic. They map currents. Fleets coordinate cleanup. Batteries recharge at sea.")
    bare_report = fallback_research_report(bare, fallback_research_plan(bare, "deep_dive"), [])
    bare_storyboard = fallback_storyboard(bare, bare.citations, "deep_dive", "Fenrir", research=bare_report)
    assert all(scene.visual_type != "generated_art" for scene in bare_storyboard.scenes)
    assert all(len(scene.callouts) >= 2 for scene in bare_storyboard.scenes if scene.visual_type == "diagram")


def test_screenshot_only_fallback_mixes_motion_graphics(tmp_path):
    capture = tmp_path / "capture.png"
    Image.new("RGB", (1080, 1920), "#602040").save(capture)
    bundle = ingest_text("Ocean robots collect plastic. They map currents. Fleets coordinate cleanup. Batteries recharge at sea.").model_copy(
        update={"screenshots": [capture]}
    )
    report = fallback_research_report(bundle, fallback_research_plan(bundle, "deep_dive"), [])
    storyboard = fallback_storyboard(bundle, bundle.citations, "deep_dive", "Fenrir", research=report)
    types = {scene.visual_type for scene in storyboard.scenes}
    assert "screenshot" in types
    assert "kinetic_type" in types
    assert "diagram" in types


@pytest.mark.asyncio
async def test_fallback_provider_history_reaches_backend_events():
    from app.studio.graph import emit_fallback_history

    class Events:
        def __init__(self):
            self.items = []

        async def emit(self, agent, status, message, progress):
            self.items.append((agent, message, progress))

    provider = SimpleNamespace(fallback=SimpleNamespace(history=[
        "openrouter/model: HTTP 503",
        "groq/model: response accepted",
    ]))
    events = Events()
    start = await emit_fallback_history(events, "researcher", provider, 0, 22)
    assert start == 2
    assert events.items == [
        ("researcher", "Provider response / openrouter/model: HTTP 503", 22),
        ("researcher", "Provider response / groq/model: response accepted", 22),
    ]


def test_storyboard_prompt_lists_exact_direction_vocabulary():
    from app.studio.providers import build_storyboard_prompt

    bundle = ingest_text("Ocean cleanup robots")
    prompt = build_storyboard_prompt(bundle, bundle.citations, "deep_dive", "Fenrir")
    for text in (
        "screenshot | source_image | generated_art | kinetic_type | diagram | data",
        "hero | split | bento | full_bleed",
        "push_in | pull_out | pan_left | pan_right | static",
        "clip_reveal | stagger | counter_roll | path_draw | parallax",
        "cut | wipe | whip | dissolve",
        "whoosh | pop | bass_drop | none",
        "callouts must be strings",
        "metrics must contain label, numeric value, and display",
        "Scene IDs must be unique strings",
        "source_refs must be integer indexes into sources, never URLs",
    ):
        assert text in prompt
