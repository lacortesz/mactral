"""E2-H3/E2-H4: cambio de estado del lead y clasificación al cerrar venta."""
from sqlalchemy.orm import Session

from app.clients import projects_client
from app.domain import ESTADO_SIGUIENTE, EstadoLead, LineaNegocio, Rol, TipoClasificacion
from app.models import EstadoHistorial, Lead
from app.schemas import EstadoChange
from app.services import stock_service
from app.services.lead_service import Actor, can_edit_lead, get_lead_detail

MENSAJE_TRANSICION_INVALIDA = "Primero cambia el estado a Enviada"

# E2-H4: por clasificación, el prefijo del código, el tipo de proyecto y los
# módulos que se activan en el Registro Maestro. GM abre el flujo completo
# (Importaciones); Stock va directo a Técnico (flujo corto).
_CLASIFICACION_CONFIG: dict[TipoClasificacion, dict] = {
    TipoClasificacion.GM: {
        "crp_prefix": "GM",
        "tipo": "GM - Importación",
        "modulos": [
            {"modulo": "comercial", "estado": "CERRADO"},
            {"modulo": "reg-maestro", "estado": "CERRADO"},
            {"modulo": "importaciones", "estado": "EN_CURSO"},
            {"modulo": "tecnico", "estado": "PENDIENTE"},
        ],
    },
    TipoClasificacion.STOCK_MOBILITY: {
        "crp_prefix": "STMB",
        "tipo": "Stock - Mobility",
        "modulos": [
            {"modulo": "comercial", "estado": "CERRADO"},
            {"modulo": "reg-maestro", "estado": "CERRADO"},
            {"modulo": "importaciones", "estado": "CERRADO"},
            {"modulo": "tecnico", "estado": "EN_CURSO"},
        ],
    },
    TipoClasificacion.STOCK_INDUSTRY: {
        "crp_prefix": "STIN",
        "tipo": "Stock - Industry",
        "modulos": [
            {"modulo": "comercial", "estado": "CERRADO"},
            {"modulo": "reg-maestro", "estado": "CERRADO"},
            {"modulo": "importaciones", "estado": "CERRADO"},
            {"modulo": "tecnico", "estado": "EN_CURSO"},
        ],
    },
}

_STOCK_LINEA: dict[TipoClasificacion, LineaNegocio] = {
    TipoClasificacion.STOCK_MOBILITY: LineaNegocio.MOBILITY,
    TipoClasificacion.STOCK_INDUSTRY: LineaNegocio.INDUSTRY,
}


class ForbiddenError(Exception):
    pass


class InvalidTransitionError(Exception):
    pass


def _activar_clasificacion(db: Session, actor: Actor, lead: Lead, raw_token: str) -> None:
    clasificacion = lead.clasificacion
    assert clasificacion is not None

    # Restricción Stock: si no hay unidades disponibles, se bloquea el
    # cierre de la venta (no se genera código ni se crea el Registro Maestro).
    if clasificacion in _STOCK_LINEA:
        stock_service.reservar_unidad(db, _STOCK_LINEA[clasificacion], lead.tipo_producto)

    config = _CLASIFICACION_CONFIG[clasificacion]
    payload = {
        "crp_prefix": config["crp_prefix"],
        "tipo": config["tipo"],
        "cliente": lead.nombre,
        "ciudad": lead.ciudad,
        "producto": lead.tipo_producto,
        "marca": lead.marca,
        "modulos": config["modulos"],
        "evento_origen": "Comercial",
        "evento_mensaje": f"Venta cerrada · lead {lead.codigo}",
    }
    resultado = projects_client.create_project(raw_token, payload)
    lead.codigo_generado = resultado["crp_code"]


def change_estado(db: Session, actor: Actor, lead_id: str, data: EstadoChange, raw_token: str = "") -> Lead:
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
        try:
            _activar_clasificacion(db, actor, lead, raw_token)
        except Exception:
            # Sin stock disponible o falla al contactar a services/projects:
            # no debe quedar ninguna mutación a medias (clasificación
            # asignada, unidad reservada) si el cierre de venta se bloquea.
            db.rollback()
            raise

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
