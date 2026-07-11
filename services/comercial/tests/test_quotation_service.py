from datetime import date

import pytest
from pydantic import ValidationError

from app.domain import EstadoLead, LineaNegocio, Rol, TipoPago
from app.schemas import LeadCreate, QuotationCreate
from app.services import lead_service, quotation_service


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

VALID_QUOTATION = QuotationCreate(
    valor_equipo=45_000_000,
    tipo_pago=TipoPago.CONTADO,
    anticipo_inicial_pct=50,
    segundo_anticipo_pct=30,
    saldo_final_pct=20,
    fecha_estimada_entrega=date(2026, 8, 15),
)


def _make_lead(db_session):
    return lead_service.create_lead(db_session, VENDEDOR, LEAD_INPUT)


# Restricción E2-H2: la calculadora usa el formato oficial, no texto libre.
def test_porcentajes_deben_sumar_cien():
    with pytest.raises(ValidationError, match="deben sumar 100%"):
        QuotationCreate(
            valor_equipo=45_000_000,
            tipo_pago=TipoPago.CONTADO,
            anticipo_inicial_pct=50,
            segundo_anticipo_pct=30,
            saldo_final_pct=10,
            fecha_estimada_entrega=date(2026, 8, 15),
        )


def test_valor_equipo_debe_ser_positivo():
    with pytest.raises(ValidationError, match="mayor a cero"):
        QuotationCreate(
            valor_equipo=0,
            tipo_pago=TipoPago.CONTADO,
            anticipo_inicial_pct=50,
            segundo_anticipo_pct=30,
            saldo_final_pct=20,
            fecha_estimada_entrega=date(2026, 8, 15),
        )


# Escenario 1 (E2-H2): generación de cotización.
def test_generar_cotizacion_produce_un_pdf_no_vacio(db_session):
    lead = _make_lead(db_session)

    quotation = quotation_service.create_quotation(db_session, VENDEDOR, lead.id, VALID_QUOTATION)

    assert quotation.version == 1
    assert quotation.pdf_bytes.startswith(b"%PDF")
    assert quotation.numero_cotizacion == f"{lead.codigo}-v1"


def test_generar_cotizacion_adjunta_el_pdf_al_lead(db_session):
    lead = _make_lead(db_session)
    quotation_service.create_quotation(db_session, VENDEDOR, lead.id, VALID_QUOTATION)

    detail = lead_service.get_lead_detail(db_session, lead.id)
    assert len(detail.cotizaciones) == 1


def test_generar_cotizacion_cambia_el_estado_a_enviada(db_session):
    lead = _make_lead(db_session)
    assert lead.estado == EstadoLead.COTIZAR

    quotation_service.create_quotation(db_session, VENDEDOR, lead.id, VALID_QUOTATION)

    refreshed = lead_service.get_lead_detail(db_session, lead.id)
    assert refreshed.estado == EstadoLead.ENVIADA


# Escenario 2 (E2-H2): regeneración.
def test_regenerar_cotizacion_incrementa_la_version_y_conserva_el_historial(db_session):
    lead = _make_lead(db_session)
    quotation_service.create_quotation(db_session, VENDEDOR, lead.id, VALID_QUOTATION)

    nueva_version = QuotationCreate(
        valor_equipo=48_000_000,
        tipo_pago=TipoPago.CONTADO,
        anticipo_inicial_pct=50,
        segundo_anticipo_pct=30,
        saldo_final_pct=20,
        fecha_estimada_entrega=date(2026, 9, 1),
    )
    quotation_service.create_quotation(db_session, VENDEDOR, lead.id, nueva_version)

    historial = quotation_service.list_quotations(db_session, lead.id)
    assert [q.version for q in historial] == [1, 2]
    assert historial[0].valor_equipo == 45_000_000
    assert historial[1].valor_equipo == 48_000_000


def test_regenerar_no_retrocede_el_estado(db_session):
    lead = _make_lead(db_session)
    quotation_service.create_quotation(db_session, VENDEDOR, lead.id, VALID_QUOTATION)
    lead.estado = EstadoLead.VENDIDO
    db_session.commit()

    quotation_service.create_quotation(db_session, VENDEDOR, lead.id, VALID_QUOTATION)

    refreshed = lead_service.get_lead_detail(db_session, lead.id)
    assert refreshed.estado == EstadoLead.VENDIDO


def test_solo_vendedor_asignado_o_gerencia_pueden_generar_cotizacion(db_session):
    lead = _make_lead(db_session)

    with pytest.raises(lead_service.ForbiddenError):
        quotation_service.create_quotation(db_session, OTRO_VENDEDOR, lead.id, VALID_QUOTATION)


def test_gerencia_puede_generar_cotizacion_de_cualquier_lead(db_session):
    lead = _make_lead(db_session)
    quotation = quotation_service.create_quotation(db_session, GERENCIA, lead.id, VALID_QUOTATION)
    assert quotation.version == 1


def test_lead_inexistente_lanza_error(db_session):
    with pytest.raises(lead_service.LeadNotFoundError):
        quotation_service.create_quotation(db_session, VENDEDOR, "no-existe", VALID_QUOTATION)


def test_get_quotation_pdf_de_version_inexistente_lanza_error(db_session):
    lead = _make_lead(db_session)
    quotation_service.create_quotation(db_session, VENDEDOR, lead.id, VALID_QUOTATION)

    with pytest.raises(quotation_service.QuotationNotFoundError):
        quotation_service.get_quotation_pdf(db_session, lead.id, 99)


def test_get_quotation_pdf_de_lead_inexistente_lanza_error(db_session):
    with pytest.raises(lead_service.LeadNotFoundError):
        quotation_service.get_quotation_pdf(db_session, "no-existe", 1)


def test_list_quotations_de_lead_inexistente_lanza_error(db_session):
    with pytest.raises(lead_service.LeadNotFoundError):
        quotation_service.list_quotations(db_session, "no-existe")
