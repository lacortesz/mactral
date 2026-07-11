"""E5-H1/E5-H2/E5-H3: instalación, acta de entrega y semáforo de cumplimiento
(módulo Técnico)."""
from datetime import date, datetime
from typing import Protocol

from sqlalchemy.orm import Session

from app.domain import EstadoEtapa, EstadoInstalacion, Modulo, Rol, SemaforoColor, can_manage_installation
from app.models import Installation, InstallationReprogramming, Project, ProjectEvent
from app.schemas import ActaEntregaCreate, InstallationCreate, InstallationReprogram
from app.services.project_service import ForbiddenError, get_project_by_code


class Actor(Protocol):
    id: str
    name: str
    role: Rol


class InstallationAlreadyExistsError(Exception):
    pass


class InstallationNotFoundError(Exception):
    pass


class InvalidInstallationDateError(Exception):
    pass


def _check_fecha_no_anterior_a_bodega(project: Project, fecha_instalacion) -> None:
    # Restricción E5-H1: la fecha de instalación no puede ser anterior al
    # registro del ingreso a bodega en CRPL.
    if project.ingreso_bodega_fecha is not None and fecha_instalacion < project.ingreso_bodega_fecha.date():
        raise InvalidInstallationDateError(
            "La fecha de instalación no puede ser anterior al ingreso a bodega registrado en Importaciones."
        )


def programar_instalacion(db: Session, actor: Actor, crp_code: str, data: InstallationCreate) -> Installation:
    if not can_manage_installation(actor.role):
        raise ForbiddenError("Solo el Coordinador técnico (o Gerencia) puede programar instalaciones.")

    project = get_project_by_code(db, crp_code)
    if project.instalacion is not None:
        raise InstallationAlreadyExistsError(
            "Este proyecto ya tiene una instalación programada; usa la reprogramación."
        )

    _check_fecha_no_anterior_a_bodega(project, data.fecha_instalacion)

    installation = Installation(
        project_id=project.id,
        fecha_instalacion=data.fecha_instalacion,
        tecnico_id=data.tecnico_id,
        tecnico_nombre=data.tecnico_nombre,
        ciudad=data.ciudad,
        estado=EstadoInstalacion.PROGRAMADO,
    )
    db.add(installation)
    db.commit()
    db.refresh(installation)
    return installation


def reprogramar_instalacion(
    db: Session, actor: Actor, crp_code: str, data: InstallationReprogram
) -> Installation:
    if not can_manage_installation(actor.role):
        raise ForbiddenError("Solo el Coordinador técnico (o Gerencia) puede reprogramar instalaciones.")

    project = get_project_by_code(db, crp_code)
    installation = project.instalacion
    if installation is None:
        raise InstallationNotFoundError("Este proyecto todavía no tiene una instalación programada.")

    _check_fecha_no_anterior_a_bodega(project, data.fecha_instalacion)

    db.add(
        InstallationReprogramming(
            installation_id=installation.id,
            fecha_anterior=installation.fecha_instalacion,
            fecha_nueva=data.fecha_instalacion,
            motivo=data.motivo.strip(),
            usuario_id=actor.id,
            usuario_nombre=actor.name,
        )
    )
    installation.fecha_instalacion = data.fecha_instalacion

    db.commit()
    db.refresh(installation)
    return installation


def registrar_acta(
    db: Session,
    actor: Actor,
    crp_code: str,
    data: ActaEntregaCreate,
    acta_bytes: bytes | None = None,
    acta_nombre: str | None = None,
) -> Installation:
    """E5-H2: registra el acta de entrega y cierra el proyecto técnico.
    Escenario 2: no adjuntar el acta NO bloquea el registro (el frontend
    muestra la advertencia usando installation.tiene_acta == False)."""
    if not can_manage_installation(actor.role):
        raise ForbiddenError("Solo el Coordinador técnico (o Gerencia) puede registrar el acta de entrega.")

    project = get_project_by_code(db, crp_code)
    installation = project.instalacion
    if installation is None:
        raise InstallationNotFoundError("Este proyecto todavía no tiene una instalación programada.")

    installation.fecha_real_entrega = data.fecha_real_entrega
    installation.observaciones = data.observaciones
    installation.estado = EstadoInstalacion.COMPLETADO
    if acta_bytes is not None:
        installation.acta_bytes = acta_bytes
        installation.acta_nombre = acta_nombre

    project.etapa_actual = EstadoEtapa.ENTREGADO
    for m in project.module_statuses:
        if m.modulo == Modulo.TECNICO:
            m.estado = EstadoEtapa.CERRADO

    # E5-H3: al cerrar la entrega, el semáforo del proyecto queda con el
    # resultado final (comparación fecha proyectada vs. real).
    color, detalle = calcular_semaforo(installation)
    project.semaforo_color = color
    project.semaforo_detalle = detalle

    now = datetime.utcnow()
    db.add(
        ProjectEvent(
            project_id=project.id,
            fecha=now,
            origen="Técnico",
            mensaje=f"Acta de entrega registrada · firma {data.fecha_real_entrega.isoformat()}",
        )
    )
    db.add(
        ProjectEvent(
            project_id=project.id,
            fecha=now,
            origen="Sistema",
            mensaje="Proyecto entregado. Solicitar Pago Final",
        )
    )

    db.commit()
    db.refresh(installation)
    return installation


def calcular_semaforo(installation: Installation) -> tuple[SemaforoColor, str]:
    """E5-H3: compara la fecha proyectada con la real (o con hoy, si sigue
    Programada) para determinar el semáforo de cumplimiento de entrega."""
    if installation.estado == EstadoInstalacion.COMPLETADO and installation.fecha_real_entrega is not None:
        diff = (installation.fecha_real_entrega - installation.fecha_instalacion).days
        if diff < 0:
            return SemaforoColor.VERDE, f"Entrega anticipada — {-diff} día(s) antes"
        if diff == 0:
            return SemaforoColor.AMARILLO, "Entrega a tiempo"
        return SemaforoColor.ROJO, f"Entrega tardía — {diff} día(s) de retraso"

    # Escenario 4: la fecha programada ya pasó y la instalación sigue en
    # estado Programado — el semáforo cambia a Rojo automáticamente.
    if date.today() > installation.fecha_instalacion:
        dias = (date.today() - installation.fecha_instalacion).days
        return SemaforoColor.ROJO, f"Instalación programada vencida hace {dias} día(s) sin cierre"

    return SemaforoColor.VERDE, "Instalación programada — en fecha"


def get_acta_attachment(db: Session, crp_code: str) -> Installation:
    project = get_project_by_code(db, crp_code)
    installation = project.instalacion
    if installation is None:
        raise InstallationNotFoundError("Este proyecto todavía no tiene una instalación programada.")
    return installation
