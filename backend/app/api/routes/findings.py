"""Findings endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import ValidationError
from app.models.finding import FINDING_STATUSES
from app.models.user import User
from app.schemas.finding import (
    EvidenceResponse, FindingListResponse, FindingResponse, FindingUpdate,
)
from app.services.finding_service import FindingService

router = APIRouter(prefix="/findings", tags=["findings"])


@router.get("/scan/{scan_id}", response_model=FindingListResponse)
def list_findings(
    scan_id: int,
    category: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=200, le=500),
    offset: int = Query(default=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = FindingService(db)
    findings = service.list_for_scan(
        scan_id, current_user.id,
        category=category, severity=severity, status=status,
        limit=limit, offset=offset,
    )
    items = []
    for f in findings:
        response = FindingResponse.model_validate(f)
        response.evidence = [
            EvidenceResponse.model_validate(e) for e in service.get_evidence(f.id)
        ]
        items.append(response)
    return FindingListResponse(items=items, total=len(items))


@router.get("/{finding_id}", response_model=FindingResponse)
def get_finding(
    finding_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = FindingService(db)
    finding = service.get_for_user(finding_id, current_user.id)
    response = FindingResponse.model_validate(finding)
    response.evidence = [EvidenceResponse.model_validate(e) for e in service.get_evidence(finding.id)]
    return response


@router.patch("/{finding_id}", response_model=FindingResponse)
def update_finding(
    finding_id: int,
    payload: FindingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.status not in FINDING_STATUSES:
        raise ValidationError(
            f"Invalid status '{payload.status}'. Must be one of: {', '.join(FINDING_STATUSES)}"
        )
    service = FindingService(db)
    finding = service.update_status(finding_id, current_user.id, payload.status)
    response = FindingResponse.model_validate(finding)
    response.evidence = [EvidenceResponse.model_validate(e) for e in service.get_evidence(finding.id)]
    return response
