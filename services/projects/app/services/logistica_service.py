"""E8-H1: registro de programación logística (vuelo/hospedaje/transporte/
viáticos). Cada gasto logístico se guarda como una CuentaPorPagar —el
mismo modelo que consolida E7-H3 y que se imputa automáticamente al
proyecto por su project_id (E8-H3), sin necesidad de código adicional."""
from datetime import datetime
from typing import Protocol

from sqlalchemy.orm import Session

from app.domain import Rol, can_manage_logistica
from app.models import CuentaPorPagar, ProjectEvent
from app.schemas import CuentaPorPagarCreate
from app.services.project_service import ForbiddenError, get_project_by_code


class Actor(Protocol):
    id: str
    name: str
    role: Rol


class GastoLogisticoNotFoundError(Exception):
    pass


def list_gastos_logisticos(db: Session, crp_code: str) -> list[CuentaPorPagar]:
    project = get_project_by_code(db, crp_code)
    return project.cuentas_por_pagar


def _get_gasto(project, gasto_id: str) -> CuentaPorPagar:
    for cxp in project.cuentas_por_pagar:
        if cxp.id == gasto_id:
            return cxp
    raise GastoLogisticoNotFoundError(f"El gasto logístico {gasto_id} no existe en este proyecto")


def get_gasto_attachment(db: Session, crp_code: str, gasto_id: str) -> CuentaPorPagar:
    project = get_project_by_code(db, crp_code)
    return _get_gasto(project, gasto_id)


def registrar_gasto_logistico(db: Session, actor: Actor, crp_code: str, data: CuentaPorPagarCreate) -> CuentaPorPagar:
    if not can_manage_logistica(actor.role):
        raise ForbiddenError("Solo Administrativo (Logística) o Gerencia pueden registrar gastos logísticos.")

    project = get_project_by_code(db, crp_code)
    cxp = CuentaPorPagar(
        project_id=project.id,
        tipo=data.tipo,
        proveedor=data.proveedor,
        concepto=data.concepto,
        monto=data.monto,
        moneda=data.moneda,
        tasa_cop=data.tasa_cop,
        fecha_vencimiento=data.fecha_vencimiento,
        autorizado_gg=data.autorizado_gg,
    )
    db.add(cxp)
    db.add(
        ProjectEvent(
            project_id=project.id,
            fecha=datetime.utcnow(),
            origen="Logística",
            mensaje=f"Gasto logístico registrado: {data.tipo.value} — {data.proveedor} — "
            f"{data.moneda} {data.monto:,.0f}".replace(",", "."),
        )
    )
    db.commit()
    db.refresh(cxp)
    return cxp


def adjuntar_soporte(
    db: Session, actor: Actor, crp_code: str, gasto_id: str, soporte_bytes: bytes, soporte_nombre: str
) -> CuentaPorPagar:
    """E8-H2: carga del soporte (factura/comprobante) de un gasto logístico
    ya registrado."""
    if not can_manage_logistica(actor.role):
        raise ForbiddenError("Solo Administrativo (Logística) o Gerencia pueden adjuntar soportes.")

    project = get_project_by_code(db, crp_code)
    cxp = _get_gasto(project, gasto_id)
    cxp.soporte_bytes = soporte_bytes
    cxp.soporte_nombre = soporte_nombre

    db.add(
        ProjectEvent(
            project_id=project.id,
            fecha=datetime.utcnow(),
            origen="Logística",
            mensaje=f"Soporte adjuntado al gasto logístico: {cxp.proveedor} — {cxp.concepto}",
        )
    )
    db.commit()
    db.refresh(cxp)
    return cxp
