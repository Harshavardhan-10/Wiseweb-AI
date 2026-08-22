from sqlalchemy import func, select

from app.models.website import Website
from app.repositories.base_repository import BaseRepository


class WebsiteRepository(BaseRepository[Website]):
    model = Website

    def list_for_user(self, user_id: int, limit: int = 100, offset: int = 0) -> list[Website]:
        stmt = (
            select(Website)
            .where(Website.user_id == user_id)
            .order_by(Website.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(stmt).all())

    def get_for_user(self, website_id: int, user_id: int) -> Website | None:
        stmt = select(Website).where(
            Website.id == website_id, Website.user_id == user_id
        )
        return self.db.scalar(stmt)

    def get_by_normalized_url(self, normalized_url: str, user_id: int) -> Website | None:
        stmt = select(Website).where(
            Website.normalized_url == normalized_url, Website.user_id == user_id
        )
        return self.db.scalar(stmt)

    def count_for_user(self, user_id: int) -> int:
        stmt = select(func.count(Website.id)).where(Website.user_id == user_id)
        return int(self.db.scalar(stmt) or 0)
