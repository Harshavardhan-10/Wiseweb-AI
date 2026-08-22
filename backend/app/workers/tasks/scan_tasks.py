"""Scan-related Celery tasks."""

import logging

from app.config.settings import settings
from app.core.database import SessionLocal
from app.models.scan import Scan
from app.workers.celery_app import celery_app
from app.workers.orchestrator import ScanOrchestrator

logger = logging.getLogger("wisewebai.tasks.scan")


@celery_app.task(name="wisewebai.run_scan", bind=True, max_retries=0)
def run_scan(self, scan_id: int) -> dict:
    """Execute a full scan in the background."""
    logger.info("task run_scan started", extra={"scan_id": scan_id, "task_id": self.request.id})
    db = SessionLocal()
    try:
        scan = ScanOrchestrator(
            db, allow_internal=settings.allow_localhost_scans
        ).run(scan_id)
        return {"scan_id": scan_id, "status": scan.status, "overall_score": scan.overall_score}
    finally:
        db.close()


@celery_app.task(name="wisewebai.cancel_scan", bind=True)
def cancel_scan(self, scan_id: int) -> dict:
    db = SessionLocal()
    try:
        scan = db.get(Scan, scan_id)
        if scan and scan.status in ("QUEUED", "CRAWLING", "ANALYZING", "AI_PROCESSING"):
            scan.status = "CANCELLED"
            db.commit()
            return {"scan_id": scan_id, "status": "CANCELLED"}
        return {"scan_id": scan_id, "status": scan.status if scan else "NOT_FOUND"}
    finally:
        db.close()
