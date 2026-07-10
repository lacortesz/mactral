from datetime import datetime

import pytest
from pydantic import ValidationError

from app.domain import EstadoLead, LineaNegocio, Rol
from app.schemas import InteractionCreate, LeadCreate
from app.services import lead_service


class _Actor:
    def __init__(self, id: str, name: str, role: Rol):
        self.id = id
        self.name = name
        self.role = role


VENDEDOR = _Actor("u1", "Carlos Martínez", Rol.COMERCIAL)
OTRO_VENDEDOR = _Actor("u2", "María Angulo", Rol.COMERCIAL)
GERENCIA = _Actor("u3", "Maya Lozada", Rol.GERENCIA)

VALID_INPUT = LeadCreate(
    nombre="Residencias El Pinar",
    telefono="3001234567",
    ciudad="Pereira",
    canal_entrada="Sitio web",
    linea_negocio=LineaNegocio.MOBILITY,
    tipo_producto="SSE Recta",
    marca="Stannah",
)


# Escenario 1 (E2-H1): registro completo.
def test_crea_lead_con_estado_cotizar_y_consecutivo(db_session):
    lead = lead_service.create_lead(db_session, VENDEDOR, VALID_INPUT)

    assert lead.estado == EstadoLead.COTIZAR
    assert lead.codigo.startswith("MOB")
    assert lead.vendedor_id == "u1"
    assert lead.vendedor_nombre == "Carlos Martínez"


def test_lead_creado_aparece_en_el_listado_con_fecha(db_session):
    lead_service.create_lead(db_session, VENDEDOR, VALID_INPUT)

    leads = lead_service.list_leads(db_session)

    assert len(leads) == 1
    assert leads[0].created_at is not None


def test_consecutivo_se_incrementa_por_linea_de_negocio(db_session):
    first = lead_service.create_lead(db_session, VENDEDOR, VALID_INPUT)
    second = lead_service.create_lead(db_session, VENDEDOR, VALID_INPUT)

    first_seq = int(first.codigo.split("-")[1])
    second_seq = int(second.codigo.split("-")[1])
    assert second_seq == first_seq + 1


def test_consecutivo_es_independiente_por_linea(db_session):
    mobility_lead = lead_service.create_lead(db_session, VENDEDOR, VALID_INPUT)
    industry_input = LeadCreate(
        nombre="Almacenes Éxito",
        telefono="6042345678",
        ciudad="Medellín",
        canal_entrada="Feria comercial",
        linea_negocio=LineaNegocio.INDUSTRY,
        tipo_producto="Montacargas",
        marca="Savaria",
    )
    industry_lead = lead_service.create_lead(db_session, VENDEDOR, industry_input)

    assert mobility_lead.codigo.startswith("MOB")
    assert industry_lead.codigo.startswith("IND")
    assert industry_lead.codigo.split("-")[1] == "001"


def test_solo_comercial_o_gerencia_pueden_crear_leads(db_session):
    otro_rol = _Actor("u9", "Andrés Pérez", Rol.TECNICO)
    with pytest.raises(lead_service.ForbiddenError):
        lead_service.create_lead(db_session, otro_rol, VALID_INPUT)


# Escenario 2 (E2-H1): campos obligatorios incompletos.
def test_falla_sin_nombre_y_sin_contacto():
    with pytest.raises(ValidationError, match="Completa los campos requeridos"):
        LeadCreate(
            nombre="",
            ciudad="Pereira",
            canal_entrada="Sitio web",
            linea_negocio=LineaNegocio.MOBILITY,
            tipo_producto="SSE Recta",
            marca="Stannah",
        )


def test_nombre_valido_pero_sin_ningun_contacto_tambien_falla():
    with pytest.raises(ValidationError, match="Completa los campos requeridos"):
        LeadCreate(
            nombre="Residencias El Pinar",
            ciudad="Pereira",
            canal_entrada="Sitio web",
            linea_negocio=LineaNegocio.MOBILITY,
            tipo_producto="SSE Recta",
            marca="Stannah",
        )


def test_acepta_solo_correo_como_contacto():
    data = LeadCreate(
        nombre="Gustavo Ramírez",
        correo="gustavo@example.com",
        ciudad="Bogotá",
        canal_entrada="Referido",
        linea_negocio=LineaNegocio.MOBILITY,
        tipo_producto="SSE Curva",
        marca="Stannah",
    )
    assert data.correo == "gustavo@example.com"


# Escenario 3 (E2-H1): registro de interacción posterior.
def test_agregar_interaccion_queda_en_historial_con_usuario(db_session):
    lead = lead_service.create_lead(db_session, VENDEDOR, VALID_INPUT)

    interaction = lead_service.add_interaction(
        db_session, VENDEDOR, lead.id, InteractionCreate(canal="Llamada", resumen="Cliente pidió cotización")
    )

    assert interaction.usuario_nombre == "Carlos Martínez"
    assert interaction.fecha is not None

    detail = lead_service.get_lead_detail(db_session, lead.id)
    assert len(detail.interacciones) == 1


def test_gerencia_puede_agregar_interaccion_a_cualquier_lead(db_session):
    lead = lead_service.create_lead(db_session, VENDEDOR, VALID_INPUT)

    interaction = lead_service.add_interaction(
        db_session, GERENCIA, lead.id, InteractionCreate(canal="Correo", resumen="Seguimiento")
    )
    assert interaction.usuario_nombre == "Maya Lozada"


def test_otro_vendedor_no_puede_agregar_interaccion(db_session):
    lead = lead_service.create_lead(db_session, VENDEDOR, VALID_INPUT)

    with pytest.raises(lead_service.ForbiddenError):
        lead_service.add_interaction(
            db_session, OTRO_VENDEDOR, lead.id, InteractionCreate(canal="Correo", resumen="Intento no autorizado")
        )


def test_agregar_interaccion_a_lead_inexistente_lanza_error(db_session):
    with pytest.raises(lead_service.LeadNotFoundError):
        lead_service.add_interaction(
            db_session, VENDEDOR, "no-existe", InteractionCreate(canal="Correo", resumen="x")
        )


def test_interaccion_sin_canal_o_resumen_falla_validacion():
    with pytest.raises(ValidationError, match="Completa los campos requeridos"):
        InteractionCreate(canal="", resumen="")


def test_get_lead_detail_lanza_error_si_no_existe(db_session):
    with pytest.raises(lead_service.LeadNotFoundError):
        lead_service.get_lead_detail(db_session, "no-existe")
