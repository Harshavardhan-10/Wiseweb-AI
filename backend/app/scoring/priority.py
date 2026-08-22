"""Recommendation priority engine.

priority_score =
    severity_weight
    × impact_weight
    × confidence
    × affected_page_factor
    × business_relevance
    ÷ effort_weight

Normalized into P0..P3. Factors are explained in the response.
"""

from app.scoring.severity import effort_points, impact_points, severity_points

BUSINESS_RELEVANCE = 1.0  # currently uniform; industry/business weights later

# Hard ceilings per bucket so a single factor can't skew results.
_BUCKET_LIMITS = {
    "P0": 24.0,
    "P1": 12.0,
    "P2": 5.0,
    "P3": float("inf"),
}


def priority_score(
    severity: str,
    impact: str,
    effort: str,
    confidence: float,
    affected_pages: int = 1,
    total_pages: int = 1,
    business_relevance: float = BUSINESS_RELEVANCE,
) -> float:
    severity_w = severity_points(severity)  # 0..4
    impact_w = impact_points(impact)        # 1..4
    effort_w = max(1, effort_points(effort))  # 1..3
    affected_factor = 1.0
    if total_pages > 0:
        affected_factor = 1.0 + 0.5 * min(affected_pages / max(total_pages, 1), 1.0)
    confidence = max(0.0, min(1.0, confidence))

    score = (
        severity_w * impact_w * confidence * affected_factor * business_relevance
    ) / effort_w
    return round(score, 3)


def bucket_for(score: float) -> str:
    if score >= _BUCKET_LIMITS["P0"]:
        return "P0"
    if score >= _BUCKET_LIMITS["P1"]:
        return "P1"
    if score >= _BUCKET_LIMITS["P2"]:
        return "P2"
    return "P3"


def rank_recommendations(recommendations: list[dict]) -> list[dict]:
    """Annotate recommendation dicts with priority_score and bucket."""
    for rec in recommendations:
        affected_pages = rec.get("affected_pages", 1)
        total_pages = rec.get("total_pages", 1)
        score = priority_score(
            severity=rec.get("severity", "MEDIUM"),
            impact=rec.get("impact", "MEDIUM"),
            effort=rec.get("effort", "MEDIUM"),
            confidence=rec.get("confidence", 0.5),
            affected_pages=affected_pages,
            total_pages=total_pages,
        )
        rec["priority_score"] = score
        rec["priority"] = bucket_for(score)
        rec["priority_explanation"] = _explain(rec)
    return sorted(recommendations, key=lambda r: -r["priority_score"])


def _explain(rec: dict) -> str:
    return (
        f"Severity {rec.get('severity')} × impact {rec.get('impact')} × "
        f"confidence {rec.get('confidence'):.0%} ÷ effort {rec.get('effort')}"
    )
