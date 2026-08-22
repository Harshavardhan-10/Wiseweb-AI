"""Recommendations endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.recommendation import (
    RecommendationListResponse, RecommendationResponse, RecommendationUpdate,
)
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/scan/{scan_id}", response_model=RecommendationListResponse)
def list_recommendations(
    scan_id: int,
    category: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    limit: int = Query(default=100, le=200),
    offset: int = Query(default=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = RecommendationService(db)
    recs = service.list_for_scan(
        scan_id, current_user.id,
        category=category, priority=priority, limit=limit, offset=offset,
    )
    return RecommendationListResponse(
        items=[RecommendationResponse.model_validate(r) for r in recs],
        total=len(recs),
    )


@router.patch("/{rec_id}", response_model=RecommendationResponse)
def update_recommendation(
    rec_id: int,
    payload: RecommendationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rec = RecommendationService(db).update_status(rec_id, current_user.id, payload.status)
    return RecommendationResponse.model_validate(rec)
