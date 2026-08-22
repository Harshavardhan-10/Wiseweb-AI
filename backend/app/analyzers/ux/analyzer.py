"""UX analyzer: observable signals only.

Visual/screenshot-based UX analysis (AI vision) runs only when browser
rendering is enabled and a vision-capable AI model is configured; otherwise
it reports itself as unavailable instead of fabricating results.
"""

import logging

from app.analyzers.base import AnalyzerResult, BaseAnalyzer, ScanContext
from app.analyzers.registry import AnalyzerRegistry
from app.analyzers.ux.signals import (
    check_content_density, check_cta_presence, check_form_complexity,
    check_heading_consistency, check_mobile_layout, check_navigation_complexity,
    check_page_purpose,
)

logger = logging.getLogger("wisewebai.analyzers.ux")


class UxAnalyzer(BaseAnalyzer):
    name = "ux"
    category = "UX"

    async def analyze(self, context: ScanContext) -> AnalyzerResult:
        result = AnalyzerResult()
        if not context.pages:
            result.status = "FAILED"
            result.error = "No pages crawled."
            return result

        result.findings += check_navigation_complexity(context.pages)
        result.findings += check_cta_presence(context.pages)
        result.findings += check_form_complexity(context.pages)
        result.findings += check_mobile_layout(context.pages)
        result.findings += check_heading_consistency(context.pages)
        result.findings += check_content_density(context.pages)
        result.findings += check_page_purpose(context.pages)

        if not context.scan_config.get("browser_enabled"):
            result.metrics["visual_analysis"] = "not_available"
        else:
            result.metrics["visual_analysis"] = "pending"

        return result


AnalyzerRegistry.register(UxAnalyzer)
