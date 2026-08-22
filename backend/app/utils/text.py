"""Passive, defensive analysis helpers."""

import hashlib
import re

from bs4 import BeautifulSoup

_TEXT_STRIP_RE = re.compile(r"\s+")


def normalize_whitespace(text: str | None) -> str:
    if not text:
        return ""
    return _TEXT_STRIP_RE.sub(" ", text).strip()


def visible_text(html: str, max_chars: int = 20000) -> str:
    """Extract readable text from HTML, excluding script/style."""
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True)
    return normalize_whitespace(text)[:max_chars]


def word_count(text: str) -> int:
    return len(text.split())


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def truncate(text: str | None, limit: int = 500) -> str:
    if not text:
        return ""
    return text if len(text) <= limit else text[: limit - 3] + "..."
