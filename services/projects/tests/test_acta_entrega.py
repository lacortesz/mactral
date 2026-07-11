"""E5-H2: registro del acta de entrega."""
from datetime import date

import pytest

from app.domain import EstadoEtapa, Modulo, Rol
from app.schemas import ActaEntregaCreate, InstallationCreate, ModuleStatusIn, ProjectCreate
from app.services import installation_service, project_service


class _Actor:
    def __init__(self, id: str, name: str, role: Rol):
        self.id = id
        self.name = name
        self.role = role


COORDINADOR = _Actor("u1", "Andrés Pérez", Rol.TECNICO)
OTRO_ROL = _Actor("u2", "Carlos Martínez", Rol.COMERCIAL)

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


def _make_project_con_instalacion(db_session):
    project = project_service.create_project(db_session, STOCK_PAYLOAD)
    installation_service.programar_instalacion(db_session, COORDINADOR, project.crp_code, INSTALACION)
    return project


# Escenario 1: registro de acta con adjunto.
def test_registrar_acta_con_adjunto(db_session):
    project = _make_project_con_instalacion(db_session)

    installation = installation_service.registrar_acta(
        db_session,
        COORDINADOR,
        project.crp_code,
        ActaEntregaCreate(fecha_real_entrega=date(2026, 8, 1), observaciones="Instalación sin novedad"),
        acta_bytes=b"%PDF-fake-acta",
        acta_nombre="acta.pdf",
    )

    assert installation.estado.value == "COMPLETADO"
    assert installation.fecha_real_entrega == date(2026, 8, 1)
    assert installation.tiene_acta is True

    recuperado = installation_service.get_acta_attachment(db_session, project.crp_code)
    assert recuperado.acta_bytes == b"%PDF-fake-acta"


def test_registrar_acta_marca_proyecto_como_entregado_y_tecnico_cerrado(db_session):
    project = _make_project_con_instalacion(db_session)

    installation_service.registrar_acta(
        db_session, COORDINADOR, project.crp_code, ActaEntregaCreate(fecha_real_entrega=date(2026, 8, 1))
    )

    detail = project_service.get_project_detail(db_session, project.crp_code, Rol.TECNICO)
    assert detail.etapa_actual == EstadoEtapa.ENTREGADO
    tecnico = next(m for m in detail.modulos if m.modulo == Modulo.TECNICO)
    assert tecnico.estado == EstadoEtapa.CERRADO
    assert tecnico.bloqueado_por_cierre is True


def test_registrar_acta_notifica_pago_final(db_session):
    project = _make_project_con_instalacion(db_session)

    installation_service.registrar_acta(
        db_session, COORDINADOR, project.crp_code, ActaEntregaCreate(fecha_real_entrega=date(2026, 8, 1))
    )

    detail = project_service.get_project_detail(db_session, project.crp_code, Rol.TECNICO)
    mensajes = [e.mensaje for e in detail.linea_de_tiempo]
    assert any("Solicitar Pago Final" in m for m in mensajes)


# Escenario 2: registro sin adjunto no bloquea.
def test_registrar_acta_sin_adjunto_no_bloquea(db_session):
    project = _make_project_con_instalacion(db_session)

    installation = installation_service.registrar_acta(
        db_session, COORDINADOR, project.crp_code, ActaEntregaCreate(fecha_real_entrega=date(2026, 8, 1))
    )

    assert installation.estado.value == "COMPLETADO"
    assert installation.tiene_acta is False


def test_otro_rol_no_puede_registrar_acta(db_session):
    project = _make_project_con_instalacion(db_session)

    with pytest.raises(project_service.ForbiddenError):
        installation_service.registrar_acta(
            db_session, OTRO_ROL, project.crp_code, ActaEntregaCreate(fecha_real_entrega=date(2026, 8, 1))
        )


def test_registrar_acta_sin_instalacion_lanza_error(db_session):
    project = project_service.create_project(db_session, STOCK_PAYLOAD)

    with pytest.raises(installation_service.InstallationNotFoundError):
        installation_service.registrar_acta(
            db_session, COORDINADOR, project.crp_code, ActaEntregaCreate(fecha_real_entrega=date(2026, 8, 1))
        )
