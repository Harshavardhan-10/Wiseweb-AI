"""Scan lifecycle service (API-facing)."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.scan import Scan
from app.repositories.scan_repository import ScanRepository
from app.services.website_service import WebsiteService


class ScanService:
    def __init__(self, db: Session):
        self.db = db
        self.scans = ScanRepository(db)

    def create(self, website_id: int, user_id: int, crawl_depth: int, page_limit: int) -> Scan:
        website = WebsiteService(self.db).get_for_user(website_id, user_id)
        if not website:
            raise NotFoundError("Website not found.")
        if website.monitoring_enabled or True:
            # Allow one active scan per website at a time.
            active = self.scans.list_for_website(website_id, limit=1)
            if active and active[0].status in ("QUEUED", "CRAWLING", "ANALYZING", "AI_PROCESSING"):
                raise ConflictError("A scan is already running for this website.")
        scan = self.scans.create(
            website_id=website_id,
            status="QUEUED",
            stage="QUEUED",
            progress_percent=0,
            crawl_depth=crawl_depth,
            page_limit=page_limit,
            started_at=datetime.now(timezone.utc),
        )
        self.db.commit()
        return scan

    def get_for_user(self, scan_id: int, user_id: int) -> Scan:
        scan = self.scans.get_for_user(scan_id, user_id)
        if scan is None:
            raise NotFoundError("Scan not found.")
        return scan

    def list_for_website(self, website_id: int, user_id: int) -> list[Scan]:
        WebsiteService(self.db).get_for_user(website_id, user_id)
        return self.scans.list_for_website(website_id)

    def cancel(self, scan_id: int, user_id: int) -> Scan:
        scan = self.get_for_user(scan_id, user_id)
        if scan.status not in ("QUEUED", "CRAWLING", "ANALYZING", "AI_PROCESSING"):
            raise ConflictError("This scan can no longer be cancelled.")
        scan.status = "CANCELLED"
        scan.error_message = "Cancelled by user."
        self.db.commit()
        return scan
