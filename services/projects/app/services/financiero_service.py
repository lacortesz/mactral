"""E7-H1: definición de cuotas/anticipos y registro de pagos por proyecto."""
from datetime import datetime
from typing import Protocol

from sqlalchemy.orm import Session

from app.domain import EstadoCuota, Rol, can_manage_financiero
from app.models import Cuota, Project, ProjectEvent
from app.schemas import CuotaPagoCreate, CuotasConfigCreate
from app.services.project_service import ForbiddenError, get_project_by_code


class Actor(Protocol):
    id: str
    name: str
    role: Rol


class CuotaNotFoundError(Exception):
    pass


class CuotasYaConfiguradasError(Exception):
    pass


def list_cuotas(db: Session, crp_code: str) -> list[Cuota]:
    project = get_project_by_code(db, crp_code)
    return project.cuotas


def configurar_cuotas(db: Session, actor: Actor, crp_code: str, data: CuotasConfigCreate) -> Project:
    if not can_manage_financiero(actor.role):
        raise ForbiddenError("Solo Administrativo (Financiero) o Gerencia pueden configurar las cuotas.")

    project = get_project_by_code(db, crp_code)
    if project.cuotas:
        raise CuotasYaConfiguradasError(
            "Este proyecto ya tiene cuotas configuradas; el valor del contrato requiere aprobación de "
            "Gerencia para modificarse."
        )

    project.valor_contrato = data.valor_contrato
    project.costo_fabricacion = data.costo_fabricacion

    for cuota_in in data.cuotas:
        db.add(
            Cuota(
                project_id=project.id,
                numero=cuota_in.numero,
                etiqueta=cuota_in.etiqueta,
                monto=cuota_in.monto,
                porcentaje=cuota_in.porcentaje,
                fecha_vencimiento=cuota_in.fecha_vencimiento,
                estado=EstadoCuota.PENDIENTE,
            )
        )

    db.add(
        ProjectEvent(
            project_id=project.id,
            fecha=datetime.utcnow(),
            origen="Financiero",
            mensaje=f"Esquema de pagos configurado · {len(data.cuotas)} cuota(s) · contrato ${data.valor_contrato:,.0f}".replace(
                ",", "."
            ),
        )
    )

    db.commit()
    db.refresh(project)
    return project


def registrar_pago(db: Session, actor: Actor, crp_code: str, numero: int, data: CuotaPagoCreate) -> Cuota:
    if not can_manage_financiero(actor.role):
        raise ForbiddenError("Solo Administrativo (Financiero) o Gerencia pueden registrar pagos.")

    project = get_project_by_code(db, crp_code)
    cuota = next((c for c in project.cuotas if c.numero == numero), None)
    if cuota is None:
        raise CuotaNotFoundError(f"La cuota {numero} no existe en este proyecto")

    cuota.estado = EstadoCuota.PAGADO
    cuota.fecha_pago = data.fecha_pago
    cuota.monto_pagado = data.monto_pagado
    cuota.referencia_bancaria = data.referencia_bancaria

    db.add(
        ProjectEvent(
            project_id=project.id,
            fecha=datetime.utcnow(),
            origen="Financiero",
            mensaje=f"{cuota.etiqueta} recibido · ${data.monto_pagado:,.0f}".replace(",", "."),
        )
    )

    db.commit()
    db.refresh(cuota)
    return cuota
