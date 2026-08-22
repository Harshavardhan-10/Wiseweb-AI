"""Content analyzer: quality + potential similarity."""

import logging

from app.analyzers.base import AnalyzerResult, BaseAnalyzer, ScanContext
from app.analyzers.content.quality import (
    check_missing_headings, check_repeated_content, check_thin_content,
)
from app.analyzers.content.similarity import detect_page_similarity
from app.analyzers.registry import AnalyzerRegistry

logger = logging.getLogger("wisewebai.analyzers.content")


class ContentAnalyzer(BaseAnalyzer):
    name = "content"
    category = "CONTENT"

    async def analyze(self, context: ScanContext) -> AnalyzerResult:
        result = AnalyzerResult()
        if not context.pages:
            result.status = "FAILED"
            result.error = "No pages crawled."
            return result

        result.findings += check_thin_content(context.pages)
        result.findings += check_missing_headings(context.pages)
        result.findings += check_repeated_content(context.pages)
        result.findings += detect_page_similarity(context.pages)

        result.metrics["total_words"] = sum(p.word_count or 0 for p in context.pages)
        result.metrics["pages_with_content"] = sum(1 for p in context.pages if p.word_count)
        return result


AnalyzerRegistry.register(ContentAnalyzer)
