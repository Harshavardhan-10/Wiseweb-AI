"""Third-party dependency analysis.

Only observable signals are used. Findings use conservative wording:
"Potential tracking-related resource", never legal conclusions.
"""

from collections import Counter

from app.analyzers.base import EvidenceDraft, FindingDraft

# Domains commonly associated with analytics/advertising/tracking scripts.
# Used ONLY to produce "potential" findings with honest confidence levels.
ANALYTICS_DOMAINS = (
    "google-analytics.com", "googletagmanager.com", "googleadservices.com",
    "doubleclick.net", "facebook.net", "connect.facebook.net", "analytics.tiktok.com",
    "ads.linkedin.com", "snap.licdn.com", "x.com", "twitter.com", "criteo.com",
    "hotjar.com", "clarity.ms", "matomo.cloud", "plausible.io", "posthog.com",
    "mixpanel.com", "segment.com", "segment.io", "amplitude.com", "heap.io",
    "mouseflow.com", "fullstory.com", "cookiebot.com", "onetrust.com", "consent.",
)

SOCIAL_WIDGET_DOMAINS = (
    "facebook.com", "instagram.com", "youtube.com", "linkedin.com",
    "pinterest.com", "tiktok.com", "x.com", "twitter.com",
)

TRACKER_SCRIPT_HINTS = (
    "gtag", "googletagmanager", "google-analytics", "fbevents", "fbq(",
    "fbq", "clarity", "hotjar", "analytics", "track", "segment", "amplitude",
    "mixpanel", "posthog", "plausible", "cookieconsent", "onetrust", "cmp",
)


def analyze_third_parties(resources, pages_html: list[str], base_url: str) -> list[FindingDraft]:
    findings: list[FindingDraft] = []

    external_domains: Counter[str] = Counter(
        r.domain for r in resources if r.is_external and r.domain
    )
    if not external_domains:
        return findings

    # Category classification (observable, best-effort).
    analytics_hits = [
        (d, c) for d, c in external_domains.items()
        if any(h in d for h in ANALYTICS_DOMAINS)
    ]
    social_hits = [
        (d, c) for d, c in external_domains.items()
        if any(h in d for h in SOCIAL_WIDGET_DOMAINS)
    ]

    if analytics_hits:
        domains = ", ".join(d for d, _ in analytics_hits[:10])
        findings.append(
            FindingDraft(
                rule_id="PRIV_ANALYTICS_THIRD_PARTIES",
                title=f"Potential analytics-related third parties ({len(analytics_hits)})",
                severity="INFO",
                confidence=0.85,
                impact="LOW",
                effort="MEDIUM",
                description=(
                    "Resources are loaded from domains commonly associated with "
                    "analytics. This does not imply any legal violation; it means "
                    "visitor data may be shared with these providers."
                ),
                evidence=[EvidenceDraft(
                    "URL", base_url, domains[:1000],
                    metadata={"domains": [d for d, _ in analytics_hits[:15]]},
                )],
            )
        )

    if social_hits:
        domains = ", ".join(d for d, _ in social_hits[:10])
        findings.append(
            FindingDraft(
                rule_id="PRIV_SOCIAL_WIDGETS",
                title=f"Potential social media widgets ({len(social_hits)})",
                severity="INFO",
                confidence=0.85,
                impact="LOW",
                effort="LOW",
                description=(
                    "Resources from social platforms were observed. Social widgets "
                    "can set cookies for non-authenticated visitors."
                ),
                evidence=[EvidenceDraft(
                    "URL", base_url, domains[:1000],
                    metadata={"domains": [d for d, _ in social_hits[:15]]},
                )],
            )
        )

    # Detect potential tracking script patterns in inline/external scripts.
    all_scripts = "\n".join(
        (r.inline_content or "") for r in resources if r.resource_type == "JS"
    )[:200_000]
    matched_hints = [h for h in TRACKER_SCRIPT_HINTS if h in all_scripts.lower()]
    if matched_hints and len(matched_hints) >= 2:
        findings.append(
            FindingDraft(
                rule_id="PRIV_TRACKER_SCRIPT_PATTERNS",
                title="Potential tracking-related script patterns observed",
                severity="INFO",
                confidence=0.6,
                impact="LOW",
                effort="MEDIUM",
                description=(
                    "Script content contains patterns commonly used by tracking "
                    "libraries. This is a potential signal and requires human review."
                ),
                evidence=[EvidenceDraft(
                    "SCRIPT", base_url, ", ".join(matched_hints[:10]),
                    metadata={"patterns": matched_hints[:10]},
                )],
            )
        )

    return findings
