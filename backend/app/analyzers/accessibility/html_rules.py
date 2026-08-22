"""Deterministic HTML accessibility rule checks."""

import logging

from bs4 import BeautifulSoup

from app.analyzers.base import EvidenceDraft, FindingDraft
from app.crawler.models import CrawledPage

logger = logging.getLogger("wisewebai.analyzers.accessibility")

SEVERITY_MAP = {
    "img-alt": ("MEDIUM", "MEDIUM"),
    "label": ("HIGH", "MEDIUM"),
    "heading-order": ("MEDIUM", "LOW"),
    "html-lang": ("HIGH", "LOW"),
    "link-name": ("LOW", "LOW"),
    "button-name": ("LOW", "LOW"),
    "aria-role": ("LOW", "LOW"),
}


def _soup(page: CrawledPage) -> BeautifulSoup | None:
    if not page.html:
        return None
    try:
        return BeautifulSoup(page.html, "lxml")
    except Exception:
        return BeautifulSoup(page.html, "html.parser")


def check_img_alt(pages: list[CrawledPage]) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    missing: list[tuple[str, str]] = []
    for page in pages:
        soup = _soup(page)
        if soup is None:
            continue
        for img in soup.find_all("img"):
            src = img.get("src") or ""
            if img.get("role") == "presentation":
                continue
            if not img.get("alt") and "alt" not in img.attrs:
                missing.append((page.url, src[:200]))
    if missing:
        findings.append(
            FindingDraft(
                rule_id="A11Y_IMG_MISSING_ALT",
                title=f"Images missing alt text ({len(missing)} found)",
                severity="MEDIUM",
                confidence=0.95,
                impact="MEDIUM",
                effort="LOW",
                description=(
                    "Images without alt text are invisible to screen readers and "
                    "hurt image SEO. Decorative images should use alt=\"\"."
                ),
                affected_url=missing[0][0],
                evidence=[EvidenceDraft("HTML_ELEMENT", missing[0][0], missing[0][1],
                                         {"count": len(missing)})],
            )
        )
    return findings


def check_form_labels(pages: list[CrawledPage]) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    unlabeled: list[tuple[str, str]] = []
    for page in pages:
        soup = _soup(page)
        if soup is None:
            continue
        for field in soup.find_all(["input", "select", "textarea"]):
            if field.get("type") in ("hidden", "submit", "button", "reset"):
                continue
            field_id = field.get("id")
            if field_id and soup.find("label", attrs={"for": field_id}):
                continue
            if field.get("aria-label") or field.get("aria-labelledby"):
                continue
            if field.find_parent("label"):
                continue
            unlabeled.append((page.url, (field.get("name") or field.get("type") or "input")[:120]))
    if unlabeled:
        findings.append(
            FindingDraft(
                rule_id="A11Y_FORM_FIELD_NO_LABEL",
                title=f"Form fields without labels ({len(unlabeled)} found)",
                severity="HIGH",
                confidence=0.95,
                impact="MEDIUM",
                effort="MEDIUM",
                description=(
                    "Form inputs without associated labels are unusable with screen "
                    "readers and confusing for many users."
                ),
                affected_url=unlabeled[0][0],
                evidence=[EvidenceDraft("HTML_ELEMENT", unlabeled[0][0], unlabeled[0][1],
                                         {"count": len(unlabeled)})],
            )
        )
    return findings


def check_heading_order(pages: list[CrawledPage]) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    issues: list[tuple[str, str]] = []
    for page in pages:
        soup = _soup(page)
        if soup is None:
            continue
        headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
        prev = 0
        for h in headings:
            level = int(h.name[1])
            if level > prev + 1 and prev > 0:
                issues.append((page.url, f"h{prev} -> {h.name}"))
            prev = level
    if issues:
        findings.append(
            FindingDraft(
                rule_id="A11Y_HEADING_ORDER",
                title=f"Heading hierarchy skips levels ({len(issues)} instance(s))",
                severity="MEDIUM",
                confidence=0.9,
                impact="LOW",
                effort="LOW",
                description=(
                    "Heading levels should not skip (e.g. h1 then h3). Screen "
                    "reader users rely on a logical heading outline."
                ),
                affected_url=issues[0][0],
                evidence=[EvidenceDraft("HTML_ELEMENT", issues[0][0], issues[0][1],
                                         {"count": len(issues)})],
            )
        )
    return findings


def check_html_lang(pages: list[CrawledPage]) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    missing = [p for p in pages if _soup(p) is not None and not _soup(p).html.get("lang")]
    if missing:
        findings.append(
            FindingDraft(
                rule_id="A11Y_HTML_LANG_MISSING",
                title="Document language is not declared",
                severity="HIGH",
                confidence=0.95,
                impact="MEDIUM",
                effort="LOW",
                description=(
                    "The <html> element has no lang attribute on "
                    f"{len(missing)} page(s). Screen readers cannot pick the correct "
                    "pronunciation/language."
                ),
                affected_url=missing[0].url,
                evidence=[EvidenceDraft("HTML_ELEMENT", missing[0].url, "html[lang] missing")],
            )
        )
    return findings


def check_empty_links(pages: list[CrawledPage]) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    empty: list[tuple[str, str]] = []
    for page in pages:
        soup = _soup(page)
        if soup is None:
            continue
        for a in soup.find_all("a"):
            text = a.get_text(" ", strip=True)
            if not text and not a.get("aria-label") and not a.get("title"):
                empty.append((page.url, a.get("href", "")[:150]))
    if empty:
        findings.append(
            FindingDraft(
                rule_id="A11Y_EMPTY_LINK",
                title=f"Links without accessible names ({len(empty)} found)",
                severity="LOW",
                confidence=0.95,
                impact="LOW",
                effort="LOW",
                description="Links containing no text or accessible name are unusable for screen reader users.",
                affected_url=empty[0][0],
                evidence=[EvidenceDraft("HTML_ELEMENT", empty[0][0], empty[0][1],
                                         {"count": len(empty)})],
            )
        )
    return findings


def check_empty_buttons(pages: list[CrawledPage]) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    empty: list[tuple[str, str]] = []
    for page in pages:
        soup = _soup(page)
        if soup is None:
            continue
        for b in soup.find_all("button"):
            if not b.get_text(" ", strip=True) and not b.get("aria-label"):
                empty.append((page.url, str(b)[:150]))
    if empty:
        findings.append(
            FindingDraft(
                rule_id="A11Y_EMPTY_BUTTON",
                title=f"Buttons without accessible names ({len(empty)} found)",
                severity="LOW",
                confidence=0.95,
                impact="LOW",
                effort="LOW",
                description="Buttons with no text or aria-label cannot be identified by assistive technology.",
                affected_url=empty[0][0],
                evidence=[EvidenceDraft("HTML_ELEMENT", empty[0][0], empty[0][1],
                                         {"count": len(empty)})],
            )
        )
    return findings


def check_aria_basics(pages: list[CrawledPage]) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    issues: list[tuple[str, str]] = []
    for page in pages:
        soup = _soup(page)
        if soup is None:
            continue
        for el in soup.find_all(attrs={"aria-hidden": "true"}):
            if el.find(attrs={"role": True}):
                issues.append((page.url, "focusable content inside aria-hidden"))
                break
    if issues:
        findings.append(
            FindingDraft(
                rule_id="A11Y_ARIA_HIDDEN_FOCUSABLE",
                title="Focusable elements inside aria-hidden containers",
                severity="MEDIUM",
                confidence=0.6,
                impact="MEDIUM",
                effort="LOW",
                description="Focusable content hidden with aria-hidden may confuse keyboard and screen reader users.",
                affected_url=issues[0][0],
                evidence=[EvidenceDraft("HTML_ELEMENT", issues[0][0], issues[0][1])],
            )
        )
    return findings


def run_html_rules(pages: list[CrawledPage]) -> list[FindingDraft]:
    return (
        check_img_alt(pages)
        + check_form_labels(pages)
        + check_heading_order(pages)
        + check_html_lang(pages)
        + check_empty_links(pages)
        + check_empty_buttons(pages)
        + check_aria_basics(pages)
    )
