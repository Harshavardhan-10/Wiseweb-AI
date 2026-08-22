"""User account endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.repositories.scan_repository import ScanRepository
from app.repositories.website_repository import WebsiteRepository
from app.schemas.auth import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.get("/me/stats")
def my_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    websites = WebsiteRepository(db)
    scans = ScanRepository(db)
    return {
        "websites_count": websites.count_for_user(current_user.id),
        "scans_count": scans.count_for_user(current_user.id),
        "user_id": current_user.id,
    }
