"""E5-H3: semáforo de cumplimiento de entrega."""
from datetime import date, timedelta

from app.domain import Modulo, Rol, SemaforoColor
from app.schemas import ActaEntregaCreate, InstallationCreate, ModuleStatusIn, ProjectCreate
from app.services import installation_service, project_service


class _Actor:
    def __init__(self, id: str, name: str, role: Rol):
        self.id = id
        self.name = name
        self.role = role


COORDINADOR = _Actor("u1", "Andrés Pérez", Rol.TECNICO)

STOCK_PAYLOAD = ProjectCreate(
    crp_prefix="STMB",
    tipo="Stock - Mobility",
    cliente="Residencias El Pinar",
    ciudad="Pereira",
    producto="SSE Recta",
    marca="Stannah",
    modulos=[ModuleStatusIn(modulo=Modulo.TECNICO, estado="EN_CURSO")],
    evento_origen="Comercial",
    evento_mensaje="Venta cerrada",
)


def _make_project_con_instalacion(db_session, fecha_instalacion):
    project = project_service.create_project(db_session, STOCK_PAYLOAD)
    installation_service.programar_instalacion(
        db_session,
        COORDINADOR,
        project.crp_code,
        InstallationCreate(
            fecha_instalacion=fecha_instalacion, tecnico_id="u1", tecnico_nombre="Andrés Pérez", ciudad="Bogotá"
        ),
    )
    return project


# Escenario 1: entrega anticipada.
def test_entrega_anticipada_es_verde(db_session):
    project = _make_project_con_instalacion(db_session, date(2026, 8, 10))
    installation_service.registrar_acta(
        db_session, COORDINADOR, project.crp_code, ActaEntregaCreate(fecha_real_entrega=date(2026, 8, 8))
    )

    detail = project_service.get_project_detail(db_session, project.crp_code, Rol.TECNICO)
    assert detail.semaforo_color == SemaforoColor.VERDE
    assert "anticipada" in detail.semaforo_detalle
    assert "2 día" in detail.semaforo_detalle


# Escenario 2: entrega en fecha.
def test_entrega_en_fecha_es_amarillo(db_session):
    project = _make_project_con_instalacion(db_session, date(2026, 8, 10))
    installation_service.registrar_acta(
        db_session, COORDINADOR, project.crp_code, ActaEntregaCreate(fecha_real_entrega=date(2026, 8, 10))
    )

    detail = project_service.get_project_detail(db_session, project.crp_code, Rol.TECNICO)
    assert detail.semaforo_color == SemaforoColor.AMARILLO
    assert detail.semaforo_detalle == "Entrega a tiempo"


# Escenario 3: entrega tardía.
def test_entrega_tardia_es_rojo(db_session):
    project = _make_project_con_instalacion(db_session, date(2026, 8, 10))
    installation_service.registrar_acta(
        db_session, COORDINADOR, project.crp_code, ActaEntregaCreate(fecha_real_entrega=date(2026, 8, 13))
    )

    detail = project_service.get_project_detail(db_session, project.crp_code, Rol.TECNICO)
    assert detail.semaforo_color == SemaforoColor.ROJO
    assert "tardía" in detail.semaforo_detalle
    assert "3 día" in detail.semaforo_detalle


# Escenario 4: proyecto en retraso sin cierre (todavía Programado, fecha vencida).
def test_instalacion_vencida_sin_cierre_es_rojo_automatico(db_session):
    fecha_pasada = date.today() - timedelta(days=4)
    project = _make_project_con_instalacion(db_session, fecha_pasada)

    detail = project_service.get_project_detail(db_session, project.crp_code, Rol.TECNICO)

    assert detail.semaforo_color == SemaforoColor.ROJO
    assert "vencida" in detail.semaforo_detalle
    mensajes = [e.mensaje for e in detail.linea_de_tiempo]
    assert any("Alerta" in m for m in mensajes)


def test_instalacion_programada_futura_es_verde(db_session):
    fecha_futura = date.today() + timedelta(days=10)
    project = _make_project_con_instalacion(db_session, fecha_futura)

    detail = project_service.get_project_detail(db_session, project.crp_code, Rol.TECNICO)

    assert detail.semaforo_color == SemaforoColor.VERDE
    assert "en fecha" in detail.semaforo_detalle


def test_alerta_de_retraso_no_se_duplica_en_lecturas_sucesivas(db_session):
    fecha_pasada = date.today() - timedelta(days=2)
    project = _make_project_con_instalacion(db_session, fecha_pasada)

    project_service.get_project_detail(db_session, project.crp_code, Rol.TECNICO)
    detail = project_service.get_project_detail(db_session, project.crp_code, Rol.TECNICO)

    alertas = [e.mensaje for e in detail.linea_de_tiempo if "Alerta" in e.mensaje]
    assert len(alertas) == 1
