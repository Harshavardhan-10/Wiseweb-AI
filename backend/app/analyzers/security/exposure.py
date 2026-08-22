"""Exposure checks based only on already-collected crawl data.

Only observable signals are used: URLs referenced by crawled pages, emails
in page text, API-looking paths. No probing of hidden endpoints.
"""

import re

from app.analyzers.base import EvidenceDraft, FindingDraft

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
API_PATH_RE = re.compile(r"/api/v?\d?/?")
KEY_RE = re.compile(
    r"(api[_-]?key|secret|token|password)\s*[=:]\s*['\"][A-Za-z0-9_\-]{12,}['\"]",
    re.IGNORECASE,
)


def check_observable_endpoints(
    pages_html: list[str], base_url: str
) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    all_html = "\n".join(pages_html)[:500_000]

    api_paths = sorted(set(API_PATH_RE.findall(all_html)))[:5]
    if api_paths:
        findings.append(
            FindingDraft(
                rule_id="SEC_OBSERVABLE_API",
                title="Observable API endpoints referenced in page code",
                severity="INFO",
                confidence=0.7,
                impact="LOW",
                effort="LOW",
                description=(
                    "API-style paths are referenced by the crawled pages. Review "
                    "that these endpoints are authenticated and rate-limited."
                ),
                affected_url=base_url,
                evidence=[EvidenceDraft("URL", base_url, ", ".join(api_paths))],
            )
        )

    emails = sorted(set(EMAIL_RE.findall(all_html)))[:5]
    if emails:
        findings.append(
            FindingDraft(
                rule_id="SEC_PUBLIC_EMAIL",
                title="Public email address(es) exposed on the site",
                severity="INFO",
                confidence=0.9,
                impact="LOW",
                effort="LOW",
                description=(
                    "Contact addresses are visible in page content. This is normal "
                    "for public sites but may attract spam."
                ),
                affected_url=base_url,
                evidence=[EvidenceDraft("HTML_ELEMENT", base_url, ", ".join(emails))],
            )
        )

    key_matches = KEY_RE.findall(all_html)
    if key_matches:
        findings.append(
            FindingDraft(
                rule_id="SEC_EXPOSED_SECRET_PATTERN",
                title="Possible API key or secret pattern in page code",
                severity="HIGH",
                confidence=0.4,
                impact="HIGH",
                effort="MEDIUM",
                description=(
                    "A string matching an API-key-like pattern was found in page "
                    "code. This requires human review: it may be a false positive "
                    "or an accidentally exposed credential."
                ),
                affected_url=base_url,
                evidence=[EvidenceDraft("SCRIPT", base_url, str(key_matches[:3]))],
            )
        )
    return findings
