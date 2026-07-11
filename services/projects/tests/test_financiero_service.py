"""E7-H1: definición de cuotas y anticipos por proyecto."""
from datetime import date

import pytest
from pydantic import ValidationError

from app.domain import Modulo, Rol
from app.schemas import CuotaIn, CuotaPagoCreate, CuotasConfigCreate, ModuleStatusIn, ProjectCreate
from app.services import financiero_service, project_service


class _Actor:
    def __init__(self, id: str, name: str, role: Rol):
        self.id = id
        self.name = name
        self.role = role


ADMIN_FINANCIERO = _Actor("u1", "Maya Lozada Admin", Rol.ADMINISTRATIVO)
GERENCIA = _Actor("u2", "Maya Lozada", Rol.GERENCIA)
OTRO_ROL = _Actor("u3", "Carlos Martínez", Rol.COMERCIAL)

GM_PAYLOAD = ProjectCreate(
    crp_prefix="GM",
    tipo="GM - Importación",
    cliente="Clínica San Pedro",
    ciudad="Medellín",
    producto="SSE Curva",
    marca="Stannah",
    modulos=[ModuleStatusIn(modulo=Modulo.COMERCIAL, estado="CERRADO")],
    evento_origen="Comercial",
    evento_mensaje="Venta cerrada",
)

CUOTAS_VALIDAS = CuotasConfigCreate(
    valor_contrato=45_000_000,
    costo_fabricacion=12_500_000,
    cuotas=[
        CuotaIn(numero=1, etiqueta="Anticipo 1", monto=22_500_000, porcentaje=50, fecha_vencimiento=date(2026, 8, 1)),
        CuotaIn(numero=2, etiqueta="Anticipo 2", monto=13_500_000, porcentaje=30, fecha_vencimiento=date(2026, 8, 20)),
        CuotaIn(numero=3, etiqueta="Pago Final", monto=9_000_000, porcentaje=20, fecha_vencimiento=date(2026, 9, 1)),
    ],
)


def _make_project(db_session):
    return project_service.create_project(db_session, GM_PAYLOAD)


# Escenario 1: configuración de esquema de pagos.
def test_configurar_cuotas_exitoso(db_session):
    project = _make_project(db_session)

    updated = financiero_service.configurar_cuotas(db_session, ADMIN_FINANCIERO, project.crp_code, CUOTAS_VALIDAS)

    assert updated.valor_contrato == 45_000_000
    assert len(updated.cuotas) == 3
    assert all(c.estado.value == "PENDIENTE" for c in updated.cuotas)


def test_configurar_cuotas_queda_en_la_linea_de_tiempo(db_session):
    project = _make_project(db_session)
    financiero_service.configurar_cuotas(db_session, ADMIN_FINANCIERO, project.crp_code, CUOTAS_VALIDAS)

    detail = project_service.get_project_detail(db_session, project.crp_code, Rol.ADMINISTRATIVO)
    assert any("Esquema de pagos configurado" in e.mensaje for e in detail.linea_de_tiempo)


def test_maximo_3_cuotas():
    with pytest.raises(ValidationError, match="Máximo 3 cuotas"):
        CuotasConfigCreate(
            valor_contrato=100,
            cuotas=[
                CuotaIn(numero=1, etiqueta="A", monto=25, porcentaje=25, fecha_vencimiento=date(2026, 8, 1)),
                CuotaIn(numero=2, etiqueta="B", monto=25, porcentaje=25, fecha_vencimiento=date(2026, 8, 1)),
                CuotaIn(numero=3, etiqueta="C", monto=25, porcentaje=25, fecha_vencimiento=date(2026, 8, 1)),
                CuotaIn(numero=4, etiqueta="D", monto=25, porcentaje=25, fecha_vencimiento=date(2026, 8, 1)),
            ],
        )


def test_suma_de_cuotas_debe_igualar_el_contrato():
    with pytest.raises(ValidationError, match="igualar el valor del contrato"):
        CuotasConfigCreate(
            valor_contrato=100,
            cuotas=[CuotaIn(numero=1, etiqueta="A", monto=50, porcentaje=50, fecha_vencimiento=date(2026, 8, 1))],
        )


def test_otro_rol_no_puede_configurar_cuotas(db_session):
    project = _make_project(db_session)
    with pytest.raises(project_service.ForbiddenError):
        financiero_service.configurar_cuotas(db_session, OTRO_ROL, project.crp_code, CUOTAS_VALIDAS)


def test_no_se_pueden_reconfigurar_cuotas_ya_creadas(db_session):
    project = _make_project(db_session)
    financiero_service.configurar_cuotas(db_session, ADMIN_FINANCIERO, project.crp_code, CUOTAS_VALIDAS)

    with pytest.raises(financiero_service.CuotasYaConfiguradasError):
        financiero_service.configurar_cuotas(db_session, ADMIN_FINANCIERO, project.crp_code, CUOTAS_VALIDAS)


# Escenario 2: registro de pago recibido.
def test_registrar_pago_marca_la_cuota_como_pagada(db_session):
    project = _make_project(db_session)
    financiero_service.configurar_cuotas(db_session, ADMIN_FINANCIERO, project.crp_code, CUOTAS_VALIDAS)

    cuota = financiero_service.registrar_pago(
        db_session,
        ADMIN_FINANCIERO,
        project.crp_code,
        1,
        CuotaPagoCreate(fecha_pago=date(2026, 7, 30), monto_pagado=22_500_000, referencia_bancaria="TRF-001"),
    )

    assert cuota.estado.value == "PAGADO"
    assert cuota.monto_pagado == 22_500_000
    assert cuota.referencia_bancaria == "TRF-001"


def test_registrar_pago_de_cuota_inexistente_lanza_error(db_session):
    project = _make_project(db_session)
    financiero_service.configurar_cuotas(db_session, ADMIN_FINANCIERO, project.crp_code, CUOTAS_VALIDAS)

    with pytest.raises(financiero_service.CuotaNotFoundError):
        financiero_service.registrar_pago(
            db_session,
            ADMIN_FINANCIERO,
            project.crp_code,
            99,
            CuotaPagoCreate(fecha_pago=date(2026, 7, 30), monto_pagado=1),
        )


def test_gerencia_puede_registrar_pago(db_session):
    project = _make_project(db_session)
    financiero_service.configurar_cuotas(db_session, ADMIN_FINANCIERO, project.crp_code, CUOTAS_VALIDAS)

    cuota = financiero_service.registrar_pago(
        db_session, GERENCIA, project.crp_code, 2, CuotaPagoCreate(fecha_pago=date(2026, 8, 18), monto_pagado=13_500_000)
    )
    assert cuota.estado.value == "PAGADO"


def test_otro_rol_no_puede_registrar_pago(db_session):
    project = _make_project(db_session)
    financiero_service.configurar_cuotas(db_session, ADMIN_FINANCIERO, project.crp_code, CUOTAS_VALIDAS)

    with pytest.raises(project_service.ForbiddenError):
        financiero_service.registrar_pago(
            db_session, OTRO_ROL, project.crp_code, 1, CuotaPagoCreate(fecha_pago=date(2026, 7, 30), monto_pagado=1)
        )
