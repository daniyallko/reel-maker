import json
import re
from pathlib import Path

from app.studio.providers import portfolio_storyboard
from app.studio.renderer import SAMPLE_OUTPUT
from app.studio.schemas import StoryScene, StudioOutput
from app.studio.vision import REQUIRED_CRITERIA

CV_PATH = Path(__file__).resolve().parents[2] / "assets/link2reel/portfolio/cv.txt"


def test_sanitized_cv_contains_only_public_professional_evidence():
    text = CV_PATH.read_text(encoding="utf-8").casefold()
    for claim in ("1,000+", "100,000+", "sub-500ms", "99.9%"):
        assert claim in text
    assert "mohd daniyal" in text
    assert "daniyal.pro" in text
    assert "@gmail.com" not in text
    assert "+91" not in text


def test_portfolio_storyboard_is_third_person_and_grounded():
    storyboard = portfolio_storyboard("launch", "Fenrir")
    script = " ".join(scene.narration for scene in storyboard.scenes)
    assert storyboard.duration == 32
    assert "Mohd Daniyal" in script
    assert not re.search(r"\b(I|me|my|mine)\b", script, re.IGNORECASE)
    assert "1,000 websites" in script
    assert "100,000 users" in script
    assert "500 milliseconds" in script
    assert "99.9 percent uptime" in script
    assert "daniyal.pro" in script
    assert storyboard.sources[0].url == "https://daniyal.pro"


def test_bundled_demo_is_the_portfolio_reel():
    payload = json.loads((SAMPLE_OUTPUT / "sample.json").read_text(encoding="utf-8"))
    output = StudioOutput.model_validate(payload["output"])
    assert output.title == "Mohd Daniyal — Production AI in Motion"
    assert output.source_url == "https://daniyal.pro"
    assert output.duration == 32
    assert "100,000 users" in output.script
    assert "500 milliseconds" in output.script
    assert "99.9 percent uptime" in output.script
    assert (SAMPLE_OUTPUT / "trailer.mp4").exists()
    assert (SAMPLE_OUTPUT / "visuals" / "thumbnail-03.png").exists()


def test_bundled_demo_has_typed_direction_and_six_criterion_audit():
    payload = json.loads((SAMPLE_OUTPUT / "sample.json").read_text(encoding="utf-8"))
    output = payload["output"]
    directed_fields = {"visual_type", "layout", "camera", "animation", "transition", "sfx", "callouts", "metrics"}
    scenes = [StoryScene.model_validate(scene) for scene in output["scenes"]]
    assert all(directed_fields <= scene.keys() for scene in output["scenes"])
    assert [scene.visual_type for scene in scenes] == ["screenshot", "screenshot", "source_image", "source_image"]
    scores = output["critique_scores"]
    if scores:
        assert len(scores) == 6
        assert set(scores) == REQUIRED_CRITERIA
