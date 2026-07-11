"""E5-H1: programación de fecha de instalación."""
from datetime import date

import pytest

from app.domain import Modulo, Rol
from app.schemas import InstallationCreate, InstallationReprogram, ModuleStatusIn, ProjectCreate
from app.services import installation_service, project_service


class _Actor:
    def __init__(self, id: str, name: str, role: Rol):
        self.id = id
        self.name = name
        self.role = role


COORDINADOR = _Actor("u1", "Andrés Pérez", Rol.TECNICO)
GERENCIA = _Actor("u2", "Maya Lozada", Rol.GERENCIA)
OTRO_ROL = _Actor("u3", "Carlos Martínez", Rol.COMERCIAL)

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

INSTALACION = InstallationCreate(
    fecha_instalacion=date(2026, 8, 1), tecnico_id="u1", tecnico_nombre="Andrés Pérez", ciudad="Barranquilla"
)


# Escenario 1: programación exitosa.
def test_programar_instalacion_exitosa(db_session):
    project = project_service.create_project(db_session, STOCK_PAYLOAD)

    installation = installation_service.programar_instalacion(db_session, COORDINADOR, project.crp_code, INSTALACION)

    assert installation.estado.value == "PROGRAMADO"
    assert installation.tecnico_nombre == "Andrés Pérez"
    assert installation.ciudad == "Barranquilla"


def test_programar_instalacion_aparece_en_la_ficha(db_session):
    project = project_service.create_project(db_session, STOCK_PAYLOAD)
    installation_service.programar_instalacion(db_session, COORDINADOR, project.crp_code, INSTALACION)

    detail = project_service.get_project_detail(db_session, project.crp_code, Rol.TECNICO)

    assert detail.instalacion is not None
    assert detail.instalacion.fecha_instalacion == date(2026, 8, 1)


def test_programar_instalacion_ya_existente_lanza_error(db_session):
    project = project_service.create_project(db_session, STOCK_PAYLOAD)
    installation_service.programar_instalacion(db_session, COORDINADOR, project.crp_code, INSTALACION)

    with pytest.raises(installation_service.InstallationAlreadyExistsError):
        installation_service.programar_instalacion(db_session, COORDINADOR, project.crp_code, INSTALACION)


def test_gerencia_puede_programar_instalacion(db_session):
    project = project_service.create_project(db_session, STOCK_PAYLOAD)
    installation = installation_service.programar_instalacion(db_session, GERENCIA, project.crp_code, INSTALACION)
    assert installation.estado.value == "PROGRAMADO"


def test_otro_rol_no_puede_programar_instalacion(db_session):
    project = project_service.create_project(db_session, STOCK_PAYLOAD)
    with pytest.raises(project_service.ForbiddenError):
        installation_service.programar_instalacion(db_session, OTRO_ROL, project.crp_code, INSTALACION)


# Restricción: la fecha no puede ser anterior al ingreso a bodega en CRPL.
def test_fecha_anterior_al_ingreso_a_bodega_lanza_error(db_session):
    gm_payload = ProjectCreate(
        crp_prefix="GM",
        tipo="GM - Importación",
        cliente="Clínica San Pedro",
        ciudad="Medellín",
        producto="SSE Curva",
        marca="Stannah",
        modulos=[ModuleStatusIn(modulo=Modulo.TECNICO, estado="PENDIENTE")],
        evento_origen="Comercial",
        evento_mensaje="Venta cerrada",
    )
    project = project_service.create_project(db_session, gm_payload)
    project_service.enviar_a_tecnico(db_session, Rol.IMPORTACIONES, project.crp_code, ingreso_bodega_nota="Urgente")

    fecha_pasada = InstallationCreate(
        fecha_instalacion=date(2020, 1, 1), tecnico_id="u1", tecnico_nombre="Andrés Pérez", ciudad="Bogotá"
    )
    with pytest.raises(installation_service.InvalidInstallationDateError):
        installation_service.programar_instalacion(db_session, COORDINADOR, project.crp_code, fecha_pasada)


def test_proyecto_inexistente_lanza_error(db_session):
    with pytest.raises(project_service.ProjectNotFoundError):
        installation_service.programar_instalacion(db_session, COORDINADOR, "NO-EXISTE", INSTALACION)


# Escenario 2: reprogramación.
def test_reprogramar_instalacion_actualiza_fecha_y_registra_historial(db_session):
    project = project_service.create_project(db_session, STOCK_PAYLOAD)
    installation_service.programar_instalacion(db_session, COORDINADOR, project.crp_code, INSTALACION)

    reprogramacion = InstallationReprogram(fecha_instalacion=date(2026, 8, 10), motivo="Cliente solicitó aplazar")
    installation = installation_service.reprogramar_instalacion(
        db_session, COORDINADOR, project.crp_code, reprogramacion
    )

    assert installation.fecha_instalacion == date(2026, 8, 10)
    assert len(installation.historial) == 1
    assert installation.historial[0].fecha_anterior == date(2026, 8, 1)
    assert installation.historial[0].fecha_nueva == date(2026, 8, 10)
    assert installation.historial[0].motivo == "Cliente solicitó aplazar"
    assert installation.historial[0].usuario_nombre == "Andrés Pérez"


def test_reprogramar_sin_motivo_lanza_error():
    with pytest.raises(Exception, match="motivo"):
        InstallationReprogram(fecha_instalacion=date(2026, 8, 10), motivo="   ")


def test_reprogramar_instalacion_inexistente_lanza_error(db_session):
    project = project_service.create_project(db_session, STOCK_PAYLOAD)
    reprogramacion = InstallationReprogram(fecha_instalacion=date(2026, 8, 10), motivo="Motivo")

    with pytest.raises(installation_service.InstallationNotFoundError):
        installation_service.reprogramar_instalacion(db_session, COORDINADOR, project.crp_code, reprogramacion)
