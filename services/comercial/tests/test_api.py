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
from app.main import app


def _token(role: str, sub: str = "u1", name: str = "Carlos Martínez") -> str:
    payload = {
        "sub": sub,
        "name": name,
        "email": "carlos@grupomactral.com",
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

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    engine.dispose()


VALID_PAYLOAD = {
    "nombre": "Residencias El Pinar",
    "telefono": "3001234567",
    "ciudad": "Pereira",
    "canal_entrada": "Sitio web",
    "linea_negocio": "MOBILITY",
    "tipo_producto": "SSE Recta",
    "marca": "Stannah",
}


def test_listar_sin_token_devuelve_401(client):
    response = client.get("/leads")
    assert response.status_code == 401


def test_crear_lead_exitoso(client):
    token = _token("COMERCIAL")
    response = client.post("/leads", json=VALID_PAYLOAD, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 201
    body = response.json()
    assert body["estado"] == "COTIZAR"
    assert body["codigo"].startswith("MOB")


def test_crear_lead_con_campos_incompletos_devuelve_422(client):
    token = _token("COMERCIAL")
    payload = {**VALID_PAYLOAD, "nombre": "", "telefono": None}
    response = client.post("/leads", json=payload, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 422
    assert "Completa los campos requeridos" in response.text


def test_rol_no_autorizado_no_puede_crear_lead(client):
    token = _token("TECNICO")
    response = client.post("/leads", json=VALID_PAYLOAD, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403


def test_listar_leads_incluye_el_creado(client):
    token = _token("COMERCIAL")
    client.post("/leads", json=VALID_PAYLOAD, headers={"Authorization": f"Bearer {token}"})

    response = client.get("/leads", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_agregar_interaccion_y_verla_en_detalle(client):
    token = _token("COMERCIAL")
    created = client.post(
        "/leads", json=VALID_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()

    response = client.post(
        f"/leads/{created['id']}/interactions",
        json={"canal": "Llamada", "resumen": "Primer contacto"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201

    detail = client.get(f"/leads/{created['id']}", headers={"Authorization": f"Bearer {token}"}).json()
    assert len(detail["interacciones"]) == 1
    assert detail["interacciones"][0]["canal"] == "Llamada"


def test_otro_vendedor_no_puede_agregar_interaccion(client):
    token_creador = _token("COMERCIAL", sub="u1", name="Carlos Martínez")
    token_otro = _token("COMERCIAL", sub="u2", name="María Angulo")

    created = client.post(
        "/leads", json=VALID_PAYLOAD, headers={"Authorization": f"Bearer {token_creador}"}
    ).json()

    response = client.post(
        f"/leads/{created['id']}/interactions",
        json={"canal": "Correo", "resumen": "No autorizado"},
        headers={"Authorization": f"Bearer {token_otro}"},
    )
    assert response.status_code == 403


def test_lead_inexistente_devuelve_404(client):
    token = _token("COMERCIAL")
    response = client.get("/leads/no-existe", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404


VALID_QUOTATION_PAYLOAD = {
    "valor_equipo": 45_000_000,
    "tipo_pago": "CONTADO",
    "anticipo_inicial_pct": 50,
    "segundo_anticipo_pct": 30,
    "saldo_final_pct": 20,
    "fecha_estimada_entrega": "2026-08-15",
}


def test_generar_cotizacion_devuelve_pdf_adjunto_y_cambia_estado(client):
    token = _token("COMERCIAL")
    lead = client.post(
        "/leads", json=VALID_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()

    response = client.post(
        f"/leads/{lead['id']}/quotations",
        json=VALID_QUOTATION_PAYLOAD,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["version"] == 1
    assert body["numero_cotizacion"] == f"{lead['codigo']}-v1"

    detail = client.get(f"/leads/{lead['id']}", headers={"Authorization": f"Bearer {token}"}).json()
    assert detail["estado"] == "ENVIADA"
    assert len(detail["cotizaciones"]) == 1


def test_porcentajes_que_no_suman_100_devuelve_422(client):
    token = _token("COMERCIAL")
    lead = client.post(
        "/leads", json=VALID_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()

    payload = {**VALID_QUOTATION_PAYLOAD, "saldo_final_pct": 10}
    response = client.post(
        f"/leads/{lead['id']}/quotations",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_descargar_pdf_de_la_cotizacion(client):
    token = _token("COMERCIAL")
    lead = client.post(
        "/leads", json=VALID_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()
    client.post(
        f"/leads/{lead['id']}/quotations",
        json=VALID_QUOTATION_PAYLOAD,
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.get(
        f"/leads/{lead['id']}/quotations/1/pdf", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_descargar_pdf_de_version_inexistente_devuelve_404(client):
    token = _token("COMERCIAL")
    lead = client.post(
        "/leads", json=VALID_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()

    response = client.get(
        f"/leads/{lead['id']}/quotations/1/pdf", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404


def test_regenerar_cotizacion_incrementa_version_via_api(client):
    token = _token("COMERCIAL")
    lead = client.post(
        "/leads", json=VALID_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()
    client.post(
        f"/leads/{lead['id']}/quotations",
        json=VALID_QUOTATION_PAYLOAD,
        headers={"Authorization": f"Bearer {token}"},
    )
    segunda = client.post(
        f"/leads/{lead['id']}/quotations",
        json=VALID_QUOTATION_PAYLOAD,
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    assert segunda["version"] == 2

    historial = client.get(
        f"/leads/{lead['id']}/quotations", headers={"Authorization": f"Bearer {token}"}
    ).json()
    assert len(historial) == 2


def test_otro_vendedor_no_puede_generar_cotizacion(client):
    token_creador = _token("COMERCIAL", sub="u1", name="Carlos Martínez")
    token_otro = _token("COMERCIAL", sub="u2", name="María Angulo")

    lead = client.post(
        "/leads", json=VALID_PAYLOAD, headers={"Authorization": f"Bearer {token_creador}"}
    ).json()

    response = client.post(
        f"/leads/{lead['id']}/quotations",
        json=VALID_QUOTATION_PAYLOAD,
        headers={"Authorization": f"Bearer {token_otro}"},
    )
    assert response.status_code == 403


def test_avanzar_estado_via_api_y_ver_historial(client):
    token = _token("COMERCIAL")
    lead = client.post(
        "/leads", json=VALID_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()

    response = client.patch(
        f"/leads/{lead['id']}/estado",
        json={"estado": "ENVIADA"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["estado"] == "ENVIADA"
    assert len(body["historial_estados"]) == 1
    assert body["historial_estados"][0]["estado_nuevo"] == "ENVIADA"


def test_saltar_a_vendido_devuelve_422_con_mensaje_exacto(client):
    token = _token("COMERCIAL")
    lead = client.post(
        "/leads", json=VALID_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()

    response = client.patch(
        f"/leads/{lead['id']}/estado",
        json={"estado": "VENDIDO", "clasificacion": "GM"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
    assert "Primero cambia el estado a Enviada" in response.text


def test_marcar_como_vendido_sin_clasificacion_devuelve_422(client):
    token = _token("COMERCIAL")
    lead = client.post(
        "/leads", json=VALID_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()
    client.patch(
        f"/leads/{lead['id']}/estado",
        json={"estado": "ENVIADA"},
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.patch(
        f"/leads/{lead['id']}/estado",
        json={"estado": "VENDIDO"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_marcar_como_vendido_con_clasificacion_via_api(client):
    token = _token("COMERCIAL")
    lead = client.post(
        "/leads", json=VALID_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()
    client.patch(
        f"/leads/{lead['id']}/estado",
        json={"estado": "ENVIADA"},
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.patch(
        f"/leads/{lead['id']}/estado",
        json={"estado": "VENDIDO", "clasificacion": "STOCK_INDUSTRY"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["clasificacion"] == "STOCK_INDUSTRY"


def test_otro_vendedor_no_puede_cambiar_estado(client):
    token_creador = _token("COMERCIAL", sub="u1", name="Carlos Martínez")
    token_otro = _token("COMERCIAL", sub="u2", name="María Angulo")
    lead = client.post(
        "/leads", json=VALID_PAYLOAD, headers={"Authorization": f"Bearer {token_creador}"}
    ).json()

    response = client.patch(
        f"/leads/{lead['id']}/estado",
        json={"estado": "ENVIADA"},
        headers={"Authorization": f"Bearer {token_otro}"},
    )
    assert response.status_code == 403


def test_cambiar_estado_de_lead_inexistente_devuelve_404(client):
    token = _token("COMERCIAL")
    response = client.patch(
        "/leads/no-existe/estado",
        json={"estado": "ENVIADA"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
