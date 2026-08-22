"""Website management service."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.models.competitor import Competitor
from app.models.website import Website
from app.repositories.website_repository import WebsiteRepository
from app.utils.urls import normalize_url


class WebsiteService:
    def __init__(self, db: Session):
        self.db = db
        self.websites = WebsiteRepository(db)

    def _validate(self, url: str) -> str:
        try:
            return normalize_url(url)
        except ValidationError as exc:
            # Reraise with a friendlier code for the API.
            raise ValidationError(str(exc)) from exc

    def create(self, user_id: int, name: str, url: str, **kwargs) -> Website:
        normalized = self._validate(url)
        if self.websites.get_by_normalized_url(normalized, user_id):
            raise ValidationError("This website is already registered.")
        website = self.websites.create(
            user_id=user_id,
            name=name.strip(),
            url=normalized,
            normalized_url=normalized,
            **kwargs,
        )
        self.db.commit()
        return website

    def get_for_user(self, website_id: int, user_id: int) -> Website:
        website = self.websites.get_for_user(website_id, user_id)
        if website is None:
            raise NotFoundError("Website not found.")
        return website

    def list_for_user(self, user_id: int) -> list[Website]:
        return self.websites.list_for_user(user_id)

    def update(self, website_id: int, user_id: int, **changes) -> Website:
        website = self.get_for_user(website_id, user_id)
        if "url" in changes and changes["url"]:
            normalized = self._validate(changes["url"])
            changes["url"] = normalized
            changes["normalized_url"] = normalized
        for key, value in changes.items():
            if value is not None and hasattr(website, key):
                setattr(website, key, value)
        website.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        return website

    def delete(self, website_id: int, user_id: int) -> None:
        website = self.get_for_user(website_id, user_id)
        self.websites.delete(website)
        self.db.commit()

    def add_competitor(self, website_id: int, user_id: int, name: str, url: str):
        self.get_for_user(website_id, user_id)
        normalized = self._validate(url)
        competitor = Competitor(
            website_id=website_id, name=name.strip(), url=normalized, normalized_url=normalized
        )
        self.db.add(competitor)
        self.db.commit()
        return competitor

    def list_competitors(self, website_id: int, user_id: int) -> list[Competitor]:
        self.get_for_user(website_id, user_id)
        return list(
            self.db.scalars(
                select(Competitor).where(Competitor.website_id == website_id)
            ).all()
        )

    def delete_competitor(self, website_id: int, competitor_id: int, user_id: int) -> None:
        self.get_for_user(website_id, user_id)
        competitor = self.db.get(Competitor, competitor_id)
        if competitor is None or competitor.website_id != website_id:
            raise NotFoundError("Competitor not found.")
        self.db.delete(competitor)
        self.db.commit()
