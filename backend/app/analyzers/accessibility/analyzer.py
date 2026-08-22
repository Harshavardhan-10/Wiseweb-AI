"""Accessibility analyzer: deterministic HTML rule checks.

Optional axe-core browser checks run only when explicitly enabled
(``AXE_ENABLED=true`` + Playwright browsers installed); otherwise the
feature reports itself as unavailable rather than faking results.
"""

import logging

from app.analyzers.accessibility.html_rules import run_html_rules
from app.analyzers.base import AnalyzerResult, BaseAnalyzer, ScanContext, FindingDraft, EvidenceDraft
from app.analyzers.registry import AnalyzerRegistry

logger = logging.getLogger("wisewebai.analyzers.accessibility")


class AccessibilityAnalyzer(BaseAnalyzer):
    name = "accessibility"
    category = "ACCESSIBILITY"

    async def analyze(self, context: ScanContext) -> AnalyzerResult:
        result = AnalyzerResult()
        if not context.pages:
            result.status = "FAILED"
            result.error = "No pages crawled."
            return result

        result.findings += run_html_rules(context.pages)

        # Optional axe-core pass (off by default). Never fabricate results:
        # if unavailable, the finding below is not emitted at all.
        from app.analyzers.accessibility.axe_runner import run_axe
        if context.home_page and context.home_page.html:
            violations = await run_axe(context.home_page.html, context.home_page.url)
            if violations:
                for violation in violations[:10]:
                    result.findings.append(
                        FindingDraft(
                            rule_id=f"A11Y_AXE_{violation.get('id', 'UNKNOWN')}",
                            title=f"axe-core: {violation.get('help', violation.get('id', 'violation'))}",
                            severity="MEDIUM",
                            confidence=0.9,
                            impact="MEDIUM",
                            effort="MEDIUM",
                            description=(
                                violation.get("description", "")
                                + " (detected via axe-core browser analysis)"
                            ),
                            affected_url=context.home_page.url,
                            evidence=[EvidenceDraft(
                                "HTML_ELEMENT", context.home_page.url,
                                str(violation.get("impact")),
                                {"nodes": len(violation.get("nodes", []))},
                            )],
                        )
                    )
            else:
                result.metrics["axe"] = "not_available_or_clean"
        return result


AnalyzerRegistry.register(AccessibilityAnalyzer)
