"""Industry weights for health scoring.

Default weights come from the product spec. Industry-specific weights can
be added later without touching the scoring core.
"""

DEFAULT_WEIGHTS: dict[str, float] = {
    "SECURITY": 20,
    "PERFORMANCE": 20,
    "ACCESSIBILITY": 10,
    "PRIVACY": 10,
    "SEO": 10,
    "CONTENT": 10,
    "UX": 10,
    "ARCHITECTURE": 10,
}


def weights_for(website_type: str | None) -> dict[str, float]:
    """Return scoring weights for a website type.

    Currently all types use the default weights; future industry datasets
    plug in here.
    """
    return dict(DEFAULT_WEIGHTS)
