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


# Escenario 2 (E3-H2): la búsqueda por nombre de cliente devuelve código,
# estado (semáforo) y etapa de cada coincidencia, no solo el identificador.
def test_buscar_por_cliente_incluye_codigo_estado_y_etapa(client):
    token = _token("GERENCIA")
    response = client.get(
        "/projects/search", params={"q": "san pedro"}, headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    body = response.json()[0]
    assert body["crp_code"] == "GM26-03"
    assert body["etapa_actual"] == "EN_CURSO"
    assert body["semaforo_color"] == "AMARILLO"


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


def test_crear_gm_siembra_checklist_visible_en_la_ficha(client):
    token = _token("COMERCIAL")
    created = client.post(
        "/projects", json=GM_CREATE_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()

    detail = client.get(
        f"/projects/{created['crp_code']}", headers={"Authorization": f"Bearer {token}"}
    ).json()
    assert len(detail["checklist"]) == 14
    assert detail["checklist"][0]["estado"] == "PENDIENTE"


def test_archivar_item_del_checklist_con_adjunto_via_api(client):
    token_creador = _token("COMERCIAL")
    token_importaciones = _token("IMPORTACIONES")
    created = client.post(
        "/projects", json=GM_CREATE_PAYLOAD, headers={"Authorization": f"Bearer {token_creador}"}
    ).json()

    response = client.patch(
        f"/projects/{created['crp_code']}/checklist/4",
        data={"estado": "ARCHIVADO"},
        files={"archivo": ("swift.pdf", b"%PDF-fake", "application/pdf")},
        headers={"Authorization": f"Bearer {token_importaciones}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["estado"] == "ARCHIVADO"
    assert body["tiene_adjunto"] is True

    download = client.get(
        f"/projects/{created['crp_code']}/checklist/4/adjunto",
        headers={"Authorization": f"Bearer {token_importaciones}"},
    )
    assert download.status_code == 200
    assert download.content == b"%PDF-fake"


def test_marcar_no_aplica_sin_nota_devuelve_422_via_api(client):
    token = _token("COMERCIAL")
    token_importaciones = _token("IMPORTACIONES")
    created = client.post(
        "/projects", json=GM_CREATE_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()

    response = client.patch(
        f"/projects/{created['crp_code']}/checklist/11",
        data={"estado": "NO_APLICA"},
        headers={"Authorization": f"Bearer {token_importaciones}"},
    )
    assert response.status_code == 422


def test_otro_rol_no_puede_cambiar_checklist_via_api(client):
    token = _token("COMERCIAL")
    created = client.post(
        "/projects", json=GM_CREATE_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()

    response = client.patch(
        f"/projects/{created['crp_code']}/checklist/1",
        data={"estado": "ARCHIVADO"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_cambiar_checklist_de_proyecto_inexistente_devuelve_404(client):
    token = _token("IMPORTACIONES")
    response = client.patch(
        "/projects/NO-EXISTE/checklist/1",
        data={"estado": "ARCHIVADO"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


def test_cambiar_item_inexistente_devuelve_404(client):
    token = _token("COMERCIAL")
    token_importaciones = _token("IMPORTACIONES")
    created = client.post(
        "/projects", json=GM_CREATE_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()

    response = client.patch(
        f"/projects/{created['crp_code']}/checklist/99",
        data={"estado": "ARCHIVADO"},
        headers={"Authorization": f"Bearer {token_importaciones}"},
    )
    assert response.status_code == 404


def test_descargar_adjunto_de_proyecto_inexistente_devuelve_404(client):
    token = _token("IMPORTACIONES")
    response = client.get(
        "/projects/NO-EXISTE/checklist/1/adjunto", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404


def test_descargar_adjunto_inexistente_devuelve_404(client):
    token = _token("COMERCIAL")
    created = client.post(
        "/projects", json=GM_CREATE_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()

    response = client.get(
        f"/projects/{created['crp_code']}/checklist/1/adjunto", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "El ítem no tiene un adjunto"


def test_enviar_a_tecnico_bloqueado_por_checklist_incompleto_via_api(client):
    token = _token("COMERCIAL")
    token_importaciones = _token("IMPORTACIONES")
    created = client.post(
        "/projects", json=GM_CREATE_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()

    response = client.post(
        f"/projects/{created['crp_code']}/enviar-tecnico",
        json={},
        headers={"Authorization": f"Bearer {token_importaciones}"},
    )
    assert response.status_code == 422


def test_enviar_a_tecnico_con_ingreso_a_bodega_via_api(client):
    token = _token("COMERCIAL")
    token_importaciones = _token("IMPORTACIONES")
    created = client.post(
        "/projects", json=GM_CREATE_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()

    response = client.post(
        f"/projects/{created['crp_code']}/enviar-tecnico",
        json={"ingreso_bodega_nota": "Cliente urgía la instalación"},
        headers={"Authorization": f"Bearer {token_importaciones}"},
    )
    assert response.status_code == 200
    body = response.json()
    tecnico = next(m for m in body["modulos"] if m["modulo"] == "tecnico")
    assert tecnico["estado"] == "EN_CURSO"


STOCK_CREATE_PAYLOAD = {
    "crp_prefix": "STMB",
    "tipo": "Stock - Mobility",
    "cliente": "Residencias El Pinar",
    "ciudad": "Pereira",
    "producto": "SSE Recta",
    "marca": "Stannah",
    "modulos": [{"modulo": "tecnico", "estado": "EN_CURSO"}],
    "evento_origen": "Comercial",
    "evento_mensaje": "Venta cerrada",
}


def test_programar_instalacion_via_api(client):
    token = _token("COMERCIAL")
    token_tecnico = _token("TECNICO")
    created = client.post(
        "/projects", json=STOCK_CREATE_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()

    response = client.post(
        f"/projects/{created['crp_code']}/instalacion",
        json={
            "fecha_instalacion": "2026-08-01",
            "tecnico_id": "u1",
            "tecnico_nombre": "Andrés Pérez",
            "ciudad": "Barranquilla",
        },
        headers={"Authorization": f"Bearer {token_tecnico}"},
    )
    assert response.status_code == 201
    assert response.json()["estado"] == "PROGRAMADO"


def test_reprogramar_instalacion_via_api(client):
    token = _token("COMERCIAL")
    token_tecnico = _token("TECNICO")
    created = client.post(
        "/projects", json=STOCK_CREATE_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()
    client.post(
        f"/projects/{created['crp_code']}/instalacion",
        json={
            "fecha_instalacion": "2026-08-01",
            "tecnico_id": "u1",
            "tecnico_nombre": "Andrés Pérez",
            "ciudad": "Barranquilla",
        },
        headers={"Authorization": f"Bearer {token_tecnico}"},
    )

    response = client.patch(
        f"/projects/{created['crp_code']}/instalacion",
        json={"fecha_instalacion": "2026-08-15", "motivo": "Cliente solicitó aplazar"},
        headers={"Authorization": f"Bearer {token_tecnico}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["fecha_instalacion"] == "2026-08-15"
    assert len(body["historial"]) == 1


def test_programar_instalacion_duplicada_devuelve_409(client):
    token = _token("COMERCIAL")
    token_tecnico = _token("TECNICO")
    created = client.post(
        "/projects", json=STOCK_CREATE_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()
    payload = {
        "fecha_instalacion": "2026-08-01",
        "tecnico_id": "u1",
        "tecnico_nombre": "Andrés Pérez",
        "ciudad": "Barranquilla",
    }
    client.post(
        f"/projects/{created['crp_code']}/instalacion", json=payload, headers={"Authorization": f"Bearer {token_tecnico}"}
    )
    response = client.post(
        f"/projects/{created['crp_code']}/instalacion", json=payload, headers={"Authorization": f"Bearer {token_tecnico}"}
    )
    assert response.status_code == 409


def test_otro_rol_no_puede_programar_instalacion_via_api(client):
    token = _token("COMERCIAL")
    created = client.post(
        "/projects", json=STOCK_CREATE_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()

    response = client.post(
        f"/projects/{created['crp_code']}/instalacion",
        json={
            "fecha_instalacion": "2026-08-01",
            "tecnico_id": "u1",
            "tecnico_nombre": "Andrés Pérez",
            "ciudad": "Barranquilla",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_registrar_acta_con_adjunto_via_api(client):
    token = _token("COMERCIAL")
    token_tecnico = _token("TECNICO")
    created = client.post(
        "/projects", json=STOCK_CREATE_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()
    client.post(
        f"/projects/{created['crp_code']}/instalacion",
        json={
            "fecha_instalacion": "2026-08-01",
            "tecnico_id": "u1",
            "tecnico_nombre": "Andrés Pérez",
            "ciudad": "Barranquilla",
        },
        headers={"Authorization": f"Bearer {token_tecnico}"},
    )

    response = client.patch(
        f"/projects/{created['crp_code']}/instalacion/acta",
        data={"fecha_real_entrega": "2026-08-01", "observaciones": "Sin novedad"},
        files={"acta": ("acta.pdf", b"%PDF-fake-acta", "application/pdf")},
        headers={"Authorization": f"Bearer {token_tecnico}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["estado"] == "COMPLETADO"
    assert body["tiene_acta"] is True

    detail = client.get(
        f"/projects/{created['crp_code']}", headers={"Authorization": f"Bearer {token_tecnico}"}
    ).json()
    assert detail["etapa_actual"] == "ENTREGADO"

    download = client.get(
        f"/projects/{created['crp_code']}/instalacion/acta", headers={"Authorization": f"Bearer {token_tecnico}"}
    )
    assert download.status_code == 200
    assert download.content == b"%PDF-fake-acta"


def test_registrar_acta_sin_adjunto_no_bloquea_via_api(client):
    token = _token("COMERCIAL")
    token_tecnico = _token("TECNICO")
    created = client.post(
        "/projects", json=STOCK_CREATE_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()
    client.post(
        f"/projects/{created['crp_code']}/instalacion",
        json={
            "fecha_instalacion": "2026-08-01",
            "tecnico_id": "u1",
            "tecnico_nombre": "Andrés Pérez",
            "ciudad": "Barranquilla",
        },
        headers={"Authorization": f"Bearer {token_tecnico}"},
    )

    response = client.patch(
        f"/projects/{created['crp_code']}/instalacion/acta",
        data={"fecha_real_entrega": "2026-08-01"},
        headers={"Authorization": f"Bearer {token_tecnico}"},
    )
    assert response.status_code == 200
    assert response.json()["tiene_acta"] is False


def test_descargar_acta_inexistente_devuelve_404(client):
    token = _token("COMERCIAL")
    token_tecnico = _token("TECNICO")
    created = client.post(
        "/projects", json=STOCK_CREATE_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()
    client.post(
        f"/projects/{created['crp_code']}/instalacion",
        json={
            "fecha_instalacion": "2026-08-01",
            "tecnico_id": "u1",
            "tecnico_nombre": "Andrés Pérez",
            "ciudad": "Barranquilla",
        },
        headers={"Authorization": f"Bearer {token_tecnico}"},
    )

    response = client.get(
        f"/projects/{created['crp_code']}/instalacion/acta", headers={"Authorization": f"Bearer {token_tecnico}"}
    )
    assert response.status_code == 404


CUOTAS_CONFIG_PAYLOAD = {
    "valor_contrato": 45_000_000,
    "costo_fabricacion": 12_500_000,
    "cuotas": [
        {"numero": 1, "etiqueta": "Anticipo 1", "monto": 22_500_000, "porcentaje": 50, "fecha_vencimiento": "2026-08-01"},
        {"numero": 2, "etiqueta": "Anticipo 2", "monto": 13_500_000, "porcentaje": 30, "fecha_vencimiento": "2026-08-20"},
        {"numero": 3, "etiqueta": "Pago Final", "monto": 9_000_000, "porcentaje": 20, "fecha_vencimiento": "2026-09-01"},
    ],
}


def test_configurar_cuotas_via_api(client):
    token = _token("COMERCIAL")
    token_admin = _token("ADMINISTRATIVO")
    created = client.post(
        "/projects", json=GM_CREATE_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()

    response = client.post(
        f"/projects/{created['crp_code']}/cuotas",
        json=CUOTAS_CONFIG_PAYLOAD,
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert len(body) == 3
    assert body[0]["estado"] == "PENDIENTE"


def test_listar_cuotas_vacio_antes_de_configurar(client):
    token = _token("COMERCIAL")
    created = client.post(
        "/projects", json=GM_CREATE_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()

    response = client.get(f"/projects/{created['crp_code']}/cuotas", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == []


def test_listar_cuotas_de_proyecto_inexistente_devuelve_404(client):
    token = _token("COMERCIAL")
    response = client.get("/projects/NO-EXISTE/cuotas", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404


def test_registrar_pago_de_cuota_via_api(client):
    token = _token("COMERCIAL")
    token_admin = _token("ADMINISTRATIVO")
    created = client.post(
        "/projects", json=GM_CREATE_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()
    client.post(
        f"/projects/{created['crp_code']}/cuotas",
        json=CUOTAS_CONFIG_PAYLOAD,
        headers={"Authorization": f"Bearer {token_admin}"},
    )

    response = client.patch(
        f"/projects/{created['crp_code']}/cuotas/1/pago",
        json={"fecha_pago": "2026-07-30", "monto_pagado": 22_500_000, "referencia_bancaria": "TRF-001"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert response.json()["estado"] == "PAGADO"


def test_configurar_cuotas_suma_incorrecta_devuelve_422(client):
    token = _token("COMERCIAL")
    token_admin = _token("ADMINISTRATIVO")
    created = client.post(
        "/projects", json=GM_CREATE_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()

    payload = {**CUOTAS_CONFIG_PAYLOAD, "valor_contrato": 1}
    response = client.post(
        f"/projects/{created['crp_code']}/cuotas",
        json=payload,
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 422


def test_otro_rol_no_puede_configurar_cuotas_via_api(client):
    token = _token("COMERCIAL")
    created = client.post(
        "/projects", json=GM_CREATE_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()

    response = client.post(
        f"/projects/{created['crp_code']}/cuotas",
        json=CUOTAS_CONFIG_PAYLOAD,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_tablero_financiero_via_api(client):
    token = _token("COMERCIAL")
    token_admin = _token("ADMINISTRATIVO")
    created = client.post(
        "/projects", json=GM_CREATE_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()
    client.post(
        f"/projects/{created['crp_code']}/cuotas",
        json=CUOTAS_CONFIG_PAYLOAD,
        headers={"Authorization": f"Bearer {token_admin}"},
    )

    response = client.get(
        f"/projects/{created['crp_code']}/tablero-financiero", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["valor_contrato"] == 45_000_000
    assert body["total_por_cobrar"] == 45_000_000
    assert len(body["tasas_cambio"]) == 4


def test_tablero_financiero_de_proyecto_inexistente_devuelve_404_via_api(client):
    token = _token("COMERCIAL")
    response = client.get("/projects/NO-EXISTE/tablero-financiero", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404


def test_cuentas_por_pagar_consolidado_via_api(client):
    token_admin = _token("ADMINISTRATIVO")
    response = client.get("/cuentas-por-pagar", headers={"Authorization": f"Bearer {token_admin}"})
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total_pendiente_cop"] == 0


def test_cuentas_por_pagar_consolidado_otro_rol_devuelve_403(client):
    token = _token("COMERCIAL")
    response = client.get("/cuentas-por-pagar", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_confirmar_solicitud_anticipo1_via_api(client):
    token = _token("IMPORTACIONES")
    token_admin = _token("ADMINISTRATIVO")
    created = client.post(
        "/projects", json=GM_CREATE_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()
    crp = created["crp_code"]

    for numero in ("1", "2"):
        client.patch(
            f"/projects/{crp}/checklist/{numero}",
            data={"estado": "ARCHIVADO"},
            headers={"Authorization": f"Bearer {token}"},
        )

    response = client.post(
        f"/projects/{crp}/anticipo1/confirmar-solicitud", headers={"Authorization": f"Bearer {token_admin}"}
    )
    assert response.status_code == 200
    assert response.json()["anticipo1_solicitud_confirmada"] is True


def test_confirmar_solicitud_anticipo1_sin_planos_aprobados_devuelve_422(client):
    token = _token("COMERCIAL")
    token_admin = _token("ADMINISTRATIVO")
    created = client.post(
        "/projects", json=GM_CREATE_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()

    response = client.post(
        f"/projects/{created['crp_code']}/anticipo1/confirmar-solicitud",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 422


GASTO_LOGISTICO_PAYLOAD = {
    "tipo": "VUELO",
    "proveedor": "Avianca",
    "concepto": "Tiquetes técnico instalación",
    "monto": 1_500_000,
    "fecha_vencimiento": "2026-08-05",
}


def test_registrar_gasto_logistico_via_api(client):
    token = _token("COMERCIAL")
    token_admin = _token("ADMINISTRATIVO")
    created = client.post(
        "/projects", json=GM_CREATE_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()

    response = client.post(
        f"/projects/{created['crp_code']}/logistica",
        json=GASTO_LOGISTICO_PAYLOAD,
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["proveedor"] == "Avianca"
    assert body["crp_code"] == created["crp_code"]


def test_listar_gastos_logisticos_via_api(client):
    token = _token("COMERCIAL")
    token_admin = _token("ADMINISTRATIVO")
    created = client.post(
        "/projects", json=GM_CREATE_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()
    client.post(
        f"/projects/{created['crp_code']}/logistica",
        json=GASTO_LOGISTICO_PAYLOAD,
        headers={"Authorization": f"Bearer {token_admin}"},
    )

    response = client.get(
        f"/projects/{created['crp_code']}/logistica", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_registrar_gasto_logistico_otro_rol_devuelve_403(client):
    token = _token("COMERCIAL")
    created = client.post(
        "/projects", json=GM_CREATE_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()

    response = client.post(
        f"/projects/{created['crp_code']}/logistica",
        json=GASTO_LOGISTICO_PAYLOAD,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_registrar_viaticos_sin_autorizacion_devuelve_422(client):
    token = _token("COMERCIAL")
    token_admin = _token("ADMINISTRATIVO")
    created = client.post(
        "/projects", json=GM_CREATE_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()

    payload = {**GASTO_LOGISTICO_PAYLOAD, "tipo": "VIATICOS", "autorizado_gg": False}
    response = client.post(
        f"/projects/{created['crp_code']}/logistica",
        json=payload,
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 422


def test_listar_gastos_logisticos_de_proyecto_inexistente_devuelve_404(client):
    token = _token("COMERCIAL")
    response = client.get("/projects/NO-EXISTE/logistica", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404


def test_adjuntar_soporte_a_gasto_logistico_via_api(client):
    token = _token("COMERCIAL")
    token_admin = _token("ADMINISTRATIVO")
    created = client.post(
        "/projects", json=GM_CREATE_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()
    gasto = client.post(
        f"/projects/{created['crp_code']}/logistica",
        json=GASTO_LOGISTICO_PAYLOAD,
        headers={"Authorization": f"Bearer {token_admin}"},
    ).json()

    response = client.patch(
        f"/projects/{created['crp_code']}/logistica/{gasto['id']}/soporte",
        files={"soporte": ("factura.pdf", b"%PDF-fake-factura", "application/pdf")},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert response.json()["tiene_soporte"] is True

    download = client.get(
        f"/projects/{created['crp_code']}/logistica/{gasto['id']}/soporte",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert download.status_code == 200
    assert download.content == b"%PDF-fake-factura"


def test_descargar_soporte_inexistente_devuelve_404(client):
    token = _token("COMERCIAL")
    token_admin = _token("ADMINISTRATIVO")
    created = client.post(
        "/projects", json=GM_CREATE_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()
    gasto = client.post(
        f"/projects/{created['crp_code']}/logistica",
        json=GASTO_LOGISTICO_PAYLOAD,
        headers={"Authorization": f"Bearer {token_admin}"},
    ).json()

    response = client.get(
        f"/projects/{created['crp_code']}/logistica/{gasto['id']}/soporte",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


def test_notificaciones_via_api(client):
    token = _token("COMERCIAL")
    token_importaciones = _token("IMPORTACIONES")
    client.post("/projects", json=GM_CREATE_PAYLOAD, headers={"Authorization": f"Bearer {token}"})

    response = client.get("/notificaciones", headers={"Authorization": f"Bearer {token_importaciones}"})
    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 1

    notif_id = body[0]["id"]
    marcada = client.patch(
        f"/notificaciones/{notif_id}/leer", headers={"Authorization": f"Bearer {token_importaciones}"}
    )
    assert marcada.status_code == 200
    assert marcada.json()["leida"] is True


def test_marcar_notificacion_inexistente_devuelve_404_via_api(client):
    token = _token("IMPORTACIONES")
    response = client.patch("/notificaciones/no-existe/leer", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404


def test_crear_y_listar_comentarios_via_api(client):
    token = _token("COMERCIAL")
    created = client.post(
        "/projects", json=GM_CREATE_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()

    response = client.post(
        f"/projects/{created['crp_code']}/comentarios",
        json={"mensaje": "Revisar con @importaciones antes del viernes"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["autor_nombre"] == "Maya Lozada"
    assert body["menciones"] == ["importaciones"]

    listado = client.get(
        f"/projects/{created['crp_code']}/comentarios", headers={"Authorization": f"Bearer {token}"}
    )
    assert listado.status_code == 200
    assert len(listado.json()) == 1


def test_crear_comentario_vacio_devuelve_422(client):
    token = _token("COMERCIAL")
    created = client.post(
        "/projects", json=GM_CREATE_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    ).json()

    response = client.post(
        f"/projects/{created['crp_code']}/comentarios",
        json={"mensaje": "   "},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_listar_comentarios_de_proyecto_inexistente_devuelve_404(client):
    token = _token("COMERCIAL")
    response = client.get("/projects/NO-EXISTE/comentarios", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404


def test_dashboard_global_via_api(client):
    token = _token("COMERCIAL")
    response = client.get("/reportes/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["total_activos"] >= 1
    assert len(body["por_semaforo"]) == 3


def test_rentabilidad_solo_gerencia_via_api(client):
    token = _token("GERENCIA")
    response = client.get("/reportes/rentabilidad", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_rentabilidad_otro_rol_devuelve_403_via_api(client):
    token = _token("ADMINISTRATIVO")
    response = client.get("/reportes/rentabilidad", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
