import pytest

from app.domain import EstadoLead, LineaNegocio, Rol, TipoClasificacion
from app.models import StockItem
from app.schemas import EstadoChange, LeadCreate
from app.services import estado_service, lead_service, stock_service


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


@pytest.fixture(autouse=True)
def _stub_projects_client(monkeypatch):
    # Las pruebas de estado no deben depender de una red real hacia
    # services/projects: se simula la respuesta de creación del Registro
    # Maestro con un código generado determinista.
    def _fake_create_project(token, payload):
        return {"id": "fake-project-id", "crp_code": f"{payload['crp_prefix']}26-01"}

    monkeypatch.setattr(estado_service.projects_client, "create_project", _fake_create_project)


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
    assert updated.codigo_generado == "GM26-01"
    assert len(updated.historial_estados) == 2


# Escenario 1 (E2-H4): clasificación Stock con unidades disponibles.
def test_clasificar_stock_mobility_con_unidad_disponible_la_reserva(db_session):
    lead = _make_lead(db_session)
    db_session.add(StockItem(linea_negocio=LineaNegocio.MOBILITY, tipo_producto="SSE Curva", cantidad_disponible=2))
    db_session.commit()
    estado_service.change_estado(db_session, VENDEDOR, lead.id, EstadoChange(estado=EstadoLead.ENVIADA))

    updated = estado_service.change_estado(
        db_session,
        VENDEDOR,
        lead.id,
        EstadoChange(estado=EstadoLead.VENDIDO, clasificacion=TipoClasificacion.STOCK_MOBILITY),
    )

    assert updated.codigo_generado == "STMB26-01"
    item = (
        db_session.query(StockItem)
        .filter_by(linea_negocio=LineaNegocio.MOBILITY, tipo_producto="SSE Curva")
        .one()
    )
    assert item.cantidad_disponible == 1


# Escenario 2 (E2-H4): sin unidades disponibles, bloquea el cierre.
def test_clasificar_stock_sin_unidades_disponibles_queda_bloqueado(db_session):
    lead = _make_lead(db_session)
    db_session.add(StockItem(linea_negocio=LineaNegocio.MOBILITY, tipo_producto="SSE Curva", cantidad_disponible=0))
    db_session.commit()
    estado_service.change_estado(db_session, VENDEDOR, lead.id, EstadoChange(estado=EstadoLead.ENVIADA))

    with pytest.raises(stock_service.NoStockError, match=stock_service.MENSAJE_SIN_STOCK):
        estado_service.change_estado(
            db_session,
            VENDEDOR,
            lead.id,
            EstadoChange(estado=EstadoLead.VENDIDO, clasificacion=TipoClasificacion.STOCK_MOBILITY),
        )

    # El lead no debe quedar marcado como Vendido si el cierre se bloqueó.
    refreshed = lead_service.get_lead_detail(db_session, lead.id)
    assert refreshed.estado == EstadoLead.ENVIADA
    assert refreshed.codigo_generado is None


def test_clasificar_stock_sin_registro_de_stock_queda_bloqueado(db_session):
    lead = _make_lead(db_session)
    estado_service.change_estado(db_session, VENDEDOR, lead.id, EstadoChange(estado=EstadoLead.ENVIADA))

    with pytest.raises(stock_service.NoStockError):
        estado_service.change_estado(
            db_session,
            VENDEDOR,
            lead.id,
            EstadoChange(estado=EstadoLead.VENDIDO, clasificacion=TipoClasificacion.STOCK_INDUSTRY),
        )


def test_clasificar_stock_industry_genera_codigo_stin(db_session):
    lead = _make_lead(db_session)
    db_session.add(
        StockItem(linea_negocio=LineaNegocio.INDUSTRY, tipo_producto="SSE Curva", cantidad_disponible=1)
    )
    db_session.commit()
    estado_service.change_estado(db_session, VENDEDOR, lead.id, EstadoChange(estado=EstadoLead.ENVIADA))

    updated = estado_service.change_estado(
        db_session,
        VENDEDOR,
        lead.id,
        EstadoChange(estado=EstadoLead.VENDIDO, clasificacion=TipoClasificacion.STOCK_INDUSTRY),
    )

    assert updated.codigo_generado == "STIN26-01"


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
