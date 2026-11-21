import pytest
from pydantic import ValidationError

from app.studio.providers import (
    build_storyboard_prompt,
    fallback_storyboard,
    mock_storyboard,
    portfolio_storyboard,
)
from app.studio.schemas import (
    EvidenceClaim,
    ResearchReport,
    SourceCitation,
    Storyboard,
)
from app.studio.sources import ingest_text
from tests.studio.directed_fixtures import directed_storyboard


def test_direction_supports_six_typed_scenes():
    storyboard = directed_storyboard()
    assert len(storyboard.scenes) == 6
    assert [(scene.start, scene.end) for scene in storyboard.scenes] == [
        (0, 2),
        (2, 7),
        (7, 12),
        (12, 18),
        (18, 25),
        (25, 32),
    ]
    assert [scene.visual_type for scene in storyboard.scenes] == [
        "screenshot",
        "source_image",
        "generated_art",
        "kinetic_type",
        "diagram",
        "data",
    ]
    assert [scene.sfx for scene in storyboard.scenes] == [
        "pop",
        "whoosh",
        "bass_drop",
        "none",
        "none",
        "none",
    ]
    assert all(scene.source_refs == [0] for scene in storyboard.scenes)
    assert storyboard.scenes[-1].metrics[0].model_dump() == {
        "label": "Collected",
        "value": 1200,
        "display": "1,200 kg",
    }
    assert storyboard.scenes[-2].callouts == ["Collect", "Sort", "Recycle"]
    assert "content" not in storyboard.model_dump()["sources"][0]


def test_direction_requires_valid_evidence_and_visual_payloads():
    payload = directed_storyboard().model_dump()
    payload["scenes"][0]["source_refs"] = []
    with pytest.raises(ValidationError):
        Storyboard.model_validate(payload)

    payload = directed_storyboard().model_dump()
    payload["scenes"][-1]["metrics"] = []
    with pytest.raises(ValidationError):
        Storyboard.model_validate(payload)

    payload = directed_storyboard().model_dump()
    payload["scenes"][0]["source_refs"] = [1]
    with pytest.raises(ValidationError):
        Storyboard.model_validate(payload)

    payload = directed_storyboard().model_dump()
    payload["scenes"][-2]["callouts"] = ["Collect"]
    with pytest.raises(ValidationError):
        Storyboard.model_validate(payload)


@pytest.mark.parametrize("scene_count", [3, 9])
def test_direction_rejects_scene_counts_outside_four_to_eight(scene_count):
    payload = directed_storyboard().model_dump()
    if scene_count == 3:
        scenes = payload["scenes"][:3]
        scenes[0].update(start=0, end=2)
        scenes[1].update(start=2, end=12)
        scenes[2].update(start=12, end=32)
    else:
        scenes = []
        for index in range(scene_count):
            scene = dict(payload["scenes"][0])
            scene.update(
                id=f"scene-{index}",
                start=index * 32 / scene_count,
                end=(index + 1) * 32 / scene_count,
            )
            scenes.append(scene)
    payload["scenes"] = scenes
    with pytest.raises(ValidationError):
        Storyboard.model_validate(payload)


@pytest.mark.parametrize("bpm", [0, -1])
def test_direction_rejects_nonpositive_bpm(bpm):
    payload = directed_storyboard().model_dump()
    payload["bpm"] = bpm
    with pytest.raises(ValidationError):
        Storyboard.model_validate(payload)


def test_direction_rejects_duplicate_scene_ids():
    payload = directed_storyboard().model_dump()
    payload["scenes"][1]["id"] = payload["scenes"][0]["id"]
    with pytest.raises(ValidationError):
        Storyboard.model_validate(payload)


def test_direction_rejects_scenes_shorter_than_1_8_seconds():
    payload = directed_storyboard().model_dump()
    payload["scenes"][0]["end"] = 1.7
    payload["scenes"][1]["start"] = 1.7
    with pytest.raises(ValidationError):
        Storyboard.model_validate(payload)


def test_direction_rejects_noncontiguous_scenes():
    payload = directed_storyboard().model_dump()
    payload["scenes"][1]["start"] = 2.2
    with pytest.raises(ValidationError):
        Storyboard.model_validate(payload)


def test_direction_rejects_headlines_longer_than_42_characters():
    payload = directed_storyboard().model_dump()
    payload["scenes"][0]["headline"] = "X" * 43
    with pytest.raises(ValidationError):
        Storyboard.model_validate(payload)


def test_legacy_scenes_receive_safe_direction_defaults():
    payload = directed_storyboard().model_dump()
    scene = payload["scenes"][0]
    for field in (
        "visual_type",
        "layout",
        "camera",
        "animation",
        "transition",
        "sfx",
        "callouts",
        "metrics",
    ):
        scene.pop(field)
    storyboard = Storyboard.model_validate(payload)
    scene = storyboard.scenes[0]
    assert scene.visual_type == "generated_art"
    assert scene.layout == "hero"
    assert scene.camera == "push_in"
    assert scene.animation == "clip_reveal"
    assert scene.transition == "cut"
    assert scene.sfx == "none"
    assert scene.callouts == []
    assert scene.metrics == []


def test_fallback_narrative_uses_research_claims():
    bundle = ingest_text("Ocean robots")
    sources = [
        SourceCitation(url="https://example.com/fleet", title="Fleet", claim="Fleet evidence"),
        SourceCitation(url="https://example.com/cycle", title="Cycle", claim="Cycle evidence"),
    ]
    claims = [
        EvidenceClaim(text="Robots collect floating plastic.", source_refs=[0]),
        EvidenceClaim(text="Sensors map ocean currents.", source_refs=[0]),
        EvidenceClaim(text="Recovered plastic is sorted.", source_refs=[1]),
        EvidenceClaim(text="Sorted material is recycled.", source_refs=[1]),
    ]
    research = ResearchReport(
        topic="Ocean cleanup robots",
        angle="The cleanup cycle",
        summary="A connected cleanup system.",
        claims=claims,
        sources=sources,
        queries=["ocean cleanup robots"],
        external_research=True,
        provider="gemini",
    )
    storyboard = fallback_storyboard(bundle, sources, "deep_dive", "Fenrir", research=research)
    assert storyboard.title == "Ocean cleanup robots"
    assert [scene.narration for scene in storyboard.scenes] == [claim.text for claim in claims]
    assert [scene.source_refs for scene in storyboard.scenes] == [claim.source_refs for claim in claims]
    script = " ".join(scene.narration for scene in storyboard.scenes)
    for phrase in ("Behind the landing page", "The story behind the page", "The takeaway is simple"):
        assert phrase not in script


def test_prompt_requests_researched_typed_narrative_and_screen_text():
    bundle = ingest_text("Ocean robots collect plastic.")
    prompt = build_storyboard_prompt(bundle, bundle.citations, "deep_dive", "Fenrir")
    assert "6–8" in prompt
    assert "on-screen text" in prompt
    for field in (
        "visual_type",
        "layout",
        "camera",
        "animation",
        "transition",
        "sfx",
        "callouts",
        "metrics",
    ):
        assert field in prompt


def test_mock_and_portfolio_storyboards_have_explicit_safe_direction():
    mock = mock_storyboard("launch", "Fenrir")
    portfolio = portfolio_storyboard("launch", "Fenrir")
    required = {"visual_type", "layout", "camera", "animation", "transition", "sfx"}
    for scene in [*mock.scenes, *portfolio.scenes]:
        assert required <= scene.model_fields_set
    assert all(scene.visual_type in {"screenshot", "source_image"} for scene in portfolio.scenes)
    assert [scene.sfx for scene in mock.scenes] == ["pop", "whoosh", "bass_drop", "none"]
    assert [scene.sfx for scene in portfolio.scenes] == ["pop", "whoosh", "bass_drop", "none"]
