from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_comercial_module
from app.schemas import InteractionCreate, InteractionOut, LeadCreate, LeadDetailOut, LeadListItem
from app.services import lead_service

router = APIRouter(prefix="/leads", tags=["leads"])


@router.get("", response_model=list[LeadListItem])
def list_leads(
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_comercial_module),
):
    return lead_service.list_leads(db)


@router.post("", response_model=LeadDetailOut, status_code=status.HTTP_201_CREATED)
def create_lead(
    payload: LeadCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_comercial_module),
):
    try:
        return lead_service.create_lead(db, current_user, payload)
    except lead_service.ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/{lead_id}", response_model=LeadDetailOut)
def get_lead(
    lead_id: str,
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_comercial_module),
):
    try:
        return lead_service.get_lead_detail(db, lead_id)
    except lead_service.LeadNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{lead_id}/interactions", response_model=InteractionOut, status_code=status.HTTP_201_CREATED)
def add_interaction(
    lead_id: str,
    payload: InteractionCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_comercial_module),
):
    try:
        return lead_service.add_interaction(db, current_user, lead_id, payload)
    except lead_service.LeadNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except lead_service.ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
