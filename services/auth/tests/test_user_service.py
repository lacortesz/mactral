import pytest

from app.domain import LineaNegocio, Rol
from app.schemas import UserCreate
from app.services import user_service

VALID_INPUT = UserCreate(
    name="Andrés Pérez",
    email="andres@grupomactral.com",
    role=Rol.TECNICO,
    linea_negocio=LineaNegocio.INDUSTRY,
)


def test_crea_usuario_activo_y_genera_enlace_de_activacion(db_session, monkeypatch):
    enviados = []
    monkeypatch.setattr(
        "app.services.user_service.send_activation_email",
        lambda email, link: enviados.append((email, link)),
    )

    user, link = user_service.create_user(db_session, Rol.GERENCIA, VALID_INPUT)

    assert user.status.value == "ACTIVO"
    assert user.email == "andres@grupomactral.com"
    assert "/activar-cuenta?token=" in link
    assert enviados == [(user.email, link)]


def test_usuario_creado_aparece_en_el_listado(db_session, monkeypatch):
    monkeypatch.setattr("app.services.user_service.send_activation_email", lambda *a: None)

    user_service.create_user(db_session, Rol.GERENCIA, VALID_INPUT)
    users = user_service.list_users(db_session)

    assert len(users) == 1
    assert users[0].role == Rol.TECNICO
    assert users[0].linea_negocio == LineaNegocio.INDUSTRY


def test_rechaza_correo_duplicado_sin_crear_registro(db_session, monkeypatch):
    monkeypatch.setattr("app.services.user_service.send_activation_email", lambda *a: None)

    user_service.create_user(db_session, Rol.GERENCIA, VALID_INPUT)

    with pytest.raises(user_service.DuplicateEmailError):
        user_service.create_user(db_session, Rol.GERENCIA, VALID_INPUT)

    assert len(user_service.list_users(db_session)) == 1


def test_solo_gerencia_puede_crear_usuarios(db_session):
    with pytest.raises(user_service.ForbiddenError):
        user_service.create_user(db_session, Rol.TECNICO, VALID_INPUT)

    assert user_service.list_users(db_session) == []


def test_desactiva_usuario_conservando_sus_datos(db_session, monkeypatch):
    monkeypatch.setattr("app.services.user_service.send_activation_email", lambda *a: None)
    user, _ = user_service.create_user(db_session, Rol.GERENCIA, VALID_INPUT)

    updated = user_service.deactivate_user(db_session, Rol.GERENCIA, user.id)

    assert updated.status.value == "INACTIVO"
    assert updated.email == "andres@grupomactral.com"


def test_reactiva_usuario_inactivo(db_session, monkeypatch):
    monkeypatch.setattr("app.services.user_service.send_activation_email", lambda *a: None)
    user, _ = user_service.create_user(db_session, Rol.GERENCIA, VALID_INPUT)

    user_service.deactivate_user(db_session, Rol.GERENCIA, user.id)
    reactivated = user_service.activate_user(db_session, Rol.GERENCIA, user.id)

    assert reactivated.status.value == "ACTIVO"


def test_solo_gerencia_puede_desactivar(db_session, monkeypatch):
    monkeypatch.setattr("app.services.user_service.send_activation_email", lambda *a: None)
    user, _ = user_service.create_user(db_session, Rol.GERENCIA, VALID_INPUT)

    with pytest.raises(user_service.ForbiddenError):
        user_service.deactivate_user(db_session, Rol.TECNICO, user.id)


def test_lanza_error_si_el_usuario_no_existe(db_session):
    with pytest.raises(user_service.UserNotFoundError):
        user_service.deactivate_user(db_session, Rol.GERENCIA, "no-existe")
