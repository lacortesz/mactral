"""E10-H1: dashboard global de proyectos activos.
E10-H2: vista gerencial de rentabilidad por proyecto.
E11-H1/E11-H2: KPIs operativos y financieros globales."""
from datetime import date

from app.domain import Modulo, Rol
from app.models import CuentaPorPagar
from app.schemas import (
    ActaEntregaCreate,
    ChecklistItemUpdate,
    CuentaPorPagarCreate,
    CuotaIn,
    CuotaPagoCreate,
    CuotasConfigCreate,
    InstallationCreate,
    ModuleStatusIn,
    ProjectCreate,
)
from app.services import financiero_service, installation_service, logistica_service, project_service, reportes_service


class _Actor:
    def __init__(self, id: str, name: str, role: Rol):
        self.id = id
        self.name = name
        self.role = role


ADMIN = _Actor("u1", "Maya Lozada Admin", Rol.ADMINISTRATIVO)


def _make_project(db_session, cliente="Clínica San Pedro"):
    payload = ProjectCreate(
        crp_prefix="GM",
        tipo="GM - Importación",
        cliente=cliente,
        ciudad="Medellín",
        producto="SSE Curva",
        marca="Stannah",
        modulos=[ModuleStatusIn(modulo=Modulo.COMERCIAL, estado="CERRADO")],
        evento_origen="Comercial",
        evento_mensaje="Venta cerrada",
    )
    return project_service.create_project(db_session, payload)


def test_dashboard_cuenta_proyectos_activos_y_por_semaforo(db_session):
    _make_project(db_session, "Cliente A")
    _make_project(db_session, "Cliente B")

    dashboard = reportes_service.get_dashboard(db_session)

    assert dashboard.total_activos == 2
    assert dashboard.total_entregados == 0
    verdes = next(s for s in dashboard.por_semaforo if s.color.value == "VERDE")
    assert verdes.cantidad == 2
    assert len(dashboard.proyectos) == 2


def test_dashboard_vacio_sin_proyectos(db_session):
    dashboard = reportes_service.get_dashboard(db_session)
    assert dashboard.total_activos == 0
    assert dashboard.proyectos == []


def test_rentabilidad_solo_incluye_proyectos_con_contrato_configurado(db_session):
    con_contrato = _make_project(db_session, "Cliente con contrato")
    _make_project(db_session, "Cliente sin contrato")

    financiero_service.configurar_cuotas(
        db_session,
        ADMIN,
        con_contrato.crp_code,
        CuotasConfigCreate(
            valor_contrato=45_000_000,
            costo_fabricacion=12_500_000,
            cuotas=[CuotaIn(numero=1, etiqueta="Anticipo", monto=45_000_000, porcentaje=100, fecha_vencimiento=date(2026, 8, 1))],
        ),
    )

    rentabilidad = reportes_service.get_rentabilidad(db_session)

    assert len(rentabilidad.proyectos) == 1
    assert rentabilidad.proyectos[0].crp_code == con_contrato.crp_code
    assert rentabilidad.proyectos[0].margen_bruto == 32_500_000
    assert round(rentabilidad.proyectos[0].margen_pct, 2) == round(32_500_000 / 45_000_000 * 100, 2)


def test_rentabilidad_incluye_gastos_logisticos_en_el_margen(db_session):
    project = _make_project(db_session)
    financiero_service.configurar_cuotas(
        db_session,
        ADMIN,
        project.crp_code,
        CuotasConfigCreate(
            valor_contrato=10_000_000,
            cuotas=[CuotaIn(numero=1, etiqueta="Anticipo", monto=10_000_000, porcentaje=100, fecha_vencimiento=date(2026, 8, 1))],
        ),
    )
    db_session.add(
        CuentaPorPagar(
            project_id=project.id,
            tipo="VUELO",
            proveedor="Avianca",
            concepto="Tiquetes",
            monto=500_000,
            fecha_vencimiento=date(2026, 8, 5),
        )
    )
    db_session.commit()

    rentabilidad = reportes_service.get_rentabilidad(db_session)

    assert rentabilidad.proyectos[0].gastos_logisticos_cop == 500_000
    assert rentabilidad.proyectos[0].margen_bruto == 10_000_000 - 0 - 500_000


def test_rentabilidad_totales_agregados(db_session):
    p1 = _make_project(db_session, "Cliente A")
    p2 = _make_project(db_session, "Cliente B")
    for p in (p1, p2):
        financiero_service.configurar_cuotas(
            db_session,
            ADMIN,
            p.crp_code,
            CuotasConfigCreate(
                valor_contrato=10_000_000,
                cuotas=[CuotaIn(numero=1, etiqueta="Anticipo", monto=10_000_000, porcentaje=100, fecha_vencimiento=date(2026, 8, 1))],
            ),
        )

    rentabilidad = reportes_service.get_rentabilidad(db_session)

    assert rentabilidad.valor_contrato_total == 20_000_000
    assert rentabilidad.margen_bruto_total == 20_000_000


# E11-H1: KPIs operativos.
TECNICO = _Actor("u2", "Andrés Pérez", Rol.TECNICO)
IMPORTACIONES = _Actor("u3", "Carla Ruiz", Rol.IMPORTACIONES)


def test_kpis_operativos_cuenta_checklist_incompleto(db_session):
    _make_project(db_session)

    kpis = reportes_service.get_kpis_operativos(db_session)

    assert kpis.proyectos_gm_con_checklist_incompleto == 1


def test_kpis_operativos_checklist_completo_no_cuenta(db_session):
    project = _make_project(db_session)
    for item in project.checklist_items:
        project_service.update_checklist_item(
            db_session, Rol.IMPORTACIONES, project.crp_code, item.numero, ChecklistItemUpdate(estado="ARCHIVADO")
        )

    kpis = reportes_service.get_kpis_operativos(db_session)

    assert kpis.proyectos_gm_con_checklist_incompleto == 0


def test_kpis_operativos_cuenta_instalaciones_programadas_y_completadas(db_session):
    p1 = _make_project(db_session, "Cliente A")
    p2 = _make_project(db_session, "Cliente B")
    installation_service.programar_instalacion(
        db_session, TECNICO, p1.crp_code, InstallationCreate(
            fecha_instalacion=date(2026, 9, 1), tecnico_id="t1", tecnico_nombre="Andrés Pérez", ciudad="Bogotá"
        )
    )
    installation_service.programar_instalacion(
        db_session, TECNICO, p2.crp_code, InstallationCreate(
            fecha_instalacion=date(2026, 9, 1), tecnico_id="t1", tecnico_nombre="Andrés Pérez", ciudad="Bogotá"
        )
    )
    installation_service.registrar_acta(
        db_session, TECNICO, p2.crp_code, ActaEntregaCreate(fecha_real_entrega=date(2026, 9, 1)), None, None
    )

    kpis = reportes_service.get_kpis_operativos(db_session)

    assert kpis.instalaciones_programadas == 1
    assert kpis.instalaciones_completadas == 1


def test_kpis_operativos_cuenta_notificaciones_pendientes(db_session):
    payload = ProjectCreate(
        crp_prefix="GM",
        tipo="GM - Importación",
        cliente="Cliente con módulo en curso",
        ciudad="Medellín",
        producto="SSE Curva",
        marca="Stannah",
        modulos=[
            ModuleStatusIn(modulo=Modulo.COMERCIAL, estado="CERRADO"),
            ModuleStatusIn(modulo=Modulo.IMPORTACIONES, estado="EN_CURSO"),
        ],
        evento_origen="Comercial",
        evento_mensaje="Venta cerrada",
    )
    project_service.create_project(db_session, payload)

    kpis = reportes_service.get_kpis_operativos(db_session)

    assert kpis.notificaciones_asignacion_pendientes >= 1


# E11-H2: KPIs financieros.
def test_kpis_financieros_totaliza_cobrado_y_por_cobrar(db_session):
    project = _make_project(db_session)
    financiero_service.configurar_cuotas(
        db_session,
        ADMIN,
        project.crp_code,
        CuotasConfigCreate(
            valor_contrato=10_000_000,
            cuotas=[
                CuotaIn(numero=1, etiqueta="Anticipo 1", monto=5_000_000, porcentaje=50, fecha_vencimiento=date(2026, 8, 1)),
                CuotaIn(numero=2, etiqueta="Pago final", monto=5_000_000, porcentaje=50, fecha_vencimiento=date(2026, 9, 1)),
            ],
        ),
    )
    financiero_service.registrar_pago(
        db_session, ADMIN, project.crp_code, 1, CuotaPagoCreate(fecha_pago=date(2026, 7, 30), monto_pagado=5_000_000)
    )

    kpis = reportes_service.get_kpis_financieros(db_session)

    assert kpis.total_cobrado_cop == 5_000_000
    assert kpis.total_por_cobrar_cop == 5_000_000
    assert kpis.valor_contrato_total == 10_000_000


def test_kpis_financieros_totaliza_gastos_logisticos_pendientes_y_pagados(db_session):
    project = _make_project(db_session)
    logistica_service.registrar_gasto_logistico(
        db_session, ADMIN, project.crp_code,
        CuentaPorPagarCreate(tipo="VUELO", proveedor="Avianca", concepto="Tiquetes", monto=500_000, fecha_vencimiento=date(2026, 8, 5)),
    )

    kpis = reportes_service.get_kpis_financieros(db_session)

    assert kpis.total_gastos_logisticos_pendientes_cop == 500_000
    assert kpis.total_gastos_logisticos_pagados_cop == 0
