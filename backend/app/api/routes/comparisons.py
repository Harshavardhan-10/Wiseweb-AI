"""Competitor comparison endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.comparison import ComparisonCreate, ComparisonResponse, SiteComparison
from app.services.comparison_service import ComparisonService

router = APIRouter(prefix="/comparisons", tags=["comparisons"])


@router.post("", response_model=ComparisonResponse)
def create_comparison(
    payload: ComparisonCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = ComparisonService(db).compare(
        current_user.id, payload.website_id, payload.competitor_ids, payload.website_ids
    )
    return ComparisonResponse(
        sites=[SiteComparison.model_validate(s) for s in result["sites"]],
        ai_explanation=result.get("ai_explanation"),
        gaps=result.get("gaps"),
    )
