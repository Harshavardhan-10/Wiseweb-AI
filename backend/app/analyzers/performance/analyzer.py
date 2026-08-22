"""Performance analyzer (deterministic, no invented metrics)."""

import logging

from app.analyzers.base import AnalyzerResult, BaseAnalyzer, ScanContext
from app.analyzers.performance.images import check_images_missing_dimensions, check_large_images
from app.analyzers.performance.metrics import summarize_metrics
from app.analyzers.performance.resources import (
    check_page_weight, check_render_blocking_scripts, check_request_count,
    check_resource_sizes, check_third_party_requests,
)
from app.analyzers.performance.scripts import check_script_sizes
from app.analyzers.registry import AnalyzerRegistry

logger = logging.getLogger("wisewebai.analyzers.performance")


class PerformanceAnalyzer(BaseAnalyzer):
    name = "performance"
    category = "PERFORMANCE"

    async def analyze(self, context: ScanContext) -> AnalyzerResult:
        result = AnalyzerResult()
        if not context.pages:
            result.status = "FAILED"
            result.error = "No pages crawled; performance analysis requires pages."
            return result

        resources = context.resources
        pages = context.pages

        result.findings += check_page_weight(pages)
        result.findings += check_resource_sizes(resources)
        result.findings += check_request_count(resources)
        result.findings += check_third_party_requests(resources)
        result.findings += check_render_blocking_scripts(resources)
        result.findings += check_script_sizes(resources)
        result.findings += check_large_images(resources)
        result.findings += check_images_missing_dimensions(pages)

        result.metrics = summarize_metrics(resources, pages)
        return result


AnalyzerRegistry.register(PerformanceAnalyzer)
