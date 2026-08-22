"""ScanOrchestrator: the heart of a scan.

1. Initialize scan
2. Validate target (SSRF-guarded)
3. Crawl
4. Persist pages/resources
5. Run analyzer registry (per-category status tracking)
6. Persist findings + evidence
7. Compute scores
8. AI correlation (root causes)
9. AI recommendations (validated)
10. AI executive summary
11. Mark scan complete

A failure in one analyzer never fails the whole scan.
"""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.analyzer import AiPipeline
from app.analyzers import AnalyzerRegistry
from app.analyzers.architecture.technology_detector import detect_technologies
from app.analyzers.base import ScanContext, TechnologyDetection
from app.config.settings import settings
from app.crawler.crawler import Crawler
from app.crawler.models import CrawledPage, CrawlResult
from app.models.architecture_node import ArchitectureEdge, ArchitectureNode
from app.models.evidence import Evidence
from app.models.finding import Finding
from app.models.page import Page
from app.models.recommendation import Recommendation
from app.models.resource import Resource
from app.models.scan import Scan
from app.models.scan_comparison import ScanSummary
from app.models.technology import Technology
from app.scoring.health_score import compute_scores
from app.scoring.priority import rank_recommendations

logger = logging.getLogger("wisewebai.orchestrator")

_STAGE_WEIGHTS = {
    "INITIALIZING": 5,
    "CRAWLING": 20,
    "ANALYZING_ARCHITECTURE": 35,
    "ANALYZING_SECURITY": 42,
    "ANALYZING_PERFORMANCE": 49,
    "ANALYZING_ACCESSIBILITY": 56,
    "ANALYZING_PRIVACY": 63,
    "ANALYZING_SEO": 70,
    "ANALYZING_CONTENT": 77,
    "ANALYZING_UX": 84,
    "AI_CORRELATION": 88,
    "AI_RECOMMENDATIONS": 92,
    "AI_SUMMARY": 96,
    "FINALIZING": 98,
}

_CATEGORY_STAGES = {
    "ARCHITECTURE": "ANALYZING_ARCHITECTURE",
    "SECURITY": "ANALYZING_SECURITY",
    "PERFORMANCE": "ANALYZING_PERFORMANCE",
    "ACCESSIBILITY": "ANALYZING_ACCESSIBILITY",
    "PRIVACY": "ANALYZING_PRIVACY",
    "SEO": "ANALYZING_SEO",
    "CONTENT": "ANALYZING_CONTENT",
    "UX": "ANALYZING_UX",
}


class ScanOrchestrator:
    def __init__(self, db: Session, ai_pipeline: AiPipeline | None = None, allow_internal: bool = False):
        self.db = db
        self.ai = ai_pipeline or AiPipeline()
        # DEMO-ONLY: allow scanning the bundled local demo site. Never set
        # from the API layer; only the seed script enables it, with a warning.
        self.allow_internal = allow_internal
        if allow_internal:
            logger.warning("DEMO MODE: SSRF checks relaxed for this orchestrator instance")

    # ------------------------------------------------------------------
    def run(self, scan_id: int) -> Scan:
        """Sync entry point (called by Celery / tests)."""
        asyncio.run(self._run(scan_id))
        scan = self.db.get(Scan, scan_id)
        return scan

    async def _run(self, scan_id: int) -> None:
        scan = self.db.get(Scan, scan_id)
        if scan is None:
            logger.error("scan %s not found", scan_id, extra={"scan_id": scan_id})
            return
        if scan.status == "CANCELLED":
            return

        website = scan.website
        scan.status = "CRAWLING"
        scan.stage = "INITIALIZING"
        scan.progress_percent = _STAGE_WEIGHTS["INITIALIZING"]
        self._commit()
        logger.info("scan %s started for %s", scan.id, website.url,
                    extra={"scan_id": scan.id, "website_id": website.id})

        try:
            crawl_result = await self._crawl(scan, website.url)
            if crawl_result.error and not crawl_result.pages:
                raise RuntimeError(crawl_result.error)

            context = await self._persist_crawl(scan, crawl_result)
            analyzer_results, runs, findings_by_category = await self._analyze(scan, context)
            score_result = compute_scores(
                {cat: _draft_dicts(result) for cat, result in analyzer_results.items()
                 if result.status == "COMPLETED"},
                website.website_type,
            )
            self._persist_scores(scan, score_result)

            self._persist_architecture(scan, analyzer_results.get("ARCHITECTURE"))

            await self._ai_phase(scan, context, findings_by_category)

            scan.status = "COMPLETED"
            scan.stage = "COMPLETED"
            scan.progress_percent = 100
            scan.completed_at = datetime.now(timezone.utc)
            website.last_scanned_at = datetime.now(timezone.utc)
            self._commit()
            logger.info("scan %s completed", scan.id, extra={"scan_id": scan.id})
        except Exception as exc:  # noqa: BLE001
            self.db.rollback()
            scan = self.db.get(Scan, scan_id)
            if scan is not None:
                scan.status = "FAILED"
                scan.stage = "FAILED"
                scan.error_message = str(exc)[:2000]
                self._commit()
            logger.exception("scan %s failed: %s", scan_id, exc,
                             extra={"scan_id": scan_id, "error": str(exc)})

    # ------------------------------------------------------------------
    async def _crawl(self, scan: Scan, base_url: str) -> CrawlResult:
        scan.stage = "CRAWLING"
        scan.progress_percent = _STAGE_WEIGHTS["CRAWLING"]
        self._commit()
        crawler = Crawler(
            max_pages=scan.page_limit,
            max_depth=scan.crawl_depth,
            timeout=settings.crawler_timeout,
            concurrency=settings.crawler_concurrency,
            delay=settings.crawler_delay,
            allow_internal=self.allow_internal,
        )
        result = await crawler.crawl(base_url)
        scan.pages_discovered = len(result.pages)
        return result

    async def _persist_crawl(self, scan: Scan, result: CrawlResult) -> ScanContext:
        # Clear any previous crawl data for this scan (rescan-safe).
        pages = list(scan.pages)
        for p in pages:
            self.db.delete(p)
        for r in list(scan.resources):
            self.db.delete(r)
        for t in list(scan.technologies):
            self.db.delete(t)
        self.db.flush()

        headers: dict[str, str] = {}
        cookies: list[dict] = []
        context_pages: list[CrawledPage] = []
        context_resources: list = []
        technologies: list[TechnologyDetection] = []

        for page in result.pages:
            db_page = Page(
                scan_id=scan.id,
                url=page.url,
                canonical_url=page.canonical_url,
                status_code=page.status_code,
                content_type=page.content_type,
                title=page.title,
                meta_description=page.meta_description,
                word_count=page.word_count,
                html_size=page.html_size,
                load_time=page.load_time,
                depth=page.depth,
                is_internal=True,
            )
            self.db.add(db_page)
            self.db.flush()

            for r in page.resources:
                self.db.add(Resource(
                    scan_id=scan.id,
                    page_id=db_page.id,
                    url=r.url,
                    resource_type=r.resource_type,
                    mime_type=r.mime_type,
                    size_bytes=r.size_bytes,
                    status_code=r.status_code,
                    is_external=r.is_external,
                    domain=r.domain,
                    load_time=r.load_time,
                ))
            # Build the in-memory context (html truncated already by crawler).
            page.html = page.html[:300_000]
            context_pages.append(page)
            context_resources.extend(page.resources)
            if page.depth == 0:
                headers = page.headers
                cookies = page.cookies

        scan.pages_analyzed = len(context_pages)

        technologies = detect_technologies(context_pages, headers, cookies)
        for tech in technologies:
            self.db.add(Technology(
                scan_id=scan.id,
                name=tech.name,
                category=tech.category,
                confidence=tech.confidence,
                evidence=tech.evidence,
            ))
        self._commit()

        return ScanContext(
            scan_id=scan.id,
            website_id=scan.website_id,
            base_url=result.base_url,
            pages=context_pages,
            resources=context_resources,
            technologies=technologies,
            scan_config={"browser_enabled": settings.browser_enabled},
        )

    async def _analyze(self, scan: Scan, context: ScanContext):
        """Run all analyzers, persist findings + evidence, track statuses."""
        results, runs = await AnalyzerRegistry.run_all(context)

        findings_by_category: dict[str, list[dict]] = {}
        analyzer_status: dict[str, str] = {}
        for run in runs:
            analyzer_status[run.category] = run.status
            scan.stage = _CATEGORY_STAGES.get(run.category, "ANALYZING")
            scan.progress_percent = _STAGE_WEIGHTS.get(scan.stage, 50)
            scan.analyzer_status = analyzer_status
            self._commit()

            result = results.get(run.category)
            if result is None or result.status == "FAILED":
                continue
            category_findings: list[dict] = []
            for draft in result.findings:
                finding = Finding(
                    scan_id=scan.id,
                    category=draft.category or run.category,
                    rule_id=draft.rule_id,
                    title=draft.title[:500],
                    description=draft.description,
                    severity=draft.severity,
                    confidence=draft.confidence,
                    impact=draft.impact,
                    effort=draft.effort,
                    affected_url=draft.affected_url,
                )
                self.db.add(finding)
                self.db.flush()
                for ev in draft.evidence:
                    self.db.add(Evidence(
                        finding_id=finding.id,
                        evidence_type=ev.evidence_type,
                        source=ev.source,
                        value=ev.value,
                        meta=ev.metadata,
                        confidence=ev.confidence,
                    ))
                category_findings.append({
                    "id": finding.id, "category": finding.category,
                    "rule_id": finding.rule_id, "title": finding.title,
                    "description": finding.description, "severity": finding.severity,
                    "impact": finding.impact, "effort": finding.effort,
                    "confidence": finding.confidence, "affected_url": finding.affected_url,
                })
            findings_by_category[run.category] = category_findings

        scan.analyzer_status = analyzer_status
        self._commit()
        return results, runs, findings_by_category

    def _persist_scores(self, scan: Scan, score_result: dict) -> None:
        categories = score_result["categories"]
        scan.overall_score = score_result["overall"]
        scan.security_score = categories.get("SECURITY")
        scan.performance_score = categories.get("PERFORMANCE")
        scan.accessibility_score = categories.get("ACCESSIBILITY")
        scan.privacy_score = categories.get("PRIVACY")
        scan.seo_score = categories.get("SEO")
        scan.content_score = categories.get("CONTENT")
        scan.ux_score = categories.get("UX")
        scan.architecture_score = categories.get("ARCHITECTURE")
        self._commit()

    def _persist_architecture(self, scan: Scan, architecture_result) -> None:
        """Persist architecture graph from the architecture analyzer metrics."""
        if architecture_result is None:
            return
        nodes = architecture_result.metrics.get("nodes") or []
        edges = architecture_result.metrics.get("edges") or []

        node_key_to_id: dict[str, int] = {}
        for n in nodes:
            node = ArchitectureNode(
                scan_id=scan.id,
                node_type=n["node_type"],
                name=(n["name"] or "")[:500],
                label=(n.get("label") or None),
                meta=n.get("metadata"),
            )
            self.db.add(node)
            self.db.flush()
            node_key_to_id[n["key"]] = node.id

        for e in edges:
            if e["source"] not in node_key_to_id or e["target"] not in node_key_to_id:
                continue
            self.db.add(ArchitectureEdge(
                scan_id=scan.id,
                source_node_id=node_key_to_id[e["source"]],
                target_node_id=node_key_to_id[e["target"]],
                relationship=e["relationship"],
            ))
        self._commit()

    async def _ai_phase(self, scan: Scan, context: ScanContext, findings_by_category: dict) -> None:
        all_findings = [
            f for fl in findings_by_category.values() for f in fl
        ]
        if not all_findings:
            return

        # Evidence lookup
        evidence_by_finding: dict[int, list[dict]] = {}
        for f in all_findings:
            evs = self.db.scalars(
                select(Evidence).where(Evidence.finding_id == f["id"])
            ).all()
            evidence_by_finding[f["id"]] = [
                {"evidence_type": e.evidence_type, "source": e.source,
                 "value": e.value, "metadata": e.meta}
                for e in evs
            ]

        # 1) Root causes
        scan.stage = "AI_CORRELATION"
        scan.progress_percent = _STAGE_WEIGHTS["AI_CORRELATION"]
        self._commit()
        root_causes = await self.ai.root_causes(all_findings, evidence_by_finding)

        # 2) Recommendations
        scan.stage = "AI_RECOMMENDATIONS"
        scan.progress_percent = _STAGE_WEIGHTS["AI_RECOMMENDATIONS"]
        self._commit()
        recommendation_output = await self.ai.recommendations(
            all_findings, evidence_by_finding, root_causes
        )

        # Build rec dicts with finding references and rank by priority engine.
        rec_dicts = []
        for rec in recommendation_output.recommendations:
            finding_ids = [fid for fid in rec.finding_ids if any(f["id"] == fid for f in all_findings)]
            # If the AI did not reference findings, link to the strongest ones.
            if not finding_ids:
                strong = [f for f in all_findings if f.get("category") == rec.category]
                if strong:
                    finding_ids = [strong[0]["id"]]
            severity = "MEDIUM"
            for f in all_findings:
                if f["id"] in finding_ids:
                    severity = f["severity"]
                    break
            rec_dicts.append({
                "title": rec.title, "description": rec.description,
                "category": rec.category, "impact": rec.impact, "effort": rec.effort,
                "confidence": rec.confidence, "root_cause": rec.root_cause,
                "implementation_guidance": rec.implementation_guidance,
                "finding_ids": finding_ids, "severity": severity,
                "affected_pages": self._affected_pages(scan, finding_ids),
                "total_pages": max(1, scan.pages_analyzed),
            })

        ranked = rank_recommendations(rec_dicts)
        for rec in ranked:
            self.db.add(Recommendation(
                scan_id=scan.id,
                title=rec["title"][:500],
                description=rec.get("description"),
                priority=rec["priority"],
                priority_score=rec["priority_score"],
                impact=rec["impact"],
                effort=rec["effort"],
                confidence=rec["confidence"],
                category=rec["category"],
                root_cause=rec.get("root_cause"),
                implementation_guidance=rec.get("implementation_guidance"),
                finding_ids=rec.get("finding_ids", []),
            ))
        self._commit()

        # 3) Summary
        scan.stage = "AI_SUMMARY"
        scan.progress_percent = _STAGE_WEIGHTS["AI_SUMMARY"]
        self._commit()
        scores = {
            "overall": scan.overall_score,
            "categories": {
                "SECURITY": scan.security_score, "PERFORMANCE": scan.performance_score,
                "ACCESSIBILITY": scan.accessibility_score, "PRIVACY": scan.privacy_score,
                "SEO": scan.seo_score, "CONTENT": scan.content_score,
                "UX": scan.ux_score, "ARCHITECTURE": scan.architecture_score,
            },
        }
        rec_list = [r.model_dump() if hasattr(r, "model_dump") else r for r in recommendation_output.recommendations]
        summary_item = await self.ai.summary(scores, all_findings, rec_list)

        self.db.add(ScanSummary(
            scan_id=scan.id,
            headline=summary_item.headline[:500],
            executive_summary=summary_item.executive_summary,
            top_risks=summary_item.top_risks,
            biggest_opportunities=summary_item.biggest_opportunities,
            roadmap=summary_item.roadmap,
        ))
        self._commit()

    def _affected_pages(self, scan: Scan, finding_ids: list[int]) -> int:
        if not finding_ids:
            return 1
        # Count distinct affected URLs among the referenced findings.
        urls = {
            f.affected_url for f in scan.findings if f.id in finding_ids and f.affected_url
        }
        return max(1, len(urls))

    def _commit(self) -> None:
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise


def _draft_dicts(result) -> list[dict]:
    """Convert AnalyzerResult findings (drafts) into scoring-ready dicts."""
    return [
        {
            "severity": f.severity,
            "impact": f.impact,
            "effort": f.effort,
            "confidence": f.confidence,
        }
        for f in result.findings
    ]
