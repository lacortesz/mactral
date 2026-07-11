"""E10-H1: dashboard global de proyectos activos.
E10-H2: vista gerencial de rentabilidad por proyecto."""
from datetime import date

from app.domain import Modulo, Rol
from app.models import CuentaPorPagar
from app.schemas import CuotaIn, CuotasConfigCreate, ModuleStatusIn, ProjectCreate
from app.services import financiero_service, project_service, reportes_service


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
