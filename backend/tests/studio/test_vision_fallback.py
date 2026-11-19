from app.studio.vision import VisionDirector, VisionAudit


class FailingClient:
    class models:
        @staticmethod
        def generate_content(**_):
            raise RuntimeError("Vision provider unavailable")


async def test_vision_failure_retains_deterministic_motion():
    from pathlib import Path
    director = VisionDirector(FailingClient())
    result = await director.safe_audit(Path("unused.png"), "<script>window.seekTo=t=>t</script>")
    assert result.passed is True
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
        scores=[CriterionScore(criterion=name, score=8) for name in ("typography", "safe zones", "editorial", "momentum")],
    )
    require_passing_audit(audit)
