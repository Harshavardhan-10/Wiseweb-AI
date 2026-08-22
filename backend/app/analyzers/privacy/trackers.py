"""Privacy signal detection: cookies, privacy policy presence, consent UI."""

import re

from app.analyzers.base import EvidenceDraft, FindingDraft

CONSENT_HINTS = ("cookie consent", "cookiepolicy", "cookie-policy", "accept cookies",
                 "consent", "onetrust", "cookiebot", "cmp-widget")
PRIVACY_POLICY_HINTS = ("privacy policy", "privacypolicy", "privacy-policy",
                        "privacy notice")


def check_privacy_policy(pages_html: list[str], base_url: str) -> list[FindingDraft]:
    all_html = "\n".join(pages_html)[:500_000].lower()
    findings: list[FindingDraft] = []
    if "privacy policy" not in all_html and "privacy-policy" not in all_html and "privacy" not in all_html:
        findings.append(
            FindingDraft(
                rule_id="PRIV_PRIVACY_POLICY_MISSING",
                title="No privacy policy reference detected",
                severity="LOW",
                confidence=0.6,
                impact="LOW",
                effort="MEDIUM",
                description=(
                    "No privacy policy page or link was detected in crawled pages. "
                    "This may not be a violation (the policy may live elsewhere) but "
                    "visitors expect a link to it."
                ),
                affected_url=base_url,
                evidence=[EvidenceDraft("HTML_ELEMENT", base_url, "no privacy policy reference found")],
            )
        )
    return findings


def check_consent_ui(pages_html: list[str], base_url: str) -> list[FindingDraft]:
    all_html = "\n".join(pages_html)[:500_000].lower()
    findings: list[FindingDraft] = []
    if any(hint in all_html for hint in CONSENT_HINTS):
        return findings  # consent UI signals observed — nothing to flag
    if "cookie" in all_html:
        findings.append(
            FindingDraft(
                rule_id="PRIV_CONSENT_UI_NOT_OBSERVED",
                title="Cookies observed but no consent UI signals detected",
                severity="LOW",
                confidence=0.4,
                impact="LOW",
                effort="MEDIUM",
                description=(
                    "The site sets cookies, but no consent/cookie-policy signals were "
                    "observed in the crawled pages. This is an observable signal, not "
                    "a legal conclusion; compliance depends on jurisdiction."
                ),
                affected_url=base_url,
                evidence=[EvidenceDraft("COOKIE", base_url, "cookie signals present")],
            )
        )
    return findings


def check_third_party_cookies(cookies: list[dict], base_url: str) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    # Cookies whose domain differs from the base host are third-party cookies.
    third_party = [c for c in cookies if c.get("domain")]
    if third_party:
        names = ", ".join(c["name"] for c in third_party[:8])
        findings.append(
            FindingDraft(
                rule_id="PRIV_THIRD_PARTY_COOKIES",
                title=f"Potential third-party cookies observed ({len(third_party)})",
                severity="INFO",
                confidence=0.5,
                impact="LOW",
                effort="LOW",
                description=(
                    "Cookies tied to domains other than the site were observed: "
                    f"{names}. This is a potential tracking signal requiring review."
                ),
                affected_url=base_url,
                evidence=[EvidenceDraft(
                    "COOKIE", base_url, names[:500],
                    metadata={"count": len(third_party), "cookies": third_party[:8]},
                )],
            )
        )
    return findings
