from sqlalchemy import func, select

from app.models.finding import Finding
from app.models.scan import Scan
from app.repositories.base_repository import BaseRepository


class FindingRepository(BaseRepository[Finding]):
    model = Finding

    def list_for_scan(
        self,
        scan_id: int,
        category: str | None = None,
        severity: str | None = None,
        status: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[Finding]:
        stmt = select(Finding).where(Finding.scan_id == scan_id)
        if category:
            stmt = stmt.where(Finding.category == category.upper())
        if severity:
            stmt = stmt.where(Finding.severity == severity.upper())
        if status:
            stmt = stmt.where(Finding.status == status.upper())
        stmt = stmt.order_by(Finding.severity.asc()).limit(limit).offset(offset)
        return list(self.db.scalars(stmt).all())

    def count_for_scan(self, scan_id: int) -> int:
        stmt = select(func.count(Finding.id)).where(Finding.scan_id == scan_id)
        return int(self.db.scalar(stmt) or 0)

    def count_by_severity(self, scan_id: int) -> dict[str, int]:
        stmt = (
            select(Finding.severity, func.count(Finding.id))
            .where(Finding.scan_id == scan_id)
            .group_by(Finding.severity)
        )
        counts: dict[str, int] = {}
        for severity, count in self.db.execute(stmt).all():
            counts[severity] = int(count)
        return counts

    def count_critical_for_user(self, user_id: int) -> int:
        stmt = (
            select(func.count(Finding.id))
            .join(Scan, Finding.scan_id == Scan.id)
            .where(
                Finding.severity == "CRITICAL",
                Scan.website.has(user_id=user_id),
                Scan.status == "COMPLETED",
            )
        )
        return int(self.db.scalar(stmt) or 0)
