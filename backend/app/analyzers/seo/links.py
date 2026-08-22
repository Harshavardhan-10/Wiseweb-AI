"""SEO link checks: internal links, broken links, URL structure."""

import re

from app.analyzers.base import EvidenceDraft, FindingDraft


def check_internal_links(pages) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    if not pages:
        return findings
    total_links = sum(len(p.internal_links) for p in pages)
    if total_links == 0 and len(pages) == 1:
        findings.append(
            FindingDraft(
                rule_id="SEO_NO_INTERNAL_LINKS",
                title="No internal links detected",
                severity="LOW",
                confidence=0.8,
                impact="LOW",
                effort="MEDIUM",
                description="No links to other pages were found; internal linking helps crawling.",
                affected_url=pages[0].url,
            )
        )
    return findings


def check_url_structure(pages, base_url: str) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    base_host = base_url.split("//")[1].split("/")[0] if "//" in base_url else ""
    messy = []
    for p in pages:
        if p.url.startswith(f"https://{base_host}") or p.url.startswith(f"http://{base_host}"):
            if re.search(r"[A-Z\s_]", p.url.split("?")[0].split("#")[0]):
                messy.append(p.url)
    if messy:
        findings.append(
            FindingDraft(
                rule_id="SEO_URL_STRUCTURE",
                title=f"URLs with uppercase characters/underscores ({len(messy)})",
                severity="INFO",
                confidence=0.8,
                impact="LOW",
                effort="LOW",
                description="Clean, lowercase hyphenated URLs are easier to read and share.",
                affected_url=messy[0],
                evidence=[EvidenceDraft("URL", messy[0], "uppercase or underscore in path")],
            )
        )
    return findings


def check_broken_links(pages) -> list[FindingDraft]:
    """Internal links that were crawled and failed (4xx/5xx)."""
    findings: list[FindingDraft] = []
    broken = [
        p for p in pages
        if p.status_code and p.status_code >= 400
    ]
    if broken:
        findings.append(
            FindingDraft(
                rule_id="SEO_BROKEN_PAGES",
                title=f"Pages returning errors ({len(broken)})",
                severity="HIGH",
                confidence=0.95,
                impact="MEDIUM",
                effort="LOW",
                description=(
                    "Crawled pages returned HTTP error status codes. If linked "
                    "internally, users and crawlers hit dead ends."
                ),
                affected_url=broken[0].url,
                evidence=[EvidenceDraft(
                    "PAGE", broken[0].url, f"status {broken[0].status_code}",
                    metadata={"urls": [(p.url, p.status_code) for p in broken[:10]]},
                )],
            )
        )
    return findings


def check_heading_structure(pages) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    from app.analyzers.accessibility.html_rules import check_heading_order
    return check_heading_order(pages)
