from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_user
from app.domain import Rol
from app.schemas import DashboardOut, RentabilidadOut
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
