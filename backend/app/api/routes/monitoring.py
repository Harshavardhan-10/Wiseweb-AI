"""Monitoring / change detection endpoints."""

import asyncio

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.scan import Scan
from app.models.scan_comparison import ScanComparison
from app.models.user import User
from app.schemas.reports import ScanComparisonCreate, ScanComparisonResponse
from app.services.monitoring_service import MonitoringService
from app.services.website_service import WebsiteService

router = APIRouter(prefix="/websites", tags=["monitoring"])

_SCORE_FIELDS = (
    "overall_score", "security_score", "performance_score",
    "accessibility_score", "privacy_score", "seo_score",
    "content_score", "ux_score", "architecture_score",
)


@router.post("/{website_id}/monitoring")
def update_monitoring(
    website_id: int,
    enabled: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = WebsiteService(db)
    website = service.get_for_user(website_id, current_user.id)
    website.monitoring_enabled = enabled
    db.commit()
    return {"monitoring_enabled": website.monitoring_enabled}


@router.post("/{website_id}/changes", response_model=ScanComparisonResponse)
def compare_scans(
    website_id: int,
    payload: ScanComparisonCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compare two scans of the same website (before/after)."""
    service = MonitoringService(db)
    changes = service.compare_scans(
        current_user.id, payload.base_scan_id, payload.compare_scan_id, website_id
    )

    from app.ai.analyzer import AiPipeline

    before = db.get(Scan, payload.base_scan_id)
    after = db.get(Scan, payload.compare_scan_id)
    ai = AiPipeline()
    summary = asyncio.run(ai.change_explanation(
        {"scores": {f: getattr(before, f) for f in _SCORE_FIELDS},
         "findings": [f.title for f in before.findings[:20]]},
        {"scores": {f: getattr(after, f) for f in _SCORE_FIELDS},
         "findings": [f.title for f in after.findings[:20]]},
        changes.get("pages", {}).get("added", [])[:30]
        + changes.get("pages", {}).get("removed", [])[:30]
        + changes.get("headers", {}).get("changed", [])[:30],
    ))
    comparison = ScanComparison(
        website_id=website_id,
        base_scan_id=payload.base_scan_id,
        compare_scan_id=payload.compare_scan_id,
        changes=changes,
        summary=summary,
    )
    db.add(comparison)
    db.commit()
    return ScanComparisonResponse.model_validate(comparison)


@router.get("/{website_id}/changes", response_model=list[ScanComparisonResponse])
def list_changes(
    website_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    WebsiteService(db).get_for_user(website_id, current_user.id)
    stmt = (
        select(ScanComparison)
        .where(ScanComparison.website_id == website_id)
        .order_by(ScanComparison.created_at.desc())
    )
    return list(db.scalars(stmt).all())
