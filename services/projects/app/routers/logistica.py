from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_user
from app.schemas import CuentaPorPagarCreate, CuentaPorPagarOut
from app.services import logistica_service, project_service

router = APIRouter(prefix="/projects/{crp_code}/logistica", tags=["logistica"])


def _to_out(cxp) -> CuentaPorPagarOut:
    return CuentaPorPagarOut(
        id=cxp.id,
        crp_code=cxp.project.crp_code,
        tipo=cxp.tipo,
        proveedor=cxp.proveedor,
        concepto=cxp.concepto,
        monto=cxp.monto,
        moneda=cxp.moneda,
        tasa_cop=cxp.tasa_cop,
        monto_cop=cxp.monto_cop,
        fecha_vencimiento=cxp.fecha_vencimiento,
        estado=cxp.estado,
        fecha_pago=cxp.fecha_pago,
        tiene_soporte=cxp.tiene_soporte,
        autorizado_gg=cxp.autorizado_gg,
    )


@router.get("", response_model=list[CuentaPorPagarOut])
def list_gastos_logisticos(
    crp_code: str,
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(get_current_user),
):
    try:
        rows = logistica_service.list_gastos_logisticos(db, crp_code)
    except project_service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return [_to_out(cxp) for cxp in rows]


@router.post("", response_model=CuentaPorPagarOut, status_code=status.HTTP_201_CREATED)
def registrar_gasto_logistico(
    crp_code: str,
    payload: CuentaPorPagarCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        cxp = logistica_service.registrar_gasto_logistico(db, current_user, crp_code, payload)
        return _to_out(cxp)
    except project_service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except project_service.ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
