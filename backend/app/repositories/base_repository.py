"""Minimal generic repository base class."""

from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    model: type[T]

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, entity_id: int) -> T | None:
        return self.db.get(self.model, entity_id)

    def create(self, **values) -> T:
        entity = self.model(**values)
        self.db.add(entity)
        self.db.flush()
        return entity

    def save(self, entity: T) -> T:
        self.db.add(entity)
        self.db.flush()
        return entity

    def delete(self, entity: T) -> None:
        self.db.delete(entity)
        self.db.flush()

    def list_all(self, limit: int = 100, offset: int = 0) -> list[T]:
        stmt = select(self.model).order_by(self.model.id).limit(limit).offset(offset)
        return list(self.db.scalars(stmt).all())
