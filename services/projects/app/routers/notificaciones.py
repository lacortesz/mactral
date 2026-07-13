from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_user
from app.schemas import NotificacionOut
from app.services import notificacion_service

router = APIRouter(prefix="/notificaciones", tags=["notificaciones"])


def _to_out(notif) -> NotificacionOut:
    return NotificacionOut(
        id=notif.id,
        crp_code=notif.project.crp_code,
        modulo=notif.modulo,
        tipo=notif.tipo,
        mensaje=notif.mensaje,
        fecha=notif.fecha,
        leida=notif.leida,
    )


@router.get("", response_model=list[NotificacionOut])
def list_notificaciones(
    solo_no_leidas: bool = True,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    rows = notificacion_service.list_notificaciones(db, current_user, solo_no_leidas)
    return [_to_out(n) for n in rows]


@router.patch("/{notificacion_id}/leer", response_model=NotificacionOut)
def marcar_leida(
    notificacion_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        notif = notificacion_service.marcar_leida(db, current_user, notificacion_id)
        return _to_out(notif)
    except notificacion_service.NotificacionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
