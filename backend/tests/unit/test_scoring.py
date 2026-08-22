"""Unit tests: health score computation."""

from app.scoring.health_score import CATEGORIES, compute_scores


def _f(severity="LOW", confidence=0.5):
    return {"severity": severity, "confidence": confidence}


def test_no_findings_means_unmeasured_not_perfect():
    result = compute_scores({})
    assert result["overall"] is None
    for category in CATEGORIES:
        assert result["categories"][category] is None


def test_single_severity_deduction():
    result = compute_scores({"SECURITY": [_f("MEDIUM", 1.0)]})
    assert result["categories"]["SECURITY"] == 92.0  # 100 - 8*1.0


def test_confidence_scales_deduction():
    low_conf = compute_scores({"SECURITY": [_f("MEDIUM", 0.5)]})
    full_conf = compute_scores({"SECURITY": [_f("MEDIUM", 1.0)]})
    assert low_conf["categories"]["SECURITY"] > full_conf["categories"]["SECURITY"]


def test_score_never_negative():
    many = [_f("CRITICAL", 1.0)] * 10
    result = compute_scores({"SECURITY": many})
    assert result["categories"]["SECURITY"] == 0.0


def test_overall_is_weighted_average():
    result = compute_scores({
        "SECURITY": [_f("HIGH", 1.0)],     # 100 - 15 = 85
        "PERFORMANCE": [_f("LOW", 1.0)],   # 100 - 3 = 97
    })
    assert result["overall"] is not None
    assert 85.0 <= result["overall"] <= 97.0


def test_breakdown_is_explainable():
    result = compute_scores({"SEO": [_f("LOW", 1.0)]})
    breakdown = result["breakdown"]["SEO"]
    assert breakdown["finding_count"] == 1
    assert "weight" in breakdown
    assert result["explainable"] is True


def test_categories_include_all_eight():
    assert set(CATEGORIES) == {
        "SECURITY", "PERFORMANCE", "ACCESSIBILITY", "PRIVACY",
        "SEO", "CONTENT", "UX", "ARCHITECTURE",
    }
