"""E2-H3: cambio de estado del lead (Cotizar -> Enviada -> Vendido)."""
from app.domain import ESTADO_SIGUIENTE, EstadoLead, Rol
from app.models import EstadoHistorial, Lead
from app.schemas import EstadoChange
from app.services.lead_service import Actor, can_edit_lead, get_lead_detail

from sqlalchemy.orm import Session

MENSAJE_TRANSICION_INVALIDA = "Primero cambia el estado a Enviada"


class ForbiddenError(Exception):
    pass


class InvalidTransitionError(Exception):
    pass


def change_estado(db: Session, actor: Actor, lead_id: str, data: EstadoChange) -> Lead:
    lead = get_lead_detail(db, lead_id)

    if not can_edit_lead(actor, lead):
        raise ForbiddenError("Solo el vendedor asignado o Gerencia pueden editar este lead.")

    siguiente = ESTADO_SIGUIENTE.get(lead.estado)
    # Restricción E2-H3: los estados son secuenciales y no reversibles. Un
    # salto (p. ej. Cotizar -> Vendido) o un retroceso quedan bloqueados.
    if siguiente is None or data.estado != siguiente:
        raise InvalidTransitionError(MENSAJE_TRANSICION_INVALIDA)

    if data.estado == EstadoLead.VENDIDO:
        # Restricción E2-H4: la clasificación es inmutable una vez
        # confirmada; solo Gerencia podría anularla (no soportado aún).
        if lead.clasificacion is not None and actor.role != Rol.GERENCIA:
            raise ForbiddenError("La clasificación ya fue confirmada y no puede modificarse.")
        lead.clasificacion = data.clasificacion

    historial = EstadoHistorial(
        lead_id=lead.id,
        estado_anterior=lead.estado,
        estado_nuevo=data.estado,
        usuario_id=actor.id,
        usuario_nombre=actor.name,
    )
    db.add(historial)
    lead.estado = data.estado
    db.commit()
    db.refresh(lead)
    return lead
