from sqlalchemy import func, select

from app.models.scan import Scan
from app.repositories.base_repository import BaseRepository


class ScanRepository(BaseRepository[Scan]):
    model = Scan

    def list_for_website(self, website_id: int, limit: int = 50) -> list[Scan]:
        stmt = (
            select(Scan)
            .where(Scan.website_id == website_id)
            .order_by(Scan.started_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def list_for_user(
        self, user_id: int, limit: int = 50, offset: int = 0
    ) -> list[Scan]:
        stmt = (
            select(Scan)
            .join(Scan.website)
            .where(Scan.website.has(user_id=user_id))
            .order_by(Scan.started_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(stmt).all())

    def count_for_user(self, user_id: int) -> int:
        stmt = (
            select(func.count(Scan.id))
            .join(Scan.website)
            .where(Scan.website.has(user_id=user_id))
        )
        return int(self.db.scalar(stmt) or 0)

    def get_for_user(self, scan_id: int, user_id: int) -> Scan | None:
        stmt = (
            select(Scan)
            .join(Scan.website)
            .where(Scan.id == scan_id, Scan.website.has(user_id=user_id))
        )
        return self.db.scalar(stmt)

    def latest_completed_for_website(self, website_id: int) -> Scan | None:
        stmt = (
            select(Scan)
            .where(
                Scan.website_id == website_id,
                Scan.status.in_(["COMPLETED", "FAILED"]),
            )
            .order_by(Scan.started_at.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)
