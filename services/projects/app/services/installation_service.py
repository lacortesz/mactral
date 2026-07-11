"""E5-H1/E5-H2: programación de instalación y acta de entrega (módulo Técnico)."""
from datetime import datetime
from typing import Protocol

from sqlalchemy.orm import Session

from app.domain import EstadoInstalacion, Rol, can_manage_installation
from app.models import Installation, InstallationReprogramming, Project
from app.schemas import InstallationCreate, InstallationReprogram
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
