"""Content quality checks (deterministic)."""

from app.analyzers.base import EvidenceDraft, FindingDraft
from app.crawler.models import CrawledPage

THIN_CONTENT_WORDS = 150


def check_thin_content(pages: list[CrawledPage]) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    thin = [
        p for p in pages
        if p.word_count is not None and p.word_count < THIN_CONTENT_WORDS
    ]
    if thin:
        details = ", ".join(f"{p.url} ({p.word_count}w)" for p in thin[:5])
        findings.append(
            FindingDraft(
                rule_id="CONTENT_THIN",
                title=f"Thin content on {len(thin)} page(s)",
                severity="LOW",
                confidence=0.9,
                impact="LOW",
                effort="MEDIUM",
                description=(
                    "Pages with very little text (< 150 words) provide limited value "
                    "to visitors and search engines."
                ),
                affected_url=thin[0].url,
                evidence=[EvidenceDraft("PAGE", thin[0].url, details[:1000],
                                         {"pages": [(p.url, p.word_count) for p in thin[:10]]})],
            )
        )
    return findings


def check_missing_headings(pages: list[CrawledPage]) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    no_headings: list[CrawledPage] = []
    for page in pages:
        if not page.html:
            continue
        from app.crawler.parser import parse_html
        parsed = parse_html(page.html, page.url)
        if parsed and not parsed.soup.find(["h1", "h2"]):
            no_headings.append(page)
    if no_headings:
        findings.append(
            FindingDraft(
                rule_id="CONTENT_NO_HEADINGS",
                title=f"Pages without heading structure ({len(no_headings)})",
                severity="LOW",
                confidence=0.9,
                impact="LOW",
                effort="LOW",
                description="Pages with no h1/h2 headings are hard to scan and weakly structured.",
                affected_url=no_headings[0].url,
                evidence=[EvidenceDraft("PAGE", no_headings[0].url, "no h1/h2 found")],
            )
        )
    return findings


def check_repeated_content(pages: list[CrawledPage]) -> list[FindingDraft]:
    """Detect pages whose main text is largely identical (boilerplate-heavy)."""
    findings: list[FindingDraft] = []
    bodies: list[tuple[CrawledPage, str]] = []
    for page in pages:
        if page.text:
            bodies.append((page, page.text))
    if len(bodies) < 2:
        return findings

    # Compare visible text of each page (first 400 chars normalized).
    import hashlib
    from collections import Counter
    sigs: Counter[str] = Counter()
    page_sig: dict[str, CrawledPage] = {}
    for page, text in bodies:
        sig = hashlib.sha256(text[:400].encode("utf-8", errors="ignore")).hexdigest()
        sigs[sig] += 1
        page_sig.setdefault(sig, page)
    duplicates = [(sig, c) for sig, c in sigs.items() if c >= 2]
    if duplicates:
        sig, count = duplicates[0]
        findings.append(
            FindingDraft(
                rule_id="CONTENT_REPEATED",
                title=f"Repeated content across {count} page(s)",
                severity="LOW",
                confidence=0.8,
                impact="LOW",
                effort="MEDIUM",
                description=(
                    "Multiple pages share nearly identical opening content. Repeated "
                    "blocks may dilute relevance for search engines."
                ),
                affected_url=page_sig[sig].url,
                evidence=[EvidenceDraft("PAGE", page_sig[sig].url,
                                         f"{count} pages share identical text prefix")],
            )
        )
    return findings
