"""Severity helpers."""

SEVERITY_POINTS = {
    "CRITICAL": 4,
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1,
    "INFO": 0,
}

IMPACT_POINTS = {
    "CRITICAL": 4,
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1,
}

EFFORT_POINTS = {
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1,
}


def severity_points(severity: str) -> int:
    return SEVERITY_POINTS.get(severity, 0)


def impact_points(impact: str) -> int:
    return IMPACT_POINTS.get(impact, 1)


def effort_points(effort: str) -> int:
    return EFFORT_POINTS.get(effort, 2)
