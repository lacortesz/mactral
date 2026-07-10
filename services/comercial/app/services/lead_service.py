"""E2-H1: registro de lead."""
from datetime import datetime, timezone
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import LEAD_CODE_PREFIX, EstadoLead, LineaNegocio, Rol, can_manage_leads
from app.models import Lead, LeadCounter, LeadInteraction
from app.schemas import InteractionCreate, LeadCreate


class Actor(Protocol):
    id: str
    name: str
    role: Rol


class ForbiddenError(Exception):
    pass


class LeadNotFoundError(Exception):
    pass


def _current_year() -> int:
    return datetime.now(timezone.utc).year


def _next_lead_code(db: Session, linea: LineaNegocio) -> str:
    year = _current_year()
    # Escenario de concurrencia (mismo principio que E3-H1): se bloquea la
    # fila del contador para que dos altas simultáneas no reciban el mismo
    # consecutivo.
    counter = db.execute(
        select(LeadCounter)
        .where(LeadCounter.linea_negocio == linea, LeadCounter.anio == year)
        .with_for_update()
    ).scalar_one_or_none()

    if counter is None:
        counter = LeadCounter(linea_negocio=linea, anio=year, ultimo_valor=0)
        db.add(counter)
        db.flush()

    counter.ultimo_valor += 1
    prefix = LEAD_CODE_PREFIX[linea]
    yy = year % 100
    return f"{prefix}{yy:02d}-{counter.ultimo_valor:03d}"


def list_leads(db: Session) -> list[Lead]:
    return list(db.execute(select(Lead).order_by(Lead.created_at.desc())).scalars())


def get_lead_detail(db: Session, lead_id: str) -> Lead:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise LeadNotFoundError("Lead no encontrado")
    return lead


def create_lead(db: Session, actor: Actor, data: LeadCreate) -> Lead:
    if not can_manage_leads(actor.role):
        raise ForbiddenError("Solo el vendedor (Comercial) o Gerencia pueden registrar leads.")

    codigo = _next_lead_code(db, data.linea_negocio)

    lead = Lead(
        codigo=codigo,
        nombre=data.nombre.strip(),
        telefono=(data.telefono or "").strip() or None,
        correo=(data.correo or "").strip() or None,
        ciudad=data.ciudad.strip(),
        canal_entrada=data.canal_entrada.strip(),
        linea_negocio=data.linea_negocio,
        tipo_producto=data.tipo_producto.strip(),
        marca=data.marca.strip(),
        estado=EstadoLead.COTIZAR,
        vendedor_id=actor.id,
        vendedor_nombre=actor.name,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def add_interaction(
    db: Session, actor: Actor, lead_id: str, data: InteractionCreate
) -> LeadInteraction:
    lead = get_lead_detail(db, lead_id)

    # Restricción E2-H1: solo el vendedor asignado y Gerencia pueden editar el lead.
    if actor.role != Rol.GERENCIA and actor.id != lead.vendedor_id:
        raise ForbiddenError("Solo el vendedor asignado o Gerencia pueden editar este lead.")

    interaction = LeadInteraction(
        lead_id=lead.id,
        canal=data.canal.strip(),
        resumen=data.resumen.strip(),
        usuario_id=actor.id,
        usuario_nombre=actor.name,
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    return interaction
