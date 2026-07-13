from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_user
from app.domain import Rol
from app.schemas import DashboardOut, KpisFinancierosOut, KpisOperativosOut, RentabilidadOut
from app.services import reportes_service

router = APIRouter(prefix="/reportes", tags=["reportes"])


@router.get("/dashboard", response_model=DashboardOut)
def get_dashboard(
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(get_current_user),
):
    return reportes_service.get_dashboard(db)


@router.get("/rentabilidad", response_model=RentabilidadOut)
def get_rentabilidad(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    # E10-H2: vista gerencial — solo Gerencia ve el margen de todos los proyectos.
    if current_user.role != Rol.GERENCIA:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Solo Gerencia puede ver la rentabilidad consolidada."
        )
    return reportes_service.get_rentabilidad(db)


@router.get("/kpis-operativos", response_model=KpisOperativosOut)
def get_kpis_operativos(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    # E11-H1: KPIs operativos globales — visibles solo para Gerencia.
    if current_user.role != Rol.GERENCIA:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Solo Gerencia puede ver los KPIs operativos."
        )
    return reportes_service.get_kpis_operativos(db)


@router.get("/kpis-financieros", response_model=KpisFinancierosOut)
def get_kpis_financieros(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    # E11-H2: KPIs financieros globales — visibles solo para Gerencia.
    if current_user.role != Rol.GERENCIA:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Solo Gerencia puede ver los KPIs financieros."
        )
    return reportes_service.get_kpis_financieros(db)
