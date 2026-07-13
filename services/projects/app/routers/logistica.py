from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_user
from app.schemas import CuentaPorPagarCreate, CuentaPorPagarOut, CuentaPorPagarPagoCreate
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


@router.patch("/{gasto_id}/pago", response_model=CuentaPorPagarOut)
def marcar_pagada(
    crp_code: str,
    gasto_id: str,
    payload: CuentaPorPagarPagoCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        cxp = logistica_service.marcar_pagada(db, current_user, crp_code, gasto_id, payload)
        return _to_out(cxp)
    except project_service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except project_service.ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except logistica_service.GastoLogisticoNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except logistica_service.GastoYaPagadoError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.patch("/{gasto_id}/soporte", response_model=CuentaPorPagarOut)
async def adjuntar_soporte(
    crp_code: str,
    gasto_id: str,
    soporte: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    soporte_bytes = await soporte.read()
    try:
        cxp = logistica_service.adjuntar_soporte(
            db, current_user, crp_code, gasto_id, soporte_bytes, soporte.filename
        )
        return _to_out(cxp)
    except project_service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except project_service.ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except logistica_service.GastoLogisticoNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{gasto_id}/soporte")
def get_soporte_attachment(
    crp_code: str,
    gasto_id: str,
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(get_current_user),
):
    try:
        cxp = logistica_service.get_gasto_attachment(db, crp_code, gasto_id)
    except project_service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except logistica_service.GastoLogisticoNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if cxp.soporte_bytes is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El gasto no tiene un soporte adjunto")

    return Response(
        content=cxp.soporte_bytes,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{cxp.soporte_nombre or gasto_id}"'},
    )
