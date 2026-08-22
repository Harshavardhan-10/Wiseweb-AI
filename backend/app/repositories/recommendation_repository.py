from sqlalchemy import func, select

from app.models.recommendation import Recommendation
from app.models.scan import Scan
from app.repositories.base_repository import BaseRepository


class RecommendationRepository(BaseRepository[Recommendation]):
    model = Recommendation

    def list_for_scan(
        self,
        scan_id: int,
        category: str | None = None,
        priority: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[Recommendation]:
        stmt = select(Recommendation).where(Recommendation.scan_id == scan_id)
        if category:
            stmt = stmt.where(Recommendation.category == category.upper())
        if priority:
            stmt = stmt.where(Recommendation.priority == priority.upper())
        stmt = stmt.order_by(Recommendation.priority_score.desc()).limit(limit).offset(offset)
        return list(self.db.scalars(stmt).all())

    def count_for_scan(self, scan_id: int) -> int:
        stmt = select(func.count(Recommendation.id)).where(Recommendation.scan_id == scan_id)
        return int(self.db.scalar(stmt) or 0)

    def top_priority_for_user(self, user_id: int, limit: int = 5) -> list[Recommendation]:
        stmt = (
            select(Recommendation)
            .join(Scan, Recommendation.scan_id == Scan.id)
            .where(Scan.website.has(user_id=user_id), Scan.status == "COMPLETED")
            .order_by(Recommendation.priority_score.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())
