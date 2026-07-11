from datetime import datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
from app.config import settings
from app.database import Base, get_db
from app.domain import EstadoEtapa, Modulo, SemaforoColor
from app.main import app
from app.models import Project, ProjectEvent, ProjectModuleStatus


def _token(role: str) -> str:
    payload = {
        "sub": "u1",
        "name": "Maya Lozada",
        "email": "maya@grupomactral.com",
        "role": role,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=1),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
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
    project = Project(
        crp_code="GM26-03",
        tipo="GM - Importación",
        cliente="Clínica San Pedro",
        ciudad="Medellín",
        producto="Silla SSE Curva",
        marca="Stannah",
        etapa_actual=EstadoEtapa.EN_CURSO,
        semaforo_color=SemaforoColor.AMARILLO,
        semaforo_detalle="En fecha",
    )
    session.add(project)
    session.flush()
    session.add_all(
        [
            ProjectModuleStatus(project_id=project.id, modulo=Modulo.COMERCIAL, estado=EstadoEtapa.CERRADO),
            ProjectModuleStatus(project_id=project.id, modulo=Modulo.TECNICO, estado=EstadoEtapa.PENDIENTE),
        ]
    )
    session.add(
        ProjectEvent(
            project_id=project.id, fecha=datetime(2026, 6, 25, 9, 0), origen="Comercial", mensaje="Venta cerrada"
        )
    )
    session.commit()
    session.close()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    engine.dispose()


def test_buscar_sin_token_devuelve_401(client):
    response = client.get("/projects/search", params={"q": "GM26"})
    assert response.status_code == 401


def test_buscar_por_codigo_crp(client):
    token = _token("GERENCIA")
    response = client.get(
        "/projects/search", params={"q": "gm26"}, headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()[0]["crp_code"] == "GM26-03"


def test_buscar_sin_coincidencias_devuelve_lista_vacia(client):
    token = _token("GERENCIA")
    response = client.get(
        "/projects/search",
        params={"q": "no-existe-este-criterio"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json() == []


def test_ficha_completa_de_un_proyecto_existente(client):
    token = _token("GERENCIA")
    response = client.get("/projects/GM26-03", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["crp_code"] == "GM26-03"
    assert body["cliente"] == "Clínica San Pedro"
    assert len(body["linea_de_tiempo"]) == 1

    comercial = next(m for m in body["modulos"] if m["modulo"] == "comercial")
    assert comercial["bloqueado_por_cierre"] is True


def test_proyecto_inexistente_devuelve_404(client):
    token = _token("GERENCIA")
    response = client.get("/projects/NO-EXISTE", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 404
    assert response.json()["detail"] == "No se encontraron proyectos con ese criterio"


def test_token_invalido_devuelve_401(client):
    response = client.get(
        "/projects/GM26-03", headers={"Authorization": "Bearer token-invalido"}
    )
    assert response.status_code == 401


GM_CREATE_PAYLOAD = {
    "crp_prefix": "GM",
    "tipo": "GM - Importación",
    "cliente": "Residencias El Pinar",
    "ciudad": "Pereira",
    "producto": "SSE Recta",
    "marca": "Stannah",
    "modulos": [
        {"modulo": "comercial", "estado": "CERRADO"},
        {"modulo": "reg-maestro", "estado": "CERRADO"},
        {"modulo": "importaciones", "estado": "EN_CURSO"},
        {"modulo": "tecnico", "estado": "PENDIENTE"},
    ],
    "evento_origen": "Comercial",
    "evento_mensaje": "Venta cerrada · lead MOB26-018",
}


def test_crear_registro_maestro_devuelve_codigo_generado(client):
    token = _token("COMERCIAL")
    response = client.post("/projects", json=GM_CREATE_PAYLOAD, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 201
    body = response.json()
    assert body["crp_code"].startswith("GM")

    detail = client.get(f"/projects/{body['crp_code']}", headers={"Authorization": f"Bearer {token}"}).json()
    assert detail["cliente"] == "Residencias El Pinar"
    assert len(detail["linea_de_tiempo"]) == 2


def test_crear_registro_maestro_con_prefijo_invalido_devuelve_422(client):
    token = _token("COMERCIAL")
    payload = {**GM_CREATE_PAYLOAD, "crp_prefix": "XYZ"}
    response = client.post("/projects", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 422


def test_crear_registro_maestro_sin_token_devuelve_401(client):
    response = client.post("/projects", json=GM_CREATE_PAYLOAD)
    assert response.status_code == 401
