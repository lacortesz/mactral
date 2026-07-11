from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_comercial_module
from app.schemas import (
    EstadoChange,
    InteractionCreate,
    InteractionOut,
    LeadCreate,
    LeadDetailOut,
    LeadListItem,
    QuotationCreate,
    QuotationOut,
)
from app.services import estado_service, lead_service, quotation_service

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


@router.patch("/{lead_id}/estado", response_model=LeadDetailOut)
def change_estado(
    lead_id: str,
    payload: EstadoChange,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_comercial_module),
):
    try:
        return estado_service.change_estado(db, current_user, lead_id, payload)
    except lead_service.LeadNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except estado_service.ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except estado_service.InvalidTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post(
    "/{lead_id}/quotations", response_model=QuotationOut, status_code=status.HTTP_201_CREATED
)
def create_quotation(
    lead_id: str,
    payload: QuotationCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_comercial_module),
):
    try:
        return quotation_service.create_quotation(db, current_user, lead_id, payload)
    except lead_service.LeadNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except lead_service.ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/{lead_id}/quotations", response_model=list[QuotationOut])
def list_quotations(
    lead_id: str,
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_comercial_module),
):
    try:
        return quotation_service.list_quotations(db, lead_id)
    except lead_service.LeadNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{lead_id}/quotations/{version}/pdf")
def get_quotation_pdf(
    lead_id: str,
    version: int,
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_comercial_module),
):
    try:
        quotation = quotation_service.get_quotation_pdf(db, lead_id, version)
    except lead_service.LeadNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except quotation_service.QuotationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return Response(
        content=quotation.pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{quotation.numero_cotizacion}.pdf"'
        },
    )
