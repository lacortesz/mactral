"""E1-H3: ficha central del proyecto (CRP)."""
from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.domain import (
    CHECKLIST_ITEMS,
    NUMERO_ITEM_BL,
    EstadoEtapa,
    EstadoItemChecklist,
    Modulo,
    Rol,
    SemaforoColor,
    TipoItemChecklist,
    can_edit_checklist,
    editable_modules,
)
from app.models import ImportChecklistItem, Project, ProjectCounter, ProjectEvent, ProjectModuleStatus
from app.schemas import (
    ChecklistItemOut,
    ChecklistItemUpdate,
    ModuleStatusOut,
    ProjectCreate,
    ProjectDetailOut,
    TimelineEventOut,
)

MAX_SEARCH_RESULTS = 20


class ProjectNotFoundError(Exception):
    pass


class ForbiddenError(Exception):
    pass


class ChecklistItemNotFoundError(Exception):
    pass


class TransitionBlockedError(Exception):
    def __init__(self, items_pendientes: list[str]):
        self.items_pendientes = items_pendientes
        nombres = ", ".join(items_pendientes)
        super().__init__(f"Checklist incompleto. Ítems requeridos pendientes: {nombres}")


class NoChecklistError(Exception):
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

    # E4-H1 restricción: el checklist documental solo aplica a proyectos GM;
    # los STMB/STIN van directo a Técnico y nunca pasan por Importaciones.
    if data.crp_prefix == "GM":
        for orden, (numero, nombre, tipo) in enumerate(CHECKLIST_ITEMS):
            db.add(
                ImportChecklistItem(
                    project_id=project.id, orden=orden, numero=numero, nombre=nombre, tipo=tipo
                )
            )

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

    checklist = [ChecklistItemOut.model_validate(item) for item in project.checklist_items]

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
        checklist=checklist,
        ingreso_bodega_fecha=project.ingreso_bodega_fecha,
        ingreso_bodega_nota=project.ingreso_bodega_nota,
    )


def _get_project_by_code(db: Session, crp_code: str) -> Project:
    project = db.execute(
        select(Project).where(Project.crp_code.ilike(crp_code.strip()))
    ).scalar_one_or_none()
    if project is None:
        raise ProjectNotFoundError("No se encontraron proyectos con ese criterio")
    return project


def _get_checklist_item(project: Project, numero: str) -> ImportChecklistItem:
    for item in project.checklist_items:
        if item.numero == numero:
            return item
    raise ChecklistItemNotFoundError(f"El ítem {numero} no existe en el checklist de este proyecto")


def update_checklist_item(
    db: Session,
    actor_role: Rol,
    crp_code: str,
    numero: str,
    data: ChecklistItemUpdate,
    adjunto_bytes: bytes | None = None,
    adjunto_nombre: str | None = None,
) -> ImportChecklistItem:
    if not can_edit_checklist(actor_role):
        raise ForbiddenError("Solo el rol Importaciones (o Gerencia) puede cambiar el checklist.")

    project = _get_project_by_code(db, crp_code)
    item = _get_checklist_item(project, numero)

    item.estado = data.estado
    item.nota = data.nota
    item.fecha = datetime.utcnow()
    if adjunto_bytes is not None:
        item.adjunto_bytes = adjunto_bytes
        item.adjunto_nombre = adjunto_nombre

    # E4-H2: archivar el BL/guía aérea dispara automáticamente la solicitud
    # de Anticipo 2 a Financiero, una sola vez por proyecto.
    if (
        numero == NUMERO_ITEM_BL
        and data.estado == EstadoItemChecklist.ARCHIVADO
        and not project.notificado_anticipo2
    ):
        now = datetime.utcnow()
        db.add(
            ProjectEvent(
                project_id=project.id,
                fecha=now,
                origen="Sistema",
                mensaje=f"Proyecto {project.crp_code} — BL recibido. Solicitar Anticipo 2",
            )
        )
        db.add(
            ProjectEvent(
                project_id=project.id,
                fecha=now,
                origen="Sistema",
                mensaje="Correo enviado al Administrador notificando la solicitud de Anticipo 2",
            )
        )
        project.notificado_anticipo2 = True

    db.commit()
    db.refresh(item)
    return item


def get_checklist_attachment(db: Session, crp_code: str, numero: str) -> ImportChecklistItem:
    project = _get_project_by_code(db, crp_code)
    return _get_checklist_item(project, numero)


def _items_requeridos_pendientes(project: Project) -> list[str]:
    return [
        item.nombre
        for item in project.checklist_items
        if item.tipo == TipoItemChecklist.REQUERIDO and item.estado == EstadoItemChecklist.PENDIENTE
    ]


def enviar_a_tecnico(
    db: Session, actor_role: Rol, crp_code: str, ingreso_bodega_nota: str | None = None
) -> Project:
    """E4-H3: habilita el paso de Importaciones (CRPL) a Técnico. Restricción:
    solo aplica a proyectos GM (los STMB/STIN ya nacen con Técnico en curso,
    sin pasar por este checklist)."""
    if not can_edit_checklist(actor_role):
        raise ForbiddenError("Solo el rol Importaciones (o Gerencia) puede enviar el proyecto a Técnico.")

    project = _get_project_by_code(db, crp_code)
    if not project.checklist_items:
        raise NoChecklistError("Este proyecto no tiene checklist de importación (no es un proyecto GM).")

    pendientes = _items_requeridos_pendientes(project)
    nota = (ingreso_bodega_nota or "").strip()

    if pendientes and not nota:
        # Escenario 3: ni el checklist está completo ni hay ingreso a bodega
        # confirmado con justificación — la transición queda bloqueada.
        raise TransitionBlockedError(pendientes)

    now = datetime.utcnow()
    if pendientes:
        # Escenario 2: excepción de ingreso a bodega con checklist incompleto.
        project.ingreso_bodega_fecha = now
        project.ingreso_bodega_nota = nota
        db.add(
            ProjectEvent(
                project_id=project.id,
                fecha=now,
                origen="Importaciones",
                mensaje=(
                    "Ingreso a bodega confirmado con checklist incompleto "
                    f"({', '.join(pendientes)}) · Motivo: {nota}"
                ),
            )
        )
    else:
        # Escenario 1: checklist completo (todo Archivado o No Aplica).
        db.add(
            ProjectEvent(
                project_id=project.id,
                fecha=now,
                origen="Sistema",
                mensaje="Checklist de importación completo → módulo Técnico",
            )
        )

    for m in project.module_statuses:
        if m.modulo == Modulo.IMPORTACIONES:
            m.estado = EstadoEtapa.CERRADO
        elif m.modulo == Modulo.TECNICO:
            m.estado = EstadoEtapa.EN_CURSO

    db.commit()
    db.refresh(project)
    return project
