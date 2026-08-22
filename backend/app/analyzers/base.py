"""Analyzer framework: ScanContext, FindingDraft, AnalyzerResult, BaseAnalyzer.

Every analyzer is a class with ``name`` and ``category``, implementing
``async analyze(context) -> AnalyzerResult``. Analyzers only produce
*observable* findings backed by evidence drafts; they never invent data.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from app.crawler.models import CrawledPage, CrawledResource

logger = logging.getLogger("wisewebai.analyzers")

CATEGORY_ORDER = [
    "ARCHITECTURE", "SECURITY", "PERFORMANCE", "ACCESSIBILITY",
    "PRIVACY", "SEO", "CONTENT", "UX",
]

SEVERITY_RANK = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}
IMPACT_RANK = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
EFFORT_RANK = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}


@dataclass
class TechnologyDetection:
    name: str
    category: str
    confidence: float
    evidence: list[str] = field(default_factory=list)


@dataclass
class ScanContext:
    """Everything an analyzer may need. Populated by the orchestrator."""

    scan_id: int
    website_id: int
    base_url: str
    pages: list[CrawledPage] = field(default_factory=list)
    resources: list[CrawledResource] = field(default_factory=list)
    technologies: list[TechnologyDetection] = field(default_factory=list)
    scan_config: dict[str, Any] = field(default_factory=dict)

    @property
    def home_page(self) -> CrawledPage | None:
        return self.pages[0] if self.pages else None

    def pages_in(self, site_only: bool = False) -> list[CrawledPage]:
        return self.pages

    def html_pages(self) -> list[CrawledPage]:
        return [p for p in self.pages if p.html]

    def resources_by_type(self, resource_type: str) -> list[CrawledResource]:
        return [r for r in self.resources if r.resource_type == resource_type]


@dataclass
class EvidenceDraft:
    evidence_type: str
    source: str | None = None
    value: str | None = None
    metadata: dict | None = None
    confidence: float = 1.0


@dataclass
class FindingDraft:
    category: str = "OTHER"
    rule_id: str = ""
    title: str = ""
    description: str | None = None
    severity: str = "INFO"
    confidence: float = 0.5
    impact: str = "LOW"
    effort: str = "MEDIUM"
    affected_url: str | None = None
    evidence: list[EvidenceDraft] = field(default_factory=list)


@dataclass
class AnalyzerResult:
    findings: list[FindingDraft] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    status: str = "COMPLETED"  # COMPLETED | FAILED
    error: str | None = None


class BaseAnalyzer:
    """Base class for all analyzers.

    Subclasses MUST set ``name`` and ``category`` and implement
    ``async analyze(context) -> AnalyzerResult``.
    """

    name: str = "base"
    category: str = "OTHER"

    async def analyze(self, context: ScanContext) -> AnalyzerResult:
        raise NotImplementedError

    # ---- helpers ----------------------------------------------------------

    @staticmethod
    def finding(
        rule_id: str,
        title: str,
        severity: str = "INFO",
        confidence: float = 0.8,
        impact: str = "LOW",
        effort: str = "MEDIUM",
        description: str | None = None,
        affected_url: str | None = None,
        evidence: list[EvidenceDraft] | None = None,
    ) -> FindingDraft:
        return FindingDraft(
            category="",
            rule_id=rule_id,
            title=title,
            description=description,
            severity=severity,
            confidence=confidence,
            impact=impact,
            effort=effort,
            affected_url=affected_url,
            evidence=evidence or [],
        )

    @staticmethod
    def evidence(
        evidence_type: str,
        source: str | None = None,
        value: str | None = None,
        metadata: dict | None = None,
        confidence: float = 1.0,
    ) -> EvidenceDraft:
        return EvidenceDraft(
            evidence_type=evidence_type,
            source=source,
            value=value,
            metadata=metadata,
            confidence=confidence,
        )

    @staticmethod
    def ok(result: AnalyzerResult) -> AnalyzerResult:
        for f in result.findings:
            f.category = result.category if hasattr(result, "category") else "OTHER"
        return result


def severity_rank(severity: str) -> int:
    return SEVERITY_RANK.get(severity, 0)
