"""E1-H3: ficha central del proyecto (CRP)."""
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.domain import EstadoEtapa, Rol, editable_modules
from app.models import Project
from app.schemas import ModuleStatusOut, ProjectDetailOut, TimelineEventOut

MAX_SEARCH_RESULTS = 20


class ProjectNotFoundError(Exception):
    pass


def search_projects(db: Session, query: str) -> list[Project]:
    # Escenario 2: si no hay coincidencias, se devuelve una lista vacía
    # (el llamador decide el mensaje "No se encontraron proyectos...").
    like = f"%{query.strip()}%"
    stmt = (
        select(Project)
        .where(or_(Project.crp_code.ilike(like), Project.cliente.ilike(like)))
        .order_by(Project.crp_code)
        .limit(MAX_SEARCH_RESULTS)
    )
    return list(db.execute(stmt).scalars())


def get_project_detail(db: Session, crp_code: str, actor_role: Rol) -> ProjectDetailOut:
    project = db.execute(
        select(Project).where(Project.crp_code.ilike(crp_code.strip()))
    ).scalar_one_or_none()

    if project is None:
        raise ProjectNotFoundError("No se encontraron proyectos con ese criterio")

    allowed = editable_modules(actor_role)

    modulos = [
        ModuleStatusOut(
            modulo=m.modulo,
            estado=m.estado,
            # Escenario 3 (E1-H2) / restricción E1-H3: las etapas cerradas
            # quedan bloqueadas con ícono de candado para todos los roles.
            bloqueado_por_cierre=m.estado == EstadoEtapa.CERRADO,
            editable_por_mi_rol=(m.modulo in allowed) and m.estado != EstadoEtapa.CERRADO,
        )
        for m in project.module_statuses
    ]

    linea_de_tiempo = [
        TimelineEventOut(fecha=e.fecha, origen=e.origen, mensaje=e.mensaje) for e in project.events
    ]

    return ProjectDetailOut(
        id=project.id,
        crp_code=project.crp_code,
        tipo=project.tipo,
        cliente=project.cliente,
        ciudad=project.ciudad,
        producto=project.producto,
        marca=project.marca,
        etapa_actual=project.etapa_actual,
        semaforo_color=project.semaforo_color,
        semaforo_detalle=project.semaforo_detalle,
        modulos=modulos,
        linea_de_tiempo=linea_de_tiempo,
    )
