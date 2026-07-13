"""E9-H2: bandeja de notificaciones por módulo — asignación de un proyecto
a un módulo y alerta de inactividad (5 días sin eventos nuevos)."""
from datetime import datetime, timedelta
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import ROLE_MODULE_ACCESS, Modulo, Rol
from app.models import Notificacion, Project

DIAS_INACTIVIDAD = 5

TIPO_ASIGNACION = "ASIGNACION"
TIPO_INACTIVIDAD = "INACTIVIDAD"


class Actor(Protocol):
    id: str
    name: str
    role: Rol


class NotificacionNotFoundError(Exception):
    pass


def notificar_asignacion(db: Session, project: Project, modulo: Modulo) -> None:
    db.add(
        Notificacion(
            project_id=project.id,
            modulo=modulo,
            tipo=TIPO_ASIGNACION,
            mensaje=f"Proyecto {project.crp_code} ({project.cliente}) asignado al módulo",
            fecha=datetime.utcnow(),
        )
    )


def _evaluar_inactividad(db: Session) -> None:
    """Recorre los proyectos con algún módulo En curso y, si no ha habido
    eventos nuevos en los últimos 5 días, genera una notificación de
    inactividad (una sola vez mientras no se resuelva/lea)."""
    limite = datetime.utcnow() - timedelta(days=DIAS_INACTIVIDAD)
    proyectos = db.execute(select(Project)).scalars().all()
    notificaciones_activas = db.execute(
        select(Notificacion).where(Notificacion.tipo == TIPO_INACTIVIDAD, Notificacion.leida.is_(False))
    ).scalars().all()
    ya_notificadas = {(n.project_id, n.modulo) for n in notificaciones_activas}
    cambios = False

    for project in proyectos:
        ultimo_evento = max((e.fecha for e in project.events), default=None)
        if ultimo_evento is None or ultimo_evento > limite:
            continue

        for m in project.module_statuses:
            if m.estado.value != "EN_CURSO":
                continue
            if (project.id, m.modulo) in ya_notificadas:
                continue
            db.add(
                Notificacion(
                    project_id=project.id,
                    modulo=m.modulo,
                    tipo=TIPO_INACTIVIDAD,
                    mensaje=(
                        f"Proyecto {project.crp_code} ({project.cliente}) sin actividad hace más de "
                        f"{DIAS_INACTIVIDAD} días en este módulo"
                    ),
                    fecha=datetime.utcnow(),
                )
            )
            cambios = True

    if cambios:
        db.commit()


def list_notificaciones(db: Session, actor: Actor, solo_no_leidas: bool = True) -> list[Notificacion]:
    _evaluar_inactividad(db)

    modulos_visibles = ROLE_MODULE_ACCESS.get(actor.role, set())
    stmt = select(Notificacion).order_by(Notificacion.fecha.desc())
    rows = db.execute(stmt).scalars().all()
    rows = [n for n in rows if n.modulo in modulos_visibles]
    if solo_no_leidas:
        rows = [n for n in rows if not n.leida]
    return rows


def marcar_leida(db: Session, actor: Actor, notificacion_id: str) -> Notificacion:
    notif = db.get(Notificacion, notificacion_id)
    if notif is None or notif.modulo not in ROLE_MODULE_ACCESS.get(actor.role, set()):
        raise NotificacionNotFoundError(f"La notificación {notificacion_id} no existe")

    notif.leida = True
    db.commit()
    db.refresh(notif)
    return notif
