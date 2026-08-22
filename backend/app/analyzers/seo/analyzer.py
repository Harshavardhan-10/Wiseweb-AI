"""SEO analyzer: deterministic checks.

Also probes /sitemap.xml presence via the home page's robots.txt sitemap
references if observed (never guessed).
"""

import logging

from app.analyzers.base import AnalyzerResult, BaseAnalyzer, ScanContext
from app.analyzers.registry import AnalyzerRegistry
from app.analyzers.seo.links import (
    check_broken_links, check_heading_structure, check_internal_links,
    check_url_structure,
)
from app.analyzers.seo.metadata import (
    check_canonical, check_meta_description, check_open_graph, check_title,
)
from app.analyzers.seo.structured_data import (
    check_robots_meta, check_structured_data,
)

logger = logging.getLogger("wisewebai.analyzers.seo")


class SeoAnalyzer(BaseAnalyzer):
    name = "seo"
    category = "SEO"

    async def analyze(self, context: ScanContext) -> AnalyzerResult:
        result = AnalyzerResult()
        if not context.pages:
            result.status = "FAILED"
            result.error = "No pages crawled."
            return result

        htmls = [p.html for p in context.pages if p.html]

        result.findings += check_title(context.pages)
        result.findings += check_meta_description(context.pages)
        result.findings += check_canonical(context.pages)
        result.findings += check_open_graph(context.pages)
        result.findings += check_internal_links(context.pages)
        result.findings += check_url_structure(context.pages, context.base_url)
        result.findings += check_broken_links(context.pages)
        result.findings += check_heading_structure(context.pages)
        result.findings += check_structured_data(htmls, context.base_url)
        result.findings += check_robots_meta(htmls, context.base_url)

        result.metrics["pages_with_titles"] = sum(1 for p in context.pages if p.title)
        result.metrics["total_internal_links"] = sum(len(p.internal_links) for p in context.pages)
        return result


AnalyzerRegistry.register(SeoAnalyzer)
