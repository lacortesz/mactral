from datetime import timedelta

import pytest

from app.config import settings
from app.domain import EstadoUsuario, LineaNegocio, Rol
from app.models import User
from app.security import hash_password, utcnow
from app.services import auth_service


def _make_user(db_session, **overrides) -> User:
    defaults = dict(
        name="Andrés Pérez",
        email="andres@grupomactral.com",
        password_hash=hash_password("Mactral2026!"),
        role=Rol.TECNICO,
        linea_negocio=LineaNegocio.INDUSTRY,
        status=EstadoUsuario.ACTIVO,
    )
    defaults.update(overrides)
    user = User(**defaults)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# Escenario 1 (E1-H2): login exitoso.
def test_login_exitoso_actualiza_ultimo_acceso_y_reinicia_intentos(db_session):
    _make_user(db_session, failed_login_attempts=2)

    user = auth_service.login(db_session, "andres@grupomactral.com", "Mactral2026!")

    assert user.last_access_at is not None
    assert user.failed_login_attempts == 0


# Escenario 2 (E1-H2): credenciales incorrectas.
def test_password_incorrecta_lanza_error_generico(db_session):
    _make_user(db_session)

    with pytest.raises(auth_service.InvalidCredentialsError):
        auth_service.login(db_session, "andres@grupomactral.com", "incorrecta")


def test_correo_inexistente_lanza_el_mismo_error_generico(db_session):
    with pytest.raises(auth_service.InvalidCredentialsError):
        auth_service.login(db_session, "nadie@grupomactral.com", "cualquiera")


def test_bloquea_la_cuenta_tras_el_maximo_de_intentos_fallidos(db_session):
    _make_user(db_session)

    for _ in range(settings.max_failed_login_attempts - 1):
        with pytest.raises(auth_service.InvalidCredentialsError):
            auth_service.login(db_session, "andres@grupomactral.com", "incorrecta")

    # Intento número 5: bloquea la cuenta 15 minutos.
    with pytest.raises(auth_service.InvalidCredentialsError):
        auth_service.login(db_session, "andres@grupomactral.com", "incorrecta")

    with pytest.raises(auth_service.AccountLockedError):
        auth_service.login(db_session, "andres@grupomactral.com", "Mactral2026!")


def test_cuenta_bloqueada_rechaza_incluso_la_contrasena_correcta(db_session):
    user = _make_user(db_session, locked_until=utcnow() + timedelta(minutes=15))

    with pytest.raises(auth_service.AccountLockedError) as exc_info:
        auth_service.login(db_session, user.email, "Mactral2026!")

    assert exc_info.value.retry_after_seconds > 0


def test_login_funciona_de_nuevo_cuando_el_bloqueo_expiro(db_session):
    user = _make_user(
        db_session,
        locked_until=utcnow() - timedelta(seconds=1),
        failed_login_attempts=0,
    )

    result = auth_service.login(db_session, user.email, "Mactral2026!")

    assert result.locked_until is None
    assert result.failed_login_attempts == 0


def test_rechaza_el_acceso_de_una_cuenta_inactiva(db_session):
    _make_user(db_session, status=EstadoUsuario.INACTIVO)

    with pytest.raises(auth_service.InactiveAccountError):
        auth_service.login(db_session, "andres@grupomactral.com", "Mactral2026!")


# Restricción E1-H2: recuperación de contraseña por correo.
def test_request_password_reset_genera_token_para_usuario_existente(db_session, monkeypatch):
    enviados = []
    monkeypatch.setattr(
        "app.services.auth_service.send_password_reset_email",
        lambda email, link: enviados.append((email, link)),
    )
    user = _make_user(db_session)

    auth_service.request_password_reset(db_session, user.email)

    db_session.refresh(user)
    assert user.activation_token is not None
    assert len(enviados) == 1


def test_request_password_reset_no_revela_si_el_correo_no_existe(db_session, monkeypatch):
    enviados = []
    monkeypatch.setattr(
        "app.services.auth_service.send_password_reset_email",
        lambda email, link: enviados.append((email, link)),
    )

    # No debe lanzar error ni enviar correo alguno.
    auth_service.request_password_reset(db_session, "nadie@grupomactral.com")

    assert enviados == []


def test_set_password_with_token_establece_password_y_consume_token(db_session):
    user = _make_user(
        db_session,
        password_hash=None,
        activation_token="token-valido",
        activation_token_expires_at=utcnow() + timedelta(hours=1),
    )

    updated = auth_service.set_password_with_token(db_session, "token-valido", "Mactral2026!")

    assert updated.id == user.id
    assert updated.password_hash is not None
    assert updated.activation_token is None


def test_set_password_with_token_rechaza_token_expirado(db_session):
    _make_user(
        db_session,
        activation_token="token-expirado",
        activation_token_expires_at=utcnow() - timedelta(hours=1),
    )

    with pytest.raises(auth_service.InvalidActivationTokenError):
        auth_service.set_password_with_token(db_session, "token-expirado", "Mactral2026!")


def test_set_password_with_token_rechaza_token_inexistente(db_session):
    with pytest.raises(auth_service.InvalidActivationTokenError):
        auth_service.set_password_with_token(db_session, "no-existe", "Mactral2026!")
