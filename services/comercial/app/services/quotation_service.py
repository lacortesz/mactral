"""E2-H2: cotización en PDF con la calculadora oficial."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain import EstadoLead
from app.models import EstadoHistorial, Quotation
from app.pdf import build_quotation_pdf
from app.schemas import QuotationCreate
from app.services.lead_service import Actor, ForbiddenError, can_edit_lead, get_lead_detail


class QuotationNotFoundError(Exception):
    pass


def create_quotation(db: Session, actor: Actor, lead_id: str, data: QuotationCreate) -> Quotation:
    lead = get_lead_detail(db, lead_id)

    # Misma restricción que E2-H1: solo el vendedor asignado o Gerencia
    # pueden generar/regenerar la cotización del lead.
    if not can_edit_lead(actor, lead):
        raise ForbiddenError("Solo el vendedor asignado o Gerencia pueden editar este lead.")

    next_version = (
        db.execute(select(func.max(Quotation.version)).where(Quotation.lead_id == lead.id)).scalar() or 0
    ) + 1

    quotation = Quotation(
        lead_id=lead.id,
        version=next_version,
        valor_equipo=data.valor_equipo,
        tipo_pago=data.tipo_pago,
        anticipo_inicial_pct=data.anticipo_inicial_pct,
        segundo_anticipo_pct=data.segundo_anticipo_pct,
        saldo_final_pct=data.saldo_final_pct,
        fecha_estimada_entrega=data.fecha_estimada_entrega,
        pdf_bytes=b"",
    )
    quotation.lead = lead  # necesario para numero_cotizacion antes del commit
    quotation.pdf_bytes = build_quotation_pdf(lead, quotation)

    db.add(quotation)

    # Escenario 1 (E2-H2), punto 3: el estado cambia a Enviada la primera
    # vez que se genera una cotización. Al regenerar (versión > 1) el lead
    # ya está en Enviada o más adelante, así que no se toca.
    if lead.estado == EstadoLead.COTIZAR:
        db.add(
            EstadoHistorial(
                lead_id=lead.id,
                estado_anterior=EstadoLead.COTIZAR,
                estado_nuevo=EstadoLead.ENVIADA,
                usuario_id=actor.id,
                usuario_nombre=actor.name,
            )
        )
        lead.estado = EstadoLead.ENVIADA

    db.commit()
    db.refresh(quotation)
    return quotation


def list_quotations(db: Session, lead_id: str) -> list[Quotation]:
    get_lead_detail(db, lead_id)  # valida que el lead exista
    return list(
        db.execute(
            select(Quotation).where(Quotation.lead_id == lead_id).order_by(Quotation.version)
        ).scalars()
    )


def get_quotation_pdf(db: Session, lead_id: str, version: int) -> Quotation:
    get_lead_detail(db, lead_id)
    quotation = db.execute(
        select(Quotation).where(Quotation.lead_id == lead_id, Quotation.version == version)
    ).scalar_one_or_none()
    if quotation is None:
        raise QuotationNotFoundError("Cotización no encontrada")
    return quotation
