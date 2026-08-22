"""URL helpers: normalization and validation.

Never trust user-supplied URLs directly. Always normalize and validate before
any network request is made (see app.security.ssrf).
"""

from urllib.parse import urlparse, urlunparse

import tldextract

from app.core.exceptions import ValidationError

ALLOWED_SCHEMES = ("http", "https")


def normalize_url(raw_url: str) -> str:
    """Normalize a user-supplied URL for storage and comparison.

    Raises ValidationError when the URL cannot be safely normalized.
    """
    url = (raw_url or "").strip()
    if not url:
        raise ValidationError("The provided URL is empty.")

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        parsed = urlparse(url)
    except ValueError:
        raise ValidationError("The provided URL is invalid.") from None

    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValidationError("Only http and https URLs are supported.")

    hostname = parsed.hostname
    if not hostname or "." not in hostname.replace("localhost", "") and hostname != "localhost":
        raise ValidationError("The provided URL has no valid hostname.")

    # Reject userinfo (e.g. https://user:pass@host/) — never needed here.
    if parsed.username or parsed.password:
        raise ValidationError("URLs containing credentials are not supported.")

    netloc = hostname.lower()
    port = parsed.port
    if port is not None:
        netloc = f"{netloc}:{port}"
    elif parsed.scheme == "http":
        netloc = netloc
    elif parsed.scheme == "https":
        netloc = netloc

    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/") or "/"

    normalized = urlunparse(
        (parsed.scheme, netloc, path, parsed.params, parsed.query, "")
    )
    return normalized


def is_internal_link(url: str, base_hostname: str) -> bool:
    parsed = urlparse(url)
    if not parsed.hostname:
        return False
    return parsed.hostname.lower() == base_hostname.lower()


def same_site(url_a: str, url_b: str) -> bool:
    return urlparse(url_a).hostname == urlparse(url_b).hostname


def hostname_of(url: str) -> str:
    parsed = urlparse(url)
    return parsed.hostname.lower() if parsed.hostname else ""


def domain_of(url: str) -> str:
    """Registered domain (e.g. www.example.com -> example.com)."""
    parsed = urlparse(url)
    if not parsed.hostname:
        return ""
    ext = tldextract.extract(parsed.hostname)
    return f"{ext.domain}.{ext.suffix}" if ext.domain and ext.suffix else parsed.hostname


def join_url(base: str, link: str) -> str:
    from urllib.parse import urljoin

    return urljoin(base, link)


def is_html_content_type(content_type: str | None) -> bool:
    if not content_type:
        return False
    return "html" in content_type.lower()
