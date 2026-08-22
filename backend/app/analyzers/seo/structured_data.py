"""Structured data and robots meta checks."""

import json
import re

from app.analyzers.base import EvidenceDraft, FindingDraft


def check_structured_data(pages_html: list[str], base_url: str) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    found_any = False
    jsonld_count = 0
    for html in pages_html:
        for match in re.finditer(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S | re.I):
            jsonld_count += 1
            try:
                json.loads(match.group(1))
                found_any = True
            except json.JSONDecodeError:
                findings.append(
                    FindingDraft(
                        rule_id="SEO_STRUCTURED_DATA_INVALID",
                        title="Invalid JSON-LD structured data",
                        severity="LOW",
                        confidence=0.95,
                        impact="LOW",
                        effort="LOW",
                        description="A JSON-LD script block contains invalid JSON and will be ignored by search engines.",
                        affected_url=base_url,
                        evidence=[EvidenceDraft("HTML_ELEMENT", base_url, "invalid application/ld+json")],
                    )
                )
    if jsonld_count == 0:
        findings.append(
            FindingDraft(
                rule_id="SEO_STRUCTURED_DATA_MISSING",
                title="No structured data (JSON-LD) detected",
                severity="INFO",
                confidence=0.9,
                impact="LOW",
                effort="MEDIUM",
                description="Structured data (e.g. Organization, Product, FAQ schema) can improve rich results.",
                affected_url=base_url,
            )
        )
    if found_any:
        findings.append(
            FindingDraft(
                rule_id="SEO_STRUCTURED_DATA_PRESENT",
                title="Valid structured data detected",
                severity="INFO",
                confidence=0.95,
                impact="LOW",
                effort="LOW",
                description=f"{jsonld_count} valid JSON-LD block(s) found.",
                affected_url=base_url,
            )
        )
    return findings


def check_robots_meta(pages_html: list[str], base_url: str) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    noindex = 0
    for html in pages_html:
        for m in re.finditer(r'<meta\s+name="robots"\s+content="([^"]*)"', html, re.I):
            if "noindex" in m.group(1).lower():
                noindex += 1
    if noindex:
        findings.append(
            FindingDraft(
                rule_id="SEO_NOINDEX_PAGES",
                title=f"{noindex} page(s) blocked from indexing (noindex)",
                severity="LOW",
                confidence=0.95,
                impact="LOW",
                effort="LOW",
                description="Pages with robots noindex will not appear in search results.",
                affected_url=base_url,
                evidence=[EvidenceDraft("HTML_ELEMENT", base_url, f"noindex count={noindex}")],
            )
        )
    return findings
