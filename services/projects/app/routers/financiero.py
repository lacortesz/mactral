from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_user
from app.schemas import CuotaOut, CuotaPagoCreate, CuotasConfigCreate, TableroFinancieroOut
from app.services import financiero_service, project_service

router = APIRouter(prefix="/projects/{crp_code}/cuotas", tags=["financiero"])
tablero_router = APIRouter(prefix="/projects/{crp_code}/tablero-financiero", tags=["financiero"])


@tablero_router.get("", response_model=TableroFinancieroOut)
def get_tablero_financiero(
    crp_code: str,
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(get_current_user),
):
    try:
        return financiero_service.get_tablero(db, crp_code)
    except project_service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("", response_model=list[CuotaOut])
def list_cuotas(
    crp_code: str,
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(get_current_user),
):
    try:
        return financiero_service.list_cuotas(db, crp_code)
    except project_service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("", response_model=list[CuotaOut], status_code=status.HTTP_201_CREATED)
def configurar_cuotas(
    crp_code: str,
    payload: CuotasConfigCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        project = financiero_service.configurar_cuotas(db, current_user, crp_code, payload)
        return project.cuotas
    except project_service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except project_service.ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except financiero_service.CuotasYaConfiguradasError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.patch("/{numero}/pago", response_model=CuotaOut)
def registrar_pago(
    crp_code: str,
    numero: int,
    payload: CuotaPagoCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        return financiero_service.registrar_pago(db, current_user, crp_code, numero, payload)
    except project_service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except project_service.ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except financiero_service.CuotaNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
