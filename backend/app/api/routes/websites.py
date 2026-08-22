"""Website management endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import NotFoundError
from app.models.user import User
from app.schemas.website import (
    CompetitorCreate, CompetitorResponse, WebsiteCreate, WebsiteResponse,
    WebsiteUpdate,
)
from app.services.website_service import WebsiteService

router = APIRouter(prefix="/websites", tags=["websites"])


@router.get("", response_model=list[WebsiteResponse])
def list_websites(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return WebsiteService(db).list_for_user(current_user.id)


@router.post("", response_model=WebsiteResponse, status_code=201)
def create_website(
    payload: WebsiteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return WebsiteService(db).create(
        user_id=current_user.id,
        name=payload.name,
        url=payload.url,
        website_type=payload.website_type,
        industry=payload.industry,
        target_audience=payload.target_audience,
        description=payload.description,
    )


@router.get("/{website_id}", response_model=WebsiteResponse)
def get_website(
    website_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return WebsiteService(db).get_for_user(website_id, current_user.id)


@router.patch("/{website_id}", response_model=WebsiteResponse)
def update_website(
    website_id: int,
    payload: WebsiteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    changes = payload.model_dump(exclude_unset=True)
    return WebsiteService(db).update(website_id, current_user.id, **changes)


@router.delete("/{website_id}", status_code=204)
def delete_website(
    website_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    WebsiteService(db).delete(website_id, current_user.id)


@router.get("/{website_id}/competitors", response_model=list[CompetitorResponse])
def list_competitors(
    website_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return WebsiteService(db).list_competitors(website_id, current_user.id)


@router.post("/{website_id}/competitors", response_model=CompetitorResponse, status_code=201)
def add_competitor(
    website_id: int,
    payload: CompetitorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return WebsiteService(db).add_competitor(
        website_id, current_user.id, payload.name, payload.url
    )


@router.delete("/{website_id}/competitors/{competitor_id}", status_code=204)
def delete_competitor(
    website_id: int,
    competitor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    WebsiteService(db).delete_competitor(website_id, competitor_id, current_user.id)
