"""Scan lifecycle endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import UnavailableError
from app.models.user import User
from app.schemas.scan import (
    ScanCreate, ScanListResponse, ScanProgressResponse, ScanResponse,
)
from app.services.scan_service import ScanService
from app.security.rate_limit import RateLimitExceeded, scan_limiter

router = APIRouter(prefix="/scans", tags=["scans"])


@router.post("/websites/{website_id}", response_model=ScanResponse, status_code=201)
def create_scan(
    website_id: int,
    payload: ScanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _limiter=Depends(scan_limiter),
):
    """Queue a new scan for a website (dispatched to Celery)."""
    service = ScanService(db)
    scan = service.create(
        website_id, current_user.id, payload.crawl_depth, payload.page_limit
    )
    _dispatch(scan.id)
    db.refresh(scan)
    return scan


def _dispatch(scan_id: int) -> None:
    """Dispatch the scan to Celery (eager mode for tests/dev)."""
    from app.config.settings import settings
    from app.workers.tasks.scan_tasks import run_scan

    if settings.celery_task_always_eager:
        run_scan.apply(args=[scan_id])
        return
    try:
        run_scan.delay(scan_id)
    except Exception as exc:  # noqa: BLE001
        # Broker unreachable: the worker cannot accept the scan yet.
        raise UnavailableError(
            "The scan queue is unavailable; the worker is offline. "
            "Please try again shortly."
        ) from exc


@router.get("/{scan_id}", response_model=ScanResponse)
def get_scan(
    scan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ScanService(db).get_for_user(scan_id, current_user.id)


@router.get("/{scan_id}/progress", response_model=ScanProgressResponse)
def scan_progress(
    scan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scan = ScanService(db).get_for_user(scan_id, current_user.id)
    return ScanProgressResponse.model_validate(scan)


@router.post("/{scan_id}/cancel", response_model=ScanResponse)
def cancel_scan(
    scan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ScanService(db).cancel(scan_id, current_user.id)


@router.get("/website/{website_id}/list", response_model=ScanListResponse)
def list_website_scans(
    website_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scans = ScanService(db).list_for_website(website_id, current_user.id)
    return ScanListResponse(
        items=[ScanResponse.model_validate(s) for s in scans],
        total=len(scans),
    )
