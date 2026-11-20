from pathlib import Path

import pytest
from PIL import Image

from app.events import EventBus
from app.studio.graph import build_studio_graph
from app.studio.vision import (
    REQUIRED_CRITERIA,
    CriterionScore,
    VisionAudit,
    VisionDirector,
    capture_keyframes,
)
from app.studio.vision_providers import AUDIT_PROMPT
from tests.studio.directed_fixtures import directed_storyboard

CRITERIA = (
    "typography/contrast",
    "safe-zone compliance",
    "editorial craft",
    "visual momentum",
    "narrative alignment",
    "asset relevance",
)
REVIEW_TIMES = [0.6, 1.0, 4.5, 9.5, 15.0, 21.5, 28.5, 31.5]
PROMPT_TERMS = ("narrative alignment", "asset relevance", "irrelevant screenshots", "abstract placeholders")


def test_review_times_cover_every_scene_and_motion_pair():
    from app.studio.vision import director_review_times

    storyboard = directed_storyboard()
    times = director_review_times(storyboard)
    assert len(times) <= 12
    assert times[:2] == [0.6, 1.0]
    assert times[-1] == 31.5
    for scene in storyboard.scenes:
        assert round((scene.start + scene.end) / 2, 3) in times
    assert times == REVIEW_TIMES


def test_creative_audit_requires_narrative_and_asset_relevance():
    assert "narrative alignment" in REQUIRED_CRITERIA
    assert "asset relevance" in REQUIRED_CRITERIA
    assert len(REQUIRED_CRITERIA) == 6


@pytest.mark.asyncio
async def test_contact_sheet_has_enough_rows_for_all_review_times(tmp_path: Path):
    html = "<html><body><script>window.seekTo = t => { document.body.dataset.time = t; };</script></body></html>"
    contact_sheet = await capture_keyframes(html, tmp_path, REVIEW_TIMES)

    with Image.open(contact_sheet) as image:
        assert image.size == (1080, 1920)


class AuditClient:
    def __init__(self):
        self.models = self
        self.prompt = None

    def generate_content(self, **kwargs):
        self.prompt = kwargs["contents"][0]
        return type(
            "Response",
            (),
            {
                "parsed": VisionAudit(
                    passed=True,
                    issues=[],
                    scores=[CriterionScore(criterion=name, score=8) for name in CRITERIA],
                )
            },
        )()


@pytest.mark.asyncio
async def test_all_audit_prompts_cover_narrative_and_asset_relevance(tmp_path: Path):
    contact = tmp_path / "contact.png"
    contact.write_bytes(b"png")
    client = AuditClient()
    await VisionDirector(client).audit(contact, "html")

    for prompt in (client.prompt, AUDIT_PROMPT):
        for term in PROMPT_TERMS:
            assert term in prompt


class PassingDirector:
    def __init__(self):
        self.router = type("Router", (), {"history": []})()

    async def safe_audit(self, contact_sheet, html):
        return VisionAudit(
            passed=True,
            issues=[],
            scores=[CriterionScore(criterion=name, score=8) for name in CRITERIA],
        )


@pytest.mark.asyncio
async def test_graph_reviews_storyboard_derived_times(monkeypatch, tmp_path: Path):
    captured = []

    async def fake_capture(html, project_dir, times):
        captured.append(times)
        return tmp_path / "audit" / "contact-sheet.png"

    monkeypatch.setattr("app.studio.graph.capture_keyframes", fake_capture)
    graph = build_studio_graph(object(), object(), vision_director=PassingDirector())
    state = {
        "project_id": "creative-qa",
        "project_dir": tmp_path,
        "events": EventBus("creative-qa"),
        "quality_mode": "strict",
        "storyboard": directed_storyboard(),
        "html": "html",
        "assets": [],
        "visuals": [],
    }

    result = await graph.nodes["vision"].bound.afunc(state)

    assert captured == [REVIEW_TIMES]
    assert set(result["critique_scores"]) == set(CRITERIA)
