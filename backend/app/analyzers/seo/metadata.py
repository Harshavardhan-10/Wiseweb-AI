"""SEO metadata checks (title, description, canonical, OG, robots)."""

from app.analyzers.base import EvidenceDraft, FindingDraft
from app.crawler.models import CrawledPage


def check_title(pages: list[CrawledPage]) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    missing = [p for p in pages if not (p.title or "").strip()]
    if missing:
        findings.append(
            FindingDraft(
                rule_id="SEO_TITLE_MISSING",
                title=f"Missing page title on {len(missing)} page(s)",
                severity="HIGH",
                confidence=0.95,
                impact="HIGH",
                effort="LOW",
                description="Pages without a <title> are poorly indexed and show empty results in SERPs.",
                affected_url=missing[0].url,
                evidence=[EvidenceDraft("PAGE", missing[0].url, "no <title> tag")],
            )
        )
    too_long = [
        p for p in pages if (p.title or "").strip() and len(p.title) > 65
    ]
    if too_long:
        findings.append(
            FindingDraft(
                rule_id="SEO_TITLE_TOO_LONG",
                title=f"Title exceeds recommended length on {len(too_long)} page(s)",
                severity="LOW",
                confidence=0.8,
                impact="LOW",
                effort="LOW",
                description="Titles longer than ~65 characters may be truncated in search results.",
                affected_url=too_long[0].url,
                evidence=[EvidenceDraft("PAGE", too_long[0].url, too_long[0].title or "")],
            )
        )
    duplicates = _duplicates(pages, lambda x: x.title)
    if duplicates:
        findings.append(
            FindingDraft(
                rule_id="SEO_DUPLICATE_TITLES",
                title=f"Duplicate page titles ({len(duplicates)} page(s))",
                severity="MEDIUM",
                confidence=0.9,
                impact="MEDIUM",
                effort="MEDIUM",
                description=(
                    "Multiple pages share the same title, weakening search relevance "
                    "signals. Each page should have a unique title."
                ),
                affected_url=duplicates[0].url,
                evidence=[EvidenceDraft("PAGE", duplicates[0].url, duplicates[0].title or "")],
            )
        )
    return findings


def check_meta_description(pages: list[CrawledPage]) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    missing = [p for p in pages if not (p.meta_description or "").strip()]
    if missing:
        findings.append(
            FindingDraft(
                rule_id="SEO_META_DESCRIPTION_MISSING",
                title=f"Missing meta description on {len(missing)} page(s)",
                severity="MEDIUM",
                confidence=0.95,
                impact="MEDIUM",
                effort="LOW",
                description="Pages without meta descriptions let search engines choose snippets.",
                affected_url=missing[0].url,
                evidence=[EvidenceDraft("PAGE", missing[0].url, "no meta description")],
            )
        )
    return findings


def check_canonical(pages: list[CrawledPage]) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    missing = [p for p in pages if not p.canonical_url]
    if len(missing) >= 2:
        findings.append(
            FindingDraft(
                rule_id="SEO_CANONICAL_MISSING",
                title=f"No canonical URL on {len(missing)} page(s)",
                severity="LOW",
                confidence=0.8,
                impact="LOW",
                effort="LOW",
                description="Canonical tags help prevent duplicate-content indexing.",
                affected_url=missing[0].url,
                evidence=[EvidenceDraft("PAGE", missing[0].url, "no canonical link")],
            )
        )
    return findings


def check_open_graph(pages: list[CrawledPage]) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    if not pages:
        return findings
    home = pages[0]
    if not home.html:
        return findings
    og_missing = ("property=\"og:title\"" not in home.html and "og:title" not in home.html)
    if og_missing:
        findings.append(
            FindingDraft(
                rule_id="SEO_OG_MISSING",
                title="Open Graph tags not found on the homepage",
                severity="LOW",
                confidence=0.85,
                impact="LOW",
                effort="LOW",
                description="Without Open Graph tags, social platforms choose their own preview content.",
                affected_url=home.url,
                evidence=[EvidenceDraft("HTML_ELEMENT", home.url, "og:title missing")],
            )
        )
    return findings


def _duplicates(pages: list[CrawledPage], key_fn) -> list[CrawledPage]:
    seen: dict[str, CrawledPage] = {}
    dups: list[CrawledPage] = []
    for p in pages:
        k = (key_fn(p) or "").strip().lower()
        if not k:
            continue
        if k in seen:
            dups.append(p)
        else:
            seen[k] = p
    return dups
