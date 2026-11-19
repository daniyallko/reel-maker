from pathlib import Path

import pytest

from app.studio.providers import (
    CORE_MODEL,
    TTS_MODEL,
    VISUAL_MODEL,
    GeminiStudioProvider,
    MockStudioProvider,
)
from app.studio.schemas import HarvestResult, SourceBundle, SourceCitation
from app.studio.sources import ingest_text
from app.studio.urls import sample_site_url


def test_requested_model_ids_and_thinking():
    assert CORE_MODEL == "gemini-4-hydrogen"
    assert VISUAL_MODEL == "gemini-nano-banana-2.1"
    assert TTS_MODEL == "gemini-3.8-flash-tts"
    provider = GeminiStudioProvider("key")
    assert provider._core_config().thinking_config.thinking_level.value == "HIGH"


def test_visual_config_enables_search_and_vertical_images():
    config = GeminiStudioProvider("key")._visual_config()
    assert config.response_modalities == ["TEXT", "IMAGE"]
    assert config.image_config.aspect_ratio == "9:16"
    search = config.tools[0].google_search.search_types
    assert search.web_search is not None
    assert search.image_search is not None


def test_tts_text_and_style_are_separate():
    provider = GeminiStudioProvider("key")
    contents, config = provider._tts_request("Say exactly this", "Charon", "Authoritative, measured")
    assert contents[0].text == "Say exactly this"
    assert contents[0].speech_metadata.style == "Authoritative, measured"
    assert config.speech_config.voice_config.prebuilt_voice_config.voice_name == "Charon"
    assert provider.tts_api_version == "v1beta"


def test_storyboard_prompt_requires_evidence_for_every_claim():
    from app.studio.providers import build_storyboard_prompt

    harvest = HarvestResult(
        source_url="https://example.com",
        title="Example",
        palette=[],
        fonts=[],
        dom_copy="Example builds shared planning tools.",
        assets=[],
        scroll_video=Path("unused"),
    )
    prompt = build_storyboard_prompt(harvest, [SourceCitation(url="https://example.com", title="Example", claim="Shared planning tools")], "tech_launch", "Fenrir")
    assert "Use only the supplied evidence" in prompt
    assert "Never introduce a platform, technical problem, code filename, integration, metric, customer, or capability absent from that evidence" in prompt
    assert "Every scene must cite its supporting evidence in source_refs" in prompt
    assert "Headlines must contain at most 42 characters" in prompt


def test_visual_prompt_excludes_embedded_typography():
    from app.studio.providers import build_visual_prompt

    prompt = build_visual_prompt("A three-dimensional product interface")
    assert "Do not render words, headlines, captions, letters, numbers, or fake UI copy" in prompt
    assert "Leave calm negative space for a separate motion typography layer" in prompt
    assert "A three-dimensional product interface" in prompt


@pytest.mark.asyncio
async def test_mock_storyboard_and_audio(tmp_path: Path):
    provider = MockStudioProvider()
    storyboard = await provider.write_storyboard(None, [], "launch", "Fenrir")
    assert storyboard.duration == 32
    assert len(storyboard.scenes) == 4
    assert storyboard.scenes[0].start == 0
    assert storyboard.scenes[-1].end == 32
    assert storyboard.sources
    audio = await provider.synthesize(storyboard, tmp_path)
    assert audio.voice_path.exists()
    assert len(audio.durations) == 4
    assert audio.preview_url.startswith("/media/")


@pytest.mark.asyncio
async def test_partial_gemini_tts_falls_back_to_one_consistent_edge_voice(tmp_path: Path, monkeypatch):
    provider = GeminiStudioProvider("key")
    storyboard = await MockStudioProvider().write_storyboard(None, [], "launch", "Fenrir")

    async def partial_gemini(transcript, voice, style):
        return b"gemini" if transcript == storyboard.scenes[0].narration else None

    async def edge_voice(transcript, voice, style):
        return b"edge"

    async def fake_produce(storyboard, project_dir, tts_call=None):
        assert tts_call is not None
        return [await tts_call(scene.narration, storyboard.voice, storyboard.speech_style) for scene in storyboard.scenes]

    monkeypatch.setattr(provider, "_synthesize_line", partial_gemini)
    monkeypatch.setattr(provider, "_edge_synthesize_line", edge_voice)
    monkeypatch.setattr("app.studio.providers.produce_audio", fake_produce)
    result = await provider.synthesize(storyboard, tmp_path)
    assert result == [b"edge", b"edge", b"edge", b"edge"]


def test_text_storyboard_uses_user_evidence_and_inline_citations():
    from app.studio.providers import fallback_storyboard

    bundle = ingest_text("A rehabilitation robot helps patients walk safely.")
    storyboard = fallback_storyboard(bundle, bundle.citations, "cinematic", "Fenrir")
    assert "rehabilitation robot" in storyboard.title
    assert "Orbit" not in storyboard.title
    assert storyboard.sources[0].url == "inline://text"
    assert storyboard.sources[0].claim.startswith("A rehabilitation robot")


def test_fallback_storyboard_avoids_generic_template_narration():
    from app.studio.providers import fallback_storyboard

    bundle = ingest_text("Ocean robots collect plastic. They map currents. Their batteries recharge at sea. Fleets coordinate cleanup.")
    storyboard = fallback_storyboard(bundle, bundle.citations, "deep_dive", "Fenrir")
    script = " ".join(scene.narration for scene in storyboard.scenes)
    assert "This is" not in script
    assert "Behind the landing page" not in script
    assert "The takeaway is simple" not in script
    assert "They map currents" in script
    assert "Their batteries recharge at sea" in script
    assert all(len(scene.headline) <= 42 for scene in storyboard.scenes)


@pytest.mark.asyncio
async def test_storyboard_receives_uploaded_image_evidence(tmp_path: Path):
    from PIL import Image
    from app.studio.providers import mock_storyboard

    image_path = tmp_path / "evidence.png"
    Image.new("RGB", (32, 48), "#182030").save(image_path)
    bundle = ingest_text("1 source image: evidence.png").model_copy(update={"image_paths": [image_path]})
    provider = GeminiStudioProvider("key")
    captured = {}

    class Models:
        @staticmethod
        def generate_content(**kwargs):
            captured.update(kwargs)
            return type("Response", (), {"parsed": mock_storyboard("launch", "Fenrir")})()

    provider.client = type("Client", (), {"models": Models})()
    await provider.write_storyboard(bundle, bundle.citations, "launch", "Fenrir")
    contents = captured["contents"]
    assert isinstance(contents, list)
    assert any(getattr(part, "inline_data", None) for part in contents[1:])
