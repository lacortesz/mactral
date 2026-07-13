"""E9-H1: línea de tiempo del proyecto — ya implementada desde E1-H3 (ver
Project.events / ProjectEvent), aquí se formaliza con tests dedicados que
verifican que agrega eventos de distintos orígenes (Comercial, Sistema,
Financiero, Logística) en un solo timeline ordenado cronológicamente."""
from datetime import date

from app.domain import Modulo, Rol, TipoGastoLogistico
from app.schemas import (
    CuentaPorPagarCreate,
    CuotaIn,
    CuotasConfigCreate,
    ModuleStatusIn,
    ProjectCreate,
)
from app.services import financiero_service, logistica_service, project_service


class _Actor:
    def __init__(self, id: str, name: str, role: Rol):
        self.id = id
        self.name = name
        self.role = role


ADMIN = _Actor("u1", "Maya Lozada Admin", Rol.ADMINISTRATIVO)

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


def test_timeline_incluye_el_evento_de_creacion_del_proyecto(db_session):
    project = _make_project(db_session)

    detail = project_service.get_project_detail(db_session, project.crp_code, Rol.GERENCIA)

    assert len(detail.linea_de_tiempo) == 2
    assert detail.linea_de_tiempo[0].origen == "Comercial"
    assert detail.linea_de_tiempo[0].mensaje == "Venta cerrada"
    assert detail.linea_de_tiempo[1].origen == "Sistema"


def test_timeline_agrega_eventos_de_multiples_origenes_en_orden_cronologico(db_session):
    project = _make_project(db_session)

    # Financiero
    cuotas = CuotasConfigCreate(
        valor_contrato=10_000_000,
        cuotas=[CuotaIn(numero=1, etiqueta="Anticipo 1", monto=10_000_000, porcentaje=100, fecha_vencimiento=date(2026, 12, 1))],
    )
    financiero_service.configurar_cuotas(db_session, ADMIN, project.crp_code, cuotas)

    # Logística
    gasto = CuentaPorPagarCreate(
        tipo=TipoGastoLogistico.VUELO,
        proveedor="Avianca",
        concepto="Tiquetes",
        monto=500_000,
        fecha_vencimiento=date(2026, 8, 5),
    )
    logistica_service.registrar_gasto_logistico(db_session, ADMIN, project.crp_code, gasto)

    detail = project_service.get_project_detail(db_session, project.crp_code, Rol.GERENCIA)

    origenes = [e.origen for e in detail.linea_de_tiempo]
    assert origenes == ["Comercial", "Sistema", "Financiero", "Logística"]
    # El timeline debe venir ordenado cronológicamente (fecha no decreciente).
    fechas = [e.fecha for e in detail.linea_de_tiempo]
    assert fechas == sorted(fechas)


def test_timeline_es_visible_para_cualquier_rol_autorizado(db_session):
    project = _make_project(db_session)

    detail_gerencia = project_service.get_project_detail(db_session, project.crp_code, Rol.GERENCIA)
    detail_admin = project_service.get_project_detail(db_session, project.crp_code, Rol.ADMINISTRATIVO)

    assert detail_gerencia.linea_de_tiempo == detail_admin.linea_de_tiempo
