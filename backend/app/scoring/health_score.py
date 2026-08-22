"""Health score computation (100-point scale, explainable).

Each category starts at 100 and loses points based on observed findings
(severity, impact, confidence). The overall score is the weighted average
using industry weights. Every score carries a breakdown so it can be
explained — a score never hides the underlying findings.
"""

from app.scoring.severity import impact_points, severity_points
from app.scoring.industry_weights import weights_for

# Points deducted per finding by severity before confidence weighting.
DEDUCTIONS = {
    "CRITICAL": 25.0,
    "HIGH": 15.0,
    "MEDIUM": 8.0,
    "LOW": 3.0,
    "INFO": 0.0,
}

CATEGORIES = [
    "SECURITY", "PERFORMANCE", "ACCESSIBILITY", "PRIVACY",
    "SEO", "CONTENT", "UX", "ARCHITECTURE",
]


def _category_score(findings: list[dict]) -> float:
    score = 100.0
    for f in findings:
        severity = f.get("severity", "INFO")
        deduction = DEDUCTIONS.get(severity, 0.0)
        confidence = float(f.get("confidence", 0.5))
        score -= deduction * confidence
    return round(max(0.0, min(100.0, score)), 1)


def compute_scores(findings_by_category: dict[str, list[dict]], website_type: str | None = None) -> dict:
    weights = weights_for(website_type)
    scores: dict[str, float | None] = {}
    breakdown: dict[str, dict] = {}

    for category in CATEGORIES:
        findings = findings_by_category.get(category, [])
        if not findings:
            # No findings yet: the category is unmeasured, not perfect.
            score: float | None = None
        else:
            score = _category_score(findings)
        scores[category] = score
        breakdown[category] = {
            "score": score,
            "finding_count": len(findings),
            "weight": weights.get(category, 0),
        }

    measured = [(c, s) for c, s in scores.items() if s is not None]
    if measured:
        total_weight = sum(weights.get(c, 0) for c, _ in measured)
        overall = (
            sum(s * weights.get(c, 0) for c, s in measured) / total_weight
            if total_weight > 0 else None
        )
    else:
        overall = None

    return {
        "overall": round(overall, 1) if overall is not None else None,
        "categories": scores,
        "breakdown": breakdown,
        "explainable": True,
    }
