import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
from app.database import Base, get_db
from app.domain import EstadoUsuario, LineaNegocio, Rol
from app.main import app
from app.models import User
from app.security import hash_password


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr("app.services.user_service.send_activation_email", lambda *a: None)
    monkeypatch.setattr("app.services.auth_service.send_password_reset_email", lambda *a: None)

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    session = session_factory()
    session.add(
        User(
            name="Maya Lozada",
            email="maya@grupomactral.com",
            password_hash=hash_password("Mactral2026!"),
            role=Rol.GERENCIA,
            linea_negocio=LineaNegocio.AMBAS,
            status=EstadoUsuario.ACTIVO,
        )
    )
    session.add(
        User(
            name="Andrés Pérez",
            email="andres@grupomactral.com",
            password_hash=hash_password("Mactral2026!"),
            role=Rol.TECNICO,
            linea_negocio=LineaNegocio.INDUSTRY,
            status=EstadoUsuario.ACTIVO,
        )
    )
    session.commit()
    session.close()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    engine.dispose()


def _login(client, email, password):
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_login_exitoso_devuelve_token_y_datos_de_usuario(client):
    response = client.post(
        "/auth/login", json={"email": "maya@grupomactral.com", "password": "Mactral2026!"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["role"] == "GERENCIA"
    assert body["access_token"]


def test_login_con_password_incorrecta_devuelve_401(client):
    response = client.post(
        "/auth/login", json={"email": "maya@grupomactral.com", "password": "incorrecta"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Correo o contraseña incorrectos"


def test_cinco_intentos_fallidos_bloquean_la_cuenta(client):
    for _ in range(5):
        client.post(
            "/auth/login", json={"email": "andres@grupomactral.com", "password": "incorrecta"}
        )

    response = client.post(
        "/auth/login", json={"email": "andres@grupomactral.com", "password": "Mactral2026!"}
    )
    assert response.status_code == 423
    assert "retry_after_seconds" in response.json()["detail"]


def test_endpoint_sin_token_devuelve_401(client):
    response = client.get("/users")
    assert response.status_code == 401


def test_gerencia_crea_usuario_y_tecnico_no_puede(client):
    gerencia_token = _login(client, "maya@grupomactral.com", "Mactral2026!")
    tecnico_token = _login(client, "andres@grupomactral.com", "Mactral2026!")

    ok = client.post(
        "/users",
        json={
            "name": "Carla Ruiz",
            "email": "carla@grupomactral.com",
            "role": "COMERCIAL",
            "linea_negocio": "MOBILITY",
        },
        headers=_auth_headers(gerencia_token),
    )
    assert ok.status_code == 201
    assert "activation_link" in ok.json()

    forbidden = client.post(
        "/users",
        json={
            "name": "Otro",
            "email": "otro@grupomactral.com",
            "role": "COMERCIAL",
            "linea_negocio": "MOBILITY",
        },
        headers=_auth_headers(tecnico_token),
    )
    assert forbidden.status_code == 403


def test_correo_duplicado_devuelve_409(client):
    token = _login(client, "maya@grupomactral.com", "Mactral2026!")
    payload = {
        "name": "Carla Ruiz",
        "email": "carla@grupomactral.com",
        "role": "COMERCIAL",
        "linea_negocio": "MOBILITY",
    }
    client.post("/users", json=payload, headers=_auth_headers(token))
    response = client.post("/users", json=payload, headers=_auth_headers(token))

    assert response.status_code == 409


def test_desactivar_usuario(client):
    token = _login(client, "maya@grupomactral.com", "Mactral2026!")
    created = client.post(
        "/users",
        json={
            "name": "Carla Ruiz",
            "email": "carla@grupomactral.com",
            "role": "COMERCIAL",
            "linea_negocio": "MOBILITY",
        },
        headers=_auth_headers(token),
    ).json()

    response = client.patch(
        f"/users/{created['id']}", json={"status": "INACTIVO"}, headers=_auth_headers(token)
    )
    assert response.status_code == 200
    assert response.json()["status"] == "INACTIVO"


# Escenario 3 (E1-H2): acceso a módulo no autorizado.
def test_tecnico_no_puede_acceder_al_modulo_financiero(client):
    token = _login(client, "andres@grupomactral.com", "Mactral2026!")

    response = client.get("/modules/financiero", headers=_auth_headers(token))

    assert response.status_code == 403
    assert response.json()["detail"] == "No tiene permisos para acceder a este módulo."


def test_tecnico_si_puede_acceder_al_modulo_tecnico(client):
    token = _login(client, "andres@grupomactral.com", "Mactral2026!")

    response = client.get("/modules/tecnico", headers=_auth_headers(token))

    assert response.status_code == 200


def test_gerencia_accede_a_cualquier_modulo(client):
    token = _login(client, "maya@grupomactral.com", "Mactral2026!")

    response = client.get("/modules/financiero", headers=_auth_headers(token))

    assert response.status_code == 200


def test_me_incluye_los_modulos_accesibles_del_rol(client):
    token = _login(client, "andres@grupomactral.com", "Mactral2026!")

    response = client.get("/auth/me", headers=_auth_headers(token))

    assert response.status_code == 200
    modules = set(response.json()["accessible_modules"])
    assert modules == {"tecnico", "stock", "reg-maestro"}


def test_refresh_devuelve_un_nuevo_token(client):
    token = _login(client, "maya@grupomactral.com", "Mactral2026!")

    response = client.post("/auth/refresh", headers=_auth_headers(token))

    assert response.status_code == 200
    assert response.json()["access_token"]


def test_forgot_password_y_set_password_permiten_iniciar_sesion_con_la_nueva_clave(
    client, monkeypatch
):
    captured = {}
    monkeypatch.setattr(
        "app.services.auth_service.send_password_reset_email",
        lambda email, link: captured.update(link=link),
    )

    response = client.post(
        "/auth/forgot-password", json={"email": "andres@grupomactral.com"}
    )
    assert response.status_code == 200
    token = captured["link"].split("token=")[1]

    set_password = client.post(
        "/auth/set-password", json={"token": token, "password": "NuevaClave2026!"}
    )
    assert set_password.status_code == 200

    login_response = client.post(
        "/auth/login", json={"email": "andres@grupomactral.com", "password": "NuevaClave2026!"}
    )
    assert login_response.status_code == 200


def test_forgot_password_no_revela_si_el_correo_no_existe(client):
    response = client.post("/auth/forgot-password", json={"email": "nadie@grupomactral.com"})
    assert response.status_code == 200


def test_password_debil_es_rechazada_por_la_politica(client):
    response = client.post(
        "/auth/set-password", json={"token": "cualquiera", "password": "debil"}
    )
    assert response.status_code == 422
