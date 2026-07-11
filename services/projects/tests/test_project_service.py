from datetime import datetime

import pytest
from pydantic import ValidationError

from app.domain import EstadoEtapa, Modulo, Rol, SemaforoColor
from app.models import Project, ProjectEvent, ProjectModuleStatus
from app.schemas import ModuleStatusIn, ProjectCreate
from app.services import project_service


def _make_project(db_session) -> Project:
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
    db_session.add(project)
    db_session.flush()

    db_session.add_all(
        [
            ProjectModuleStatus(project_id=project.id, modulo=Modulo.COMERCIAL, estado=EstadoEtapa.CERRADO),
            ProjectModuleStatus(project_id=project.id, modulo=Modulo.REG_MAESTRO, estado=EstadoEtapa.CERRADO),
            ProjectModuleStatus(
                project_id=project.id, modulo=Modulo.IMPORTACIONES, estado=EstadoEtapa.EN_CURSO
            ),
            ProjectModuleStatus(project_id=project.id, modulo=Modulo.TECNICO, estado=EstadoEtapa.PENDIENTE),
        ]
    )
    db_session.add(
        ProjectEvent(
            project_id=project.id,
            fecha=datetime(2026, 6, 25, 9, 0),
            origen="Comercial",
            mensaje="Venta cerrada",
        )
    )
    db_session.commit()
    return project


# Escenario 1 (E1-H3): visualización completa de la ficha.
def test_get_project_detail_incluye_los_ocho_campos_de_la_ficha(db_session):
    _make_project(db_session)

    detail = project_service.get_project_detail(db_session, "GM26-03", Rol.GERENCIA)

    assert detail.crp_code == "GM26-03"
    assert detail.tipo == "GM - Importación"
    assert detail.cliente == "Clínica San Pedro"
    assert detail.ciudad == "Medellín"
    assert detail.producto == "Silla SSE Curva"
    assert detail.marca == "Stannah"
    assert detail.etapa_actual == EstadoEtapa.EN_CURSO
    assert detail.semaforo_color == SemaforoColor.AMARILLO


def test_get_project_detail_es_insensible_a_mayusculas_en_el_codigo(db_session):
    _make_project(db_session)

    detail = project_service.get_project_detail(db_session, "gm26-03", Rol.GERENCIA)

    assert detail.crp_code == "GM26-03"


def test_get_project_detail_incluye_la_linea_de_tiempo(db_session):
    _make_project(db_session)

    detail = project_service.get_project_detail(db_session, "GM26-03", Rol.GERENCIA)

    assert len(detail.linea_de_tiempo) == 1
    assert detail.linea_de_tiempo[0].origen == "Comercial"


# Restricción E1-H3: etapas cerradas quedan bloqueadas con ícono de candado.
def test_modulos_cerrados_quedan_bloqueados_para_cualquier_rol(db_session):
    _make_project(db_session)

    detail = project_service.get_project_detail(db_session, "GM26-03", Rol.COMERCIAL)

    comercial = next(m for m in detail.modulos if m.modulo == Modulo.COMERCIAL)
    assert comercial.bloqueado_por_cierre is True
    assert comercial.editable_por_mi_rol is False


def test_modulo_en_curso_es_editable_solo_para_el_rol_correspondiente(db_session):
    _make_project(db_session)

    detail_importaciones = project_service.get_project_detail(db_session, "GM26-03", Rol.IMPORTACIONES)
    importaciones = next(m for m in detail_importaciones.modulos if m.modulo == Modulo.IMPORTACIONES)
    assert importaciones.editable_por_mi_rol is True

    detail_tecnico = project_service.get_project_detail(db_session, "GM26-03", Rol.TECNICO)
    importaciones_para_tecnico = next(
        m for m in detail_tecnico.modulos if m.modulo == Modulo.IMPORTACIONES
    )
    assert importaciones_para_tecnico.editable_por_mi_rol is False


# Escenario 2 (E1-H3): proyecto no encontrado.
def test_get_project_detail_lanza_error_si_no_existe(db_session):
    with pytest.raises(project_service.ProjectNotFoundError):
        project_service.get_project_detail(db_session, "NO-EXISTE", Rol.GERENCIA)


# Búsqueda por CRP o cliente.
def test_search_projects_encuentra_por_codigo_crp_parcial(db_session):
    _make_project(db_session)

    results = project_service.search_projects(db_session, "gm26")

    assert len(results) == 1
    assert results[0].crp_code == "GM26-03"


def test_search_projects_encuentra_por_nombre_de_cliente(db_session):
    _make_project(db_session)

    results = project_service.search_projects(db_session, "san pedro")

    assert len(results) == 1


def test_search_projects_sin_coincidencias_devuelve_lista_vacia(db_session):
    _make_project(db_session)

    results = project_service.search_projects(db_session, "no-existe-este-criterio")

    assert results == []


GM_PAYLOAD = ProjectCreate(
    crp_prefix="GM",
    tipo="GM - Importación",
    cliente="Residencias El Pinar",
    ciudad="Pereira",
    producto="SSE Recta",
    marca="Stannah",
    modulos=[
        ModuleStatusIn(modulo=Modulo.COMERCIAL, estado=EstadoEtapa.CERRADO),
        ModuleStatusIn(modulo=Modulo.REG_MAESTRO, estado=EstadoEtapa.CERRADO),
        ModuleStatusIn(modulo=Modulo.IMPORTACIONES, estado=EstadoEtapa.EN_CURSO),
        ModuleStatusIn(modulo=Modulo.TECNICO, estado=EstadoEtapa.PENDIENTE),
    ],
    evento_origen="Comercial",
    evento_mensaje="Venta cerrada · lead MOB26-018 · $45.000.000",
)


# Escenario 1 (E2-H4): clasificación GM crea el Registro Maestro.
def test_create_project_genera_codigo_con_prefijo_y_anio(db_session):
    project = project_service.create_project(db_session, GM_PAYLOAD)

    assert project.crp_code.startswith("GM")
    assert project.crp_code.endswith("-01")
    assert len(project.module_statuses) == 4
    assert len(project.events) == 2  # "Venta cerrada" (Comercial) + "Código generado" (Sistema)


def test_create_project_incrementa_el_consecutivo_por_prefijo_y_anio(db_session):
    primero = project_service.create_project(db_session, GM_PAYLOAD)
    segundo = project_service.create_project(db_session, GM_PAYLOAD)

    assert primero.crp_code != segundo.crp_code
    assert segundo.crp_code.endswith("-02")


def test_create_project_prefijos_distintos_llevan_contadores_independientes(db_session):
    gm = project_service.create_project(db_session, GM_PAYLOAD)
    stock_payload = GM_PAYLOAD.model_copy(update={"crp_prefix": "STMB", "tipo": "Stock - Mobility"})
    stock = project_service.create_project(db_session, stock_payload)

    assert gm.crp_code.startswith("GM")
    assert stock.crp_code.startswith("STMB")
    assert stock.crp_code.endswith("-01")


def test_create_project_prefijo_invalido_lanza_error():
    with pytest.raises(ValidationError, match="Prefijo inválido"):
        ProjectCreate(**{**GM_PAYLOAD.model_dump(), "crp_prefix": "XYZ"})
