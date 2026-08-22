"""Sanitization helpers.

These exist to prevent log injection and to keep stored text fields clean.
No output escaping is needed on the API side (responses are JSON).
"""

import re

_CTRL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize_text(value: str | None, max_length: int = 2000) -> str:
    """Strip control characters that could corrupt structured logs."""
    if not value:
        return ""
    cleaned = _CTRL_CHARS.sub(" ", value)
    return cleaned[:max_length]
