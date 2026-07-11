import pytest

from app.domain import EstadoLead, LineaNegocio, Rol, TipoClasificacion
from app.schemas import EstadoChange, LeadCreate
from app.services import estado_service, lead_service


class _Actor:
    def __init__(self, id: str, name: str, role: Rol):
        self.id = id
        self.name = name
        self.role = role


VENDEDOR = _Actor("u1", "Carlos Martínez", Rol.COMERCIAL)
OTRO_VENDEDOR = _Actor("u2", "María Angulo", Rol.COMERCIAL)
GERENCIA = _Actor("u3", "Maya Lozada", Rol.GERENCIA)

LEAD_INPUT = LeadCreate(
    nombre="Gustavo Ramírez",
    telefono="3001234567",
    ciudad="Bogotá",
    canal_entrada="Referido",
    linea_negocio=LineaNegocio.MOBILITY,
    tipo_producto="SSE Curva",
    marca="Stannah",
)


def _make_lead(db_session):
    return lead_service.create_lead(db_session, VENDEDOR, LEAD_INPUT)


# Escenario 1 (E2-H3): avance secuencial de estado.
def test_avanzar_de_cotizar_a_enviada(db_session):
    lead = _make_lead(db_session)

    updated = estado_service.change_estado(db_session, VENDEDOR, lead.id, EstadoChange(estado=EstadoLead.ENVIADA))

    assert updated.estado == EstadoLead.ENVIADA
    assert len(updated.historial_estados) == 1
    assert updated.historial_estados[0].estado_anterior == EstadoLead.COTIZAR
    assert updated.historial_estados[0].estado_nuevo == EstadoLead.ENVIADA
    assert updated.historial_estados[0].usuario_nombre == "Carlos Martínez"


def test_avanzar_de_enviada_a_vendido_requiere_clasificacion():
    with pytest.raises(Exception, match="clasificación"):
        EstadoChange(estado=EstadoLead.VENDIDO)


def test_avanzar_de_enviada_a_vendido_con_clasificacion(db_session):
    lead = _make_lead(db_session)
    estado_service.change_estado(db_session, VENDEDOR, lead.id, EstadoChange(estado=EstadoLead.ENVIADA))

    updated = estado_service.change_estado(
        db_session,
        VENDEDOR,
        lead.id,
        EstadoChange(estado=EstadoLead.VENDIDO, clasificacion=TipoClasificacion.GM),
    )

    assert updated.estado == EstadoLead.VENDIDO
    assert updated.clasificacion == TipoClasificacion.GM
    assert len(updated.historial_estados) == 2


# Escenario 2 (E2-H3): salto de estado bloqueado.
def test_saltar_de_cotizar_a_vendido_queda_bloqueado(db_session):
    lead = _make_lead(db_session)

    with pytest.raises(estado_service.InvalidTransitionError, match=estado_service.MENSAJE_TRANSICION_INVALIDA):
        estado_service.change_estado(
            db_session,
            VENDEDOR,
            lead.id,
            EstadoChange(estado=EstadoLead.VENDIDO, clasificacion=TipoClasificacion.GM),
        )


def test_retroceder_de_enviada_a_cotizar_queda_bloqueado(db_session):
    lead = _make_lead(db_session)
    estado_service.change_estado(db_session, VENDEDOR, lead.id, EstadoChange(estado=EstadoLead.ENVIADA))

    with pytest.raises(estado_service.InvalidTransitionError):
        estado_service.change_estado(db_session, VENDEDOR, lead.id, EstadoChange(estado=EstadoLead.COTIZAR))


def test_avanzar_estado_de_lead_ya_vendido_queda_bloqueado(db_session):
    lead = _make_lead(db_session)
    estado_service.change_estado(db_session, VENDEDOR, lead.id, EstadoChange(estado=EstadoLead.ENVIADA))
    estado_service.change_estado(
        db_session, VENDEDOR, lead.id, EstadoChange(estado=EstadoLead.VENDIDO, clasificacion=TipoClasificacion.GM)
    )

    with pytest.raises(estado_service.InvalidTransitionError):
        estado_service.change_estado(
            db_session,
            VENDEDOR,
            lead.id,
            EstadoChange(estado=EstadoLead.VENDIDO, clasificacion=TipoClasificacion.STOCK_MOBILITY),
        )


def test_solo_vendedor_asignado_o_gerencia_pueden_cambiar_estado(db_session):
    lead = _make_lead(db_session)

    with pytest.raises(estado_service.ForbiddenError):
        estado_service.change_estado(db_session, OTRO_VENDEDOR, lead.id, EstadoChange(estado=EstadoLead.ENVIADA))


def test_gerencia_puede_cambiar_estado_de_cualquier_lead(db_session):
    lead = _make_lead(db_session)
    updated = estado_service.change_estado(db_session, GERENCIA, lead.id, EstadoChange(estado=EstadoLead.ENVIADA))
    assert updated.estado == EstadoLead.ENVIADA


def test_clasificacion_es_inmutable_sin_aprobacion_de_gerencia(db_session):
    lead = _make_lead(db_session)
    estado_service.change_estado(db_session, VENDEDOR, lead.id, EstadoChange(estado=EstadoLead.ENVIADA))
    estado_service.change_estado(
        db_session, VENDEDOR, lead.id, EstadoChange(estado=EstadoLead.VENDIDO, clasificacion=TipoClasificacion.GM)
    )

    lead.estado = EstadoLead.ENVIADA
    db_session.commit()

    with pytest.raises(estado_service.ForbiddenError):
        estado_service.change_estado(
            db_session,
            VENDEDOR,
            lead.id,
            EstadoChange(estado=EstadoLead.VENDIDO, clasificacion=TipoClasificacion.STOCK_MOBILITY),
        )


def test_lead_inexistente_lanza_error(db_session):
    with pytest.raises(lead_service.LeadNotFoundError):
        estado_service.change_estado(db_session, VENDEDOR, "no-existe", EstadoChange(estado=EstadoLead.ENVIADA))
