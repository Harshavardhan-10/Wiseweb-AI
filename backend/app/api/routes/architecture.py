"""Architecture graph endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.scan import Scan
from app.models.user import User
from app.schemas.architecture import (
    ArchitectureEdgeResponse, ArchitectureNodeResponse, ArchitectureResponse,
)
from app.services.scan_service import ScanService

router = APIRouter(prefix="/architecture", tags=["architecture"])


@router.get("/scan/{scan_id}", response_model=ArchitectureResponse)
def get_architecture(
    scan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scan: Scan = ScanService(db).get_for_user(scan_id, current_user.id)
    return ArchitectureResponse(
        nodes=[ArchitectureNodeResponse.model_validate(n) for n in scan.architecture_nodes],
        edges=[ArchitectureEdgeResponse.model_validate(e) for e in scan.architecture_edges],
    )
