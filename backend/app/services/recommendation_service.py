"""Recommendation service."""

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.recommendation import Recommendation
from app.repositories.recommendation_repository import RecommendationRepository
from app.services.scan_service import ScanService


class RecommendationService:
    def __init__(self, db: Session):
        self.db = db
        self.recommendations = RecommendationRepository(db)

    def list_for_scan(self, scan_id: int, user_id: int, **filters) -> list[Recommendation]:
        ScanService(self.db).get_for_user(scan_id, user_id)
        return self.recommendations.list_for_scan(scan_id, **filters)

    def get_for_user(self, rec_id: int, user_id: int) -> Recommendation:
        rec = self.db.get(Recommendation, rec_id)
        if rec is None:
            raise NotFoundError("Recommendation not found.")
        ScanService(self.db).get_for_user(rec.scan_id, user_id)
        return rec

    def update_status(self, rec_id: int, user_id: int, status: str) -> Recommendation:
        rec = self.get_for_user(rec_id, user_id)
        rec.status = status
        self.db.commit()
        return rec
