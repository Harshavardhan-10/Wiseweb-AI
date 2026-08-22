"""URL validation for crawl targets.

Combines structural URL validation with mandatory SSRF checks. Every URL
that will be fetched must pass through validate_crawl_url.
"""

from urllib.parse import urlparse, urlunparse

from app.core.exceptions import ValidationError
from app.security.ssrf import validate_url_target


def validate_crawl_url(url: str, allow_internal: bool = False) -> str:
    """Validate a URL before crawling it.

    Returns the canonicalized URL. Raises ValidationError for:
    - non-http(s) schemes
    - missing hostname
    - internal/private/localhost targets (DNS-checked)
    - URL fragments (removed), credentials (removed)

    ``allow_internal=True`` is a DEMO-ONLY escape hatch used by the seed
    script to scan the bundled local demo site. It is never accepted from
    the API layer and logs a loud warning.
    """
    # Structural checks first (fast fail without DNS).
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValidationError(f"Unsupported scheme: {parsed.scheme}")
    if not parsed.hostname:
        raise ValidationError("URL has no hostname.")
    if parsed.username or parsed.password:
        raise ValidationError("URLs with embedded credentials are not allowed.")

    # DNS-based SSRF check (hostname safety + resolved IPs are public).
    if not allow_internal:
        validate_url_target(url)

    canonical = urlunparse(
        (
            parsed.scheme,
            parsed.netloc.lower(),
            parsed.path or "/",
            "",
            parsed.query,
            "",  # drop fragment
        )
    )
    return canonical
