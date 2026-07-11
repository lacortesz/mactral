"""E1-H3: ficha central del proyecto (CRP)."""
from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.domain import EstadoEtapa, Rol, SemaforoColor, editable_modules
from app.models import Project, ProjectCounter, ProjectEvent, ProjectModuleStatus
from app.schemas import ModuleStatusOut, ProjectCreate, ProjectDetailOut, TimelineEventOut

MAX_SEARCH_RESULTS = 20


class ProjectNotFoundError(Exception):
    pass


def _current_year() -> int:
    return datetime.now(timezone.utc).year


def _next_project_code(db: Session, prefix: str) -> str:
    year = _current_year()
    # Mismo principio que el consecutivo de leads (services/comercial): se
    # bloquea la fila del contador para evitar duplicados con altas
    # concurrentes (varias ventas cerrándose al mismo tiempo).
    counter = db.execute(
        select(ProjectCounter)
        .where(ProjectCounter.prefijo == prefix, ProjectCounter.anio == year)
        .with_for_update()
    ).scalar_one_or_none()

    if counter is None:
        counter = ProjectCounter(prefijo=prefix, anio=year, ultimo_valor=0)
        db.add(counter)
        db.flush()

    counter.ultimo_valor += 1
    yy = year % 100
    return f"{prefix}{yy:02d}-{counter.ultimo_valor:02d}"


def create_project(db: Session, data: ProjectCreate) -> Project:
    codigo = _next_project_code(db, data.crp_prefix)

    project = Project(
        crp_code=codigo,
        tipo=data.tipo,
        cliente=data.cliente,
        ciudad=data.ciudad,
        producto=data.producto,
        marca=data.marca,
        etapa_actual=EstadoEtapa.EN_CURSO,
        semaforo_color=SemaforoColor.VERDE,
        semaforo_detalle=data.semaforo_detalle,
    )
    db.add(project)
    db.flush()

    for m in data.modulos:
        db.add(ProjectModuleStatus(project_id=project.id, modulo=m.modulo, estado=m.estado))

    now = datetime.utcnow()
    db.add(ProjectEvent(project_id=project.id, fecha=now, origen=data.evento_origen, mensaje=data.evento_mensaje))
    db.add(
        ProjectEvent(
            project_id=project.id,
            fecha=now,
            origen="Sistema",
            mensaje=f"Código {codigo} generado automáticamente",
        )
    )

    db.commit()
    db.refresh(project)
    return project


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
