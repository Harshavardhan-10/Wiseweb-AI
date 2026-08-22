"""HTML parsing: links, resources, metadata.

All parsing is deterministic and defensive. Inline script contents are
captured only for small inline <script> blocks (technology detection),
and truncated.
"""

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.utils.text import normalize_whitespace, visible_text as extract_visible_text, word_count

MAX_INLINE_SCRIPT_CHARS = 2000

_CSS_LINK_RE = re.compile(r"\.css($|\?)", re.I)
_FONT_RE = re.compile(r"\.(woff2?|ttf|otf|eot)($|\?)", re.I)
_IMAGE_RE = re.compile(r"\.(jpe?g|png|gif|webp|avif|svg|ico)($|\?)", re.I)


class ParsedPage:
    def __init__(self, soup: BeautifulSoup, base_url: str):
        self.soup = soup
        self.base_url = base_url

    def title(self) -> str | None:
        tag = self.soup.find("title")
        return normalize_whitespace(tag.get_text()) if tag else None

    def meta_description(self) -> str | None:
        tag = self.soup.find("meta", attrs={"name": "description"})
        if tag and tag.get("content"):
            return tag["content"].strip()[:500]
        return None

    def canonical_url(self) -> str | None:
        tag = self.soup.find("link", rel="canonical")
        if tag and tag.get("href"):
            return urljoin(self.base_url, tag["href"])
        return None

    def internal_links(self, base_hostname: str) -> list[str]:
        links: list[str] = []
        for tag in self.soup.find_all("a", href=True):
            href = tag["href"].strip()
            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
                continue
            absolute = urljoin(self.base_url, href)
            parsed = urlparse(absolute)
            if parsed.scheme not in ("http", "https"):
                continue
            if parsed.hostname and parsed.hostname.lower() == base_hostname.lower():
                cleaned = _strip_fragment(absolute)
                if cleaned not in links:
                    links.append(cleaned)
        return links

    def resources(self, base_hostname: str) -> list[dict]:
        """Extract fetchable referenced resources (css/js/img/font/video/other).

        Inline scripts are NOT included here (nothing to fetch); use
        ``inline_scripts()`` for those.
        """
        found: dict[str, dict] = {}
        base = self.base_url

        for tag in self.soup.find_all("link", href=True):
            href = tag["href"].strip()
            if not href or href.startswith("data:"):
                continue
            rel = (tag.get("rel") or [""])[0].lower()
            if rel not in ("stylesheet", "preload", "prefetch", "modulepreload", "icon"):
                continue
            absolute = urljoin(base, href)
            if rel == "icon":
                rtype = "IMAGE"
            elif rel == "stylesheet" or _CSS_LINK_RE.search(absolute):
                rtype = "CSS"
            else:
                rtype = "OTHER"
            self._add_resource(found, absolute, rtype, base_hostname)

        for tag in self.soup.find_all("script"):
            src = tag.get("src")
            if not src:
                continue
            absolute = urljoin(base, src.strip())
            self._add_resource(found, absolute, "JS", base_hostname)

        for tag, attr, rtype in (
            (self.soup.find_all("img"), "src", "IMAGE"),
            (self.soup.find_all("source"), "src", "IMAGE"),
            (self.soup.find_all("video"), "src", "VIDEO"),
            (self.soup.find_all("audio"), "src", "VIDEO"),
            (self.soup.find_all("iframe"), "src", "OTHER"),
        ):
            for el in tag:
                src = el.get(attr)
                if not src or src.startswith("data:"):
                    continue
                absolute = urljoin(base, src.strip())
                if not urlparse(absolute).hostname:
                    continue
                resolved_type = rtype
                if rtype == "IMAGE" and _FONT_RE.search(absolute):
                    resolved_type = "FONT"
                self._add_resource(found, absolute, resolved_type, base_hostname)

        return list(found.values())

    def inline_scripts(self, page_url: str) -> list[tuple[str, str]]:
        """Return (page_url, content) pairs for non-empty inline scripts."""
        items: list[tuple[str, str]] = []
        for tag in self.soup.find_all("script"):
            if tag.get("src"):
                continue
            content = tag.get_text()[:MAX_INLINE_SCRIPT_CHARS].strip()
            if content:
                items.append((page_url, content))
        return items

    def scripts_by_src(self) -> list[str]:
        urls: list[str] = []
        for tag in self.soup.find_all("script"):
            src = tag.get("src")
            if src:
                urls.append(urljoin(self.base_url, src.strip()))
        return urls

    def meta_tags(self) -> list[tuple[str, str, str]]:
        """Return (name, content, property) triples for meta tags."""
        out: list[tuple[str, str, str]] = []
        for tag in self.soup.find_all("meta"):
            name = tag.get("name") or tag.get("http-equiv") or ""
            prop = tag.get("property") or ""
            content = tag.get("content") or ""
            out.append((name, content, prop))
        return out

    @staticmethod
    def _add_resource(found: dict, url: str, rtype: str, base_hostname: str) -> None:
        parsed = urlparse(url)
        if not parsed.hostname:
            return
        external = parsed.hostname.lower() != base_hostname.lower()
        if url not in found:
            found[url] = {
                "url": url,
                "resource_type": rtype,
                "is_external": external,
                "domain": parsed.hostname.lower(),
            }

    @staticmethod
    def visible_text(html: str, max_chars: int = 30000) -> str:
        return extract_visible_text(html, max_chars)

    @staticmethod
    def count_words(text: str) -> int:
        return word_count(text)


def _strip_fragment(url: str) -> str:
    if "#" not in url:
        return url
    return urlparse(url)._replace(fragment="").geturl()


def parse_html(html: str, page_url: str) -> ParsedPage | None:
    if not html:
        return None
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")
    return ParsedPage(soup, page_url)
