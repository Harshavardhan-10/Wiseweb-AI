"""Privacy analyzer.

Detects observable signals only:
- third-party domains / analytics / advertising / social widgets
- potential tracking script patterns
- privacy policy presence
- consent UI signals
- third-party cookies

Never makes legal conclusions. Wording is conservative throughout.
"""

import logging

from app.analyzers.base import AnalyzerResult, BaseAnalyzer, ScanContext
from app.analyzers.privacy.third_party import analyze_third_parties
from app.analyzers.privacy.trackers import (
    check_consent_ui, check_privacy_policy, check_third_party_cookies,
)
from app.analyzers.registry import AnalyzerRegistry

logger = logging.getLogger("wisewebai.analyzers.privacy")


class PrivacyAnalyzer(BaseAnalyzer):
    name = "privacy"
    category = "PRIVACY"

    async def analyze(self, context: ScanContext) -> AnalyzerResult:
        result = AnalyzerResult()
        htmls = [p.html for p in context.pages if p.html]

        result.findings += analyze_third_parties(context.resources, htmls, context.base_url)
        result.findings += check_privacy_policy(htmls, context.base_url)
        result.findings += check_consent_ui(htmls, context.base_url)
        result.findings += check_third_party_cookies(
            context.home_page.cookies if context.home_page else [], context.base_url
        )

        result.metrics["external_domains"] = sorted(
            {r.domain for r in context.resources if r.is_external and r.domain}
        )
        result.metrics["cookie_count"] = len(context.home_page.cookies) if context.home_page else 0
        return result


AnalyzerRegistry.register(PrivacyAnalyzer)
