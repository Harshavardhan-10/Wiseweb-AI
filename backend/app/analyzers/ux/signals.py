"""Observable UX signals (deterministic, from crawled HTML)."""

from collections import Counter

from app.analyzers.base import EvidenceDraft, FindingDraft
from app.crawler.models import CrawledPage

CTA_HINTS = ("get started", "sign up", "signup", "buy now", "start free", "download",
             "register", "subscribe", "try for free", "join")


def _parsed(page: CrawledPage):
    if not page.html:
        return None
    from app.crawler.parser import parse_html
    return parse_html(page.html, page.url)


def check_navigation_complexity(pages: list[CrawledPage]) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    home = pages[0] if pages else None
    parsed = _parsed(home) if home else None
    if parsed is None:
        return findings
    nav_links = 0
    for nav in parsed.soup.find_all("nav"):
        nav_links += len(nav.find_all("a"))
    # Fallback: count header links.
    if nav_links == 0:
        header = parsed.soup.find("header")
        if header:
            nav_links = len(header.find_all("a"))
    if nav_links >= 12:
        findings.append(
            FindingDraft(
                rule_id="UX_NAV_COMPLEXITY",
                title=f"Navigation contains {nav_links} links",
                severity="LOW",
                confidence=0.85,
                impact="LOW",
                effort="MEDIUM",
                description="A large navigation menu increases choice burden for users.",
                affected_url=home.url if home else None,
                evidence=[EvidenceDraft("HTML_ELEMENT", home.url if home else "", f"nav_links={nav_links}")],
            )
        )
    return findings


def check_cta_presence(pages: list[CrawledPage]) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    home = pages[0] if pages else None
    parsed = _parsed(home) if home else None
    if parsed is None:
        return findings
    text = parsed.soup.get_text(" ", strip=True).lower()
    has_cta = any(hint in text for hint in CTA_HINTS)
    has_buttons = bool(parsed.soup.find_all("button")) or bool(
        parsed.soup.find_all("a", class_=lambda c: c and any("btn" in x for x in c if isinstance(x, str)))
    )
    if not has_cta and not has_buttons:
        findings.append(
            FindingDraft(
                rule_id="UX_NO_CTA",
                title="No clear call-to-action detected on the homepage",
                severity="LOW",
                confidence=0.7,
                impact="LOW",
                effort="MEDIUM",
                description=(
                    "No buttons or action-oriented links were detected. Users may "
                    "not know what to do next."
                ),
                affected_url=home.url if home else None,
                evidence=[EvidenceDraft("HTML_ELEMENT", home.url if home else "", "no CTA found")],
            )
        )
    return findings


def check_form_complexity(pages: list[CrawledPage]) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    worst: tuple[int, str] | None = None
    for page in pages:
        parsed = _parsed(page)
        if parsed is None:
            continue
        for form in parsed.soup.find_all("form"):
            fields = form.find_all(["input", "select", "textarea"])
            fields = [f for f in fields if f.get("type") not in ("hidden", "submit", "button", "reset")]
            count = len(fields)
            if count >= 8 and (worst is None or count > worst[0]):
                worst = (count, page.url)
    if worst:
        findings.append(
            FindingDraft(
                rule_id="UX_FORM_COMPLEXITY",
                title=f"Long form with {worst[0]} fields",
                severity="INFO",
                confidence=0.85,
                impact="LOW",
                effort="MEDIUM",
                description="Long forms increase drop-off. Consider progressive disclosure.",
                affected_url=worst[1],
                evidence=[EvidenceDraft("HTML_ELEMENT", worst[1], f"field_count={worst[0]}")],
            )
        )
    return findings


def check_mobile_layout(pages: list[CrawledPage]) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    home = pages[0] if pages else None
    parsed = _parsed(home) if home else None
    if parsed is None:
        return findings
    viewport = parsed.soup.find("meta", attrs={"name": "viewport"})
    if not viewport or not viewport.get("content"):
        findings.append(
            FindingDraft(
                rule_id="UX_NO_VIEWPORT",
                title="Mobile viewport meta tag is missing",
                severity="HIGH",
                confidence=0.95,
                impact="HIGH",
                effort="LOW",
                description=(
                    "Without a viewport meta tag, the homepage renders as a desktop "
                    "page on mobile devices."
                ),
                affected_url=home.url if home else None,
                evidence=[EvidenceDraft("HTML_ELEMENT", home.url if home else "", "no viewport meta")],
            )
        )
    return findings


def check_heading_consistency(pages: list[CrawledPage]) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    multi_h1: list[CrawledPage] = []
    for page in pages:
        parsed = _parsed(page)
        if parsed is None:
            continue
        h1s = parsed.soup.find_all("h1")
        if len(h1s) > 1:
            multi_h1.append(page)
    if multi_h1:
        findings.append(
            FindingDraft(
                rule_id="UX_MULTIPLE_H1",
                title=f"Multiple H1 headings on {len(multi_h1)} page(s)",
                severity="LOW",
                confidence=0.9,
                impact="LOW",
                effort="LOW",
                description="Multiple H1 headings make the page purpose less clear.",
                affected_url=multi_h1[0].url,
                evidence=[EvidenceDraft("HTML_ELEMENT", multi_h1[0].url, "multiple h1")],
            )
        )
    return findings


def check_content_density(pages: list[CrawledPage]) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    dense = [p for p in pages if p.word_count and p.word_count > 4000]
    if dense:
        findings.append(
            FindingDraft(
                rule_id="UX_CONTENT_DENSITY",
                title=f"Very dense content on {len(dense)} page(s)",
                severity="INFO",
                confidence=0.8,
                impact="LOW",
                effort="MEDIUM",
                description="Pages with very large amounts of text are harder to scan.",
                affected_url=dense[0].url,
                evidence=[EvidenceDraft("PAGE", dense[0].url, f"words={dense[0].word_count}")],
            )
        )
    return findings


def check_page_purpose(pages: list[CrawledPage]) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    unclear: list[CrawledPage] = []
    for page in pages[:8]:
        parsed = _parsed(page)
        if parsed is None:
            continue
        has_h1 = bool(parsed.soup.find("h1"))
        has_title = bool(page.title)
        has_desc = bool(page.meta_description)
        if not has_h1 and not has_title:
            unclear.append(page)
    if unclear:
        findings.append(
            FindingDraft(
                rule_id="UX_UNCLEAR_PURPOSE",
                title=f"Unclear page purpose on {len(unclear)} page(s)",
                severity="LOW",
                confidence=0.8,
                impact="LOW",
                effort="LOW",
                description="Pages without a title or H1 do not communicate their purpose at a glance.",
                affected_url=unclear[0].url,
                evidence=[EvidenceDraft("PAGE", unclear[0].url, "no title and no h1")],
            )
        )
    return findings
