"""Finding service (read + status updates)."""

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.exceptions import NotFoundError
from app.models.evidence import Evidence
from app.models.finding import Finding
from app.repositories.finding_repository import FindingRepository
from app.services.scan_service import ScanService


class FindingService:
    def __init__(self, db: Session):
        self.db = db
        self.findings = FindingRepository(db)

    def list_for_scan(self, scan_id: int, user_id: int, **filters) -> list[Finding]:
        ScanService(self.db).get_for_user(scan_id, user_id)
        return self.findings.list_for_scan(scan_id, **filters)

    def get_evidence(self, finding_id: int) -> list[Evidence]:
        stmt = select(Evidence).where(Evidence.finding_id == finding_id)
        return list(self.db.scalars(stmt).all())

    def get_for_user(self, finding_id: int, user_id: int) -> Finding:
        finding = self.db.get(Finding, finding_id)
        if finding is None:
            raise NotFoundError("Finding not found.")
        ScanService(self.db).get_for_user(finding.scan_id, user_id)
        return finding

    def update_status(self, finding_id: int, user_id: int, status: str) -> Finding:
        finding = self.get_for_user(finding_id, user_id)
        finding.status = status
        self.db.commit()
        return finding
