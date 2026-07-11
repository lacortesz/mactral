"""E8-H1: registro de programación logística (vuelo/hospedaje/transporte/
viáticos), y E8-H3: cada gasto queda imputado automáticamente al proyecto."""
from datetime import date

import pytest
from pydantic import ValidationError

from app.domain import Modulo, Rol, TipoGastoLogistico
from app.schemas import CuentaPorPagarCreate, ModuleStatusIn, ProjectCreate
from app.services import financiero_service, logistica_service, project_service


class _Actor:
    def __init__(self, id: str, name: str, role: Rol):
        self.id = id
        self.name = name
        self.role = role


ADMIN_LOGISTICA = _Actor("u1", "Maya Lozada Admin", Rol.ADMINISTRATIVO)
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


def _make_project(db_session):
    return project_service.create_project(db_session, GM_PAYLOAD)


VUELO_PAYLOAD = CuentaPorPagarCreate(
    tipo=TipoGastoLogistico.VUELO,
    proveedor="Avianca",
    concepto="Tiquetes técnico instalación",
    monto=1_500_000,
    fecha_vencimiento=date(2026, 8, 5),
)


def test_registrar_gasto_logistico_exitoso(db_session):
    project = _make_project(db_session)

    cxp = logistica_service.registrar_gasto_logistico(db_session, ADMIN_LOGISTICA, project.crp_code, VUELO_PAYLOAD)

    assert cxp.proveedor == "Avianca"
    assert cxp.tipo == TipoGastoLogistico.VUELO
    assert cxp.project_id == project.id


def test_registrar_gasto_logistico_queda_en_la_linea_de_tiempo(db_session):
    project = _make_project(db_session)
    logistica_service.registrar_gasto_logistico(db_session, ADMIN_LOGISTICA, project.crp_code, VUELO_PAYLOAD)

    detail = project_service.get_project_detail(db_session, project.crp_code, Rol.ADMINISTRATIVO)
    assert any("Gasto logístico registrado" in e.mensaje for e in detail.linea_de_tiempo)


def test_viaticos_requieren_autorizacion_gg():
    with pytest.raises(ValidationError, match="autorización obligatoria del Gerente General"):
        CuentaPorPagarCreate(
            tipo=TipoGastoLogistico.VIATICOS,
            proveedor="Juan Pérez",
            concepto="Viáticos instalación",
            monto=300_000,
            fecha_vencimiento=date(2026, 8, 5),
            autorizado_gg=False,
        )


def test_viaticos_con_autorizacion_gg_son_validos(db_session):
    project = _make_project(db_session)
    payload = CuentaPorPagarCreate(
        tipo=TipoGastoLogistico.VIATICOS,
        proveedor="Juan Pérez",
        concepto="Viáticos instalación",
        monto=300_000,
        fecha_vencimiento=date(2026, 8, 5),
        autorizado_gg=True,
    )

    cxp = logistica_service.registrar_gasto_logistico(db_session, ADMIN_LOGISTICA, project.crp_code, payload)
    assert cxp.autorizado_gg is True


def test_monto_debe_ser_mayor_a_cero():
    with pytest.raises(ValidationError, match="mayor a cero"):
        CuentaPorPagarCreate(
            tipo=TipoGastoLogistico.OTRO,
            proveedor="Proveedor X",
            concepto="Concepto",
            monto=0,
            fecha_vencimiento=date(2026, 8, 5),
        )


def test_otro_rol_no_puede_registrar_gasto_logistico(db_session):
    project = _make_project(db_session)
    with pytest.raises(project_service.ForbiddenError):
        logistica_service.registrar_gasto_logistico(db_session, OTRO_ROL, project.crp_code, VUELO_PAYLOAD)


def test_gerencia_puede_registrar_gasto_logistico(db_session):
    project = _make_project(db_session)
    cxp = logistica_service.registrar_gasto_logistico(db_session, GERENCIA, project.crp_code, VUELO_PAYLOAD)
    assert cxp.id is not None


def test_list_gastos_logisticos_de_proyecto(db_session):
    project = _make_project(db_session)
    logistica_service.registrar_gasto_logistico(db_session, ADMIN_LOGISTICA, project.crp_code, VUELO_PAYLOAD)

    gastos = logistica_service.list_gastos_logisticos(db_session, project.crp_code)
    assert len(gastos) == 1


def test_list_gastos_logisticos_de_proyecto_inexistente_lanza_error(db_session):
    with pytest.raises(project_service.ProjectNotFoundError):
        logistica_service.list_gastos_logisticos(db_session, "GM26-999")


# E8-H3: imputación automática — el gasto ya aparece en el tablero
# financiero y en el consolidado de CxP del proyecto sin código adicional.
def test_gasto_logistico_se_imputa_automaticamente_al_tablero_financiero(db_session):
    project = _make_project(db_session)
    logistica_service.registrar_gasto_logistico(db_session, ADMIN_LOGISTICA, project.crp_code, VUELO_PAYLOAD)

    tablero = financiero_service.get_tablero(db_session, project.crp_code)
    assert tablero.total_gastos_logisticos_cop == 1_500_000


def test_gasto_logistico_se_imputa_automaticamente_al_consolidado_cxp(db_session):
    project = _make_project(db_session)
    logistica_service.registrar_gasto_logistico(db_session, ADMIN_LOGISTICA, project.crp_code, VUELO_PAYLOAD)

    consolidado = financiero_service.list_cuentas_por_pagar(db_session, ADMIN_LOGISTICA, crp_code=project.crp_code)
    assert len(consolidado.items) == 1
    assert consolidado.items[0].proveedor == "Avianca"
