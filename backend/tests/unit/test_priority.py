"""Unit tests: recommendation priority engine."""

from app.scoring.priority import bucket_for, priority_score, rank_recommendations


def test_critical_high_confidence_is_p0():
    score = priority_score("CRITICAL", "CRITICAL", "LOW", confidence=1.0, affected_pages=5, total_pages=5)
    assert bucket_for(score) == "P0"


def test_high_severity_with_impact_is_at_least_p1():
    score = priority_score("CRITICAL", "HIGH", "LOW", confidence=1.0, affected_pages=5, total_pages=5)
    assert bucket_for(score) == "P1"


def test_low_severity_low_confidence_is_p3():
    score = priority_score("LOW", "LOW", "HIGH", confidence=0.3)
    assert bucket_for(score) == "P3"


def test_confidence_never_exceeds_bounds():
    score = priority_score("CRITICAL", "CRITICAL", "LOW", confidence=99)
    assert score <= 30.0


def test_affected_pages_factor():
    all_pages = priority_score("MEDIUM", "MEDIUM", "MEDIUM", 0.8, affected_pages=5, total_pages=5)
    few_pages = priority_score("MEDIUM", "MEDIUM", "MEDIUM", 0.8, affected_pages=1, total_pages=5)
    assert all_pages > few_pages


def test_rank_sorts_descending_and_annotates():
    recs = [
        {"severity": "LOW", "impact": "LOW", "effort": "HIGH", "confidence": 0.3,
         "affected_pages": 1, "total_pages": 5},
        {"severity": "HIGH", "impact": "HIGH", "effort": "LOW", "confidence": 0.9,
         "affected_pages": 4, "total_pages": 5},
    ]
    ranked = rank_recommendations(recs)
    assert ranked[0]["priority_score"] >= ranked[1]["priority_score"]
    assert "priority" in ranked[0] and "priority_explanation" in ranked[0]
