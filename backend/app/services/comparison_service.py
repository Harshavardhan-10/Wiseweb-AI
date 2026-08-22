"""Competitor comparison service."""

from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.analyzer import AiPipeline
from app.ai.schemas import CompetitorOutput
from app.core.exceptions import NotFoundError, ValidationError
from app.models.competitor import Competitor
from app.models.scan import Scan
from app.services.website_service import WebsiteService

SCORE_FIELDS = [
    "overall_score", "security_score", "performance_score", "accessibility_score",
    "privacy_score", "seo_score", "content_score", "ux_score", "architecture_score",
]
DIMENSION_KEYS = {
    "overall": "overall_score",
    "SECURITY": "security_score",
    "PERFORMANCE": "performance_score",
    "ACCESSIBILITY": "accessibility_score",
    "PRIVACY": "privacy_score",
    "SEO": "seo_score",
    "CONTENT": "content_score",
    "UX": "ux_score",
    "ARCHITECTURE": "architecture_score",
}


def _latest_completed(db: Session, website_id: int) -> Scan | None:
    stmt = (
        select(Scan)
        .where(Scan.website_id == website_id, Scan.status == "COMPLETED")
        .order_by(Scan.started_at.desc())
        .limit(1)
    )
    return db.scalar(stmt)


def _bare_host(url: str) -> str | None:
    """Lowercased hostname without a leading www. prefix, if parseable."""
    host = urlparse(url).hostname
    if not host:
        return None
    host = host.lower()
    return host[4:] if host.startswith("www.") else host


class ComparisonService:
    def __init__(self, db: Session):
        self.db = db
        self.websites = WebsiteService(db)

    def compare(
        self,
        user_id: int,
        website_id: int,
        competitor_ids: list[int] | None = None,
        website_ids: list[int] | None = None,
        ai_pipeline: AiPipeline | None = None,
    ) -> dict:
        site = self.websites.get_for_user(website_id, user_id)
        self_scan = _latest_completed(self.db, site.id)
        sites: list[dict] = [
            self._site_entry(site.id, "you", site.name, site.url, self_scan, is_self=True)
        ]

        targets: list[dict] = []
        for cid in competitor_ids or []:
            competitor = self.db.get(Competitor, cid)
            if competitor is None or competitor.website_id != site.id:
                raise NotFoundError(f"Competitor {cid} not found.")
            cscan = self._resolve_competitor_scan(user_id, competitor)
            entry = self._site_entry(
                competitor.id, f"competitor_{cid}", competitor.name, competitor.url, cscan
            )
            targets.append(entry)
            sites.append(entry)

        for wid in website_ids or []:
            other = self.websites.get_for_user(wid, user_id)
            if other.id == site.id:
                raise ValidationError("Cannot compare a website with itself.")
            wscan = _latest_completed(self.db, other.id)
            entry = self._site_entry(
                other.id, f"website_{wid}", other.name, other.url, wscan
            )
            targets.append(entry)
            sites.append(entry)

        ai_explanation: str | None = None
        gaps: dict | None = None
        if targets:
            pipeline = ai_pipeline or AiPipeline()
            self_scores = sites[0]["scores"]
            comp_scores = targets[0]["scores"]
            output = asyncio_safe_compare(pipeline, self_scores, comp_scores)
            ai_explanation = output.summary or output.explanation or None
            gaps = {
                g.dimension: {
                    "you": g.you, "competitor": g.competitor,
                    "gap": g.gap, "explanation": g.explanation,
                }
                for g in output.gaps
            }
        return {"sites": sites, "ai_explanation": ai_explanation, "gaps": gaps}

    def _resolve_competitor_scan(self, user_id: int, competitor: Competitor) -> Scan | None:
        """Latest completed scan for a competitor, resolved through the user's
        own websites by matching URL (exact match first, then www-agnostic
        hostname match). Competitor rows have no scans of their own."""
        websites = self.websites.list_for_user(user_id)
        exact = [w for w in websites if w.normalized_url == competitor.normalized_url]
        for website in exact:
            scan = _latest_completed(self.db, website.id)
            if scan:
                return scan
        comp_host = _bare_host(competitor.normalized_url)
        if not comp_host:
            return None
        for website in websites:
            if _bare_host(website.normalized_url) == comp_host:
                scan = _latest_completed(self.db, website.id)
                if scan:
                    return scan
        return None

    def _site_entry(
        self, website_id: int, key: str, name: str, url: str, scan: Scan | None,
        is_self: bool = False,
    ) -> dict:
        scores: dict[str, float | None] = {}
        if scan:
            for label, field in DIMENSION_KEYS.items():
                scores[label] = getattr(scan, field)
        return {
            "website_id": website_id,
            "key": key,
            "name": name,
            "url": url,
            "is_self": is_self,
            "scores": scores,
            "scan_id": scan.id if scan else None,
            "scanned_at": scan.completed_at if scan else None,
        }


def asyncio_safe_compare(pipeline: AiPipeline, self_scores: dict, comp_scores: dict) -> CompetitorOutput:
    """Run the async comparison safely from a sync context (worker thread)."""
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    coro = pipeline.competitor_analysis(self_scores, comp_scores)
    if loop:
        return loop.run_until_complete(coro)
    return asyncio.run(coro)
