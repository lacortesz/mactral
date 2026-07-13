"""E9-H2: bandeja de notificaciones de asignación a módulo y alerta de
inactividad (5 días sin eventos nuevos)."""
from datetime import datetime, timedelta

from app.domain import Modulo, Rol
from app.schemas import ModuleStatusIn, ProjectCreate
from app.services import notificacion_service, project_service


class _Actor:
    def __init__(self, id: str, name: str, role: Rol):
        self.id = id
        self.name = name
        self.role = role


TECNICO = _Actor("u1", "Andrés Pérez", Rol.TECNICO)
IMPORTACIONES = _Actor("u2", "Carla Ruiz", Rol.IMPORTACIONES)

GM_PAYLOAD = ProjectCreate(
    crp_prefix="GM",
    tipo="GM - Importación",
    cliente="Clínica San Pedro",
    ciudad="Medellín",
    producto="SSE Curva",
    marca="Stannah",
    modulos=[
        ModuleStatusIn(modulo=Modulo.COMERCIAL, estado="CERRADO"),
        ModuleStatusIn(modulo=Modulo.IMPORTACIONES, estado="EN_CURSO"),
        ModuleStatusIn(modulo=Modulo.TECNICO, estado="PENDIENTE"),
    ],
    evento_origen="Comercial",
    evento_mensaje="Venta cerrada",
)


def _make_project(db_session):
    return project_service.create_project(db_session, GM_PAYLOAD)


def test_crear_proyecto_notifica_la_asignacion_a_modulos_en_curso(db_session):
    _make_project(db_session)

    notifs = notificacion_service.list_notificaciones(db_session, IMPORTACIONES)

    assert len(notifs) == 1
    assert notifs[0].modulo == Modulo.IMPORTACIONES
    assert notifs[0].tipo == notificacion_service.TIPO_ASIGNACION


def test_notificaciones_filtradas_por_modulos_accesibles_al_rol(db_session):
    _make_project(db_session)

    notifs_tecnico = notificacion_service.list_notificaciones(db_session, TECNICO)
    assert all(n.modulo != Modulo.IMPORTACIONES for n in notifs_tecnico)


def test_enviar_a_tecnico_notifica_la_asignacion(db_session):
    project = _make_project(db_session)
    for item in project.checklist_items:
        item.estado = "ARCHIVADO"
    db_session.commit()
    project_service.enviar_a_tecnico(db_session, Rol.IMPORTACIONES, project.crp_code, None)

    notifs = notificacion_service.list_notificaciones(db_session, TECNICO)
    assert any(n.modulo == Modulo.TECNICO and n.tipo == notificacion_service.TIPO_ASIGNACION for n in notifs)


def test_marcar_notificacion_como_leida(db_session):
    _make_project(db_session)
    notifs = notificacion_service.list_notificaciones(db_session, IMPORTACIONES)
    notif_id = notifs[0].id

    updated = notificacion_service.marcar_leida(db_session, IMPORTACIONES, notif_id)
    assert updated.leida is True

    notifs_no_leidas = notificacion_service.list_notificaciones(db_session, IMPORTACIONES)
    assert notif_id not in [n.id for n in notifs_no_leidas]


def test_marcar_leida_de_notificacion_inexistente_lanza_error(db_session):
    import pytest

    with pytest.raises(notificacion_service.NotificacionNotFoundError):
        notificacion_service.marcar_leida(db_session, IMPORTACIONES, "no-existe")


def test_alerta_de_inactividad_se_genera_tras_5_dias_sin_eventos(db_session):
    project = _make_project(db_session)
    # Simula que el último evento ocurrió hace más de 5 días.
    for event in project.events:
        event.fecha = datetime.utcnow() - timedelta(days=6)
    db_session.commit()

    notifs = notificacion_service.list_notificaciones(db_session, IMPORTACIONES)

    assert any(n.tipo == notificacion_service.TIPO_INACTIVIDAD for n in notifs)


def test_alerta_de_inactividad_no_se_duplica_en_lecturas_sucesivas(db_session):
    project = _make_project(db_session)
    for event in project.events:
        event.fecha = datetime.utcnow() - timedelta(days=6)
    db_session.commit()

    notificacion_service.list_notificaciones(db_session, IMPORTACIONES)
    notifs = notificacion_service.list_notificaciones(db_session, IMPORTACIONES)

    alertas_inactividad = [n for n in notifs if n.tipo == notificacion_service.TIPO_INACTIVIDAD]
    assert len(alertas_inactividad) == 1


def test_sin_inactividad_no_genera_alerta(db_session):
    _make_project(db_session)

    notifs = notificacion_service.list_notificaciones(db_session, IMPORTACIONES)

    assert all(n.tipo != notificacion_service.TIPO_INACTIVIDAD for n in notifs)
