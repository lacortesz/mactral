"""E4-H3: control de transición CRPL -> módulo Técnico."""
import pytest

from app.domain import EstadoEtapa, EstadoItemChecklist, Modulo, Rol
from app.schemas import ChecklistItemUpdate, EnviarTecnicoIn, ModuleStatusIn, ProjectCreate
from app.services import project_service

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
    evento_mensaje="Venta cerrada",
)

STOCK_PAYLOAD = GM_PAYLOAD.model_copy(update={"crp_prefix": "STMB", "tipo": "Stock - Mobility"})


def _archivar_todos_los_requeridos(db_session, project):
    for item in list(project.checklist_items):
        estado = (
            EstadoItemChecklist.NO_APLICA
            if item.tipo.value == "OPCIONAL"
            else EstadoItemChecklist.ARCHIVADO
        )
        data = ChecklistItemUpdate(
            estado=estado, nota="No se requiere" if estado == EstadoItemChecklist.NO_APLICA else None
        )
        project_service.update_checklist_item(db_session, Rol.IMPORTACIONES, project.crp_code, item.numero, data)


# Escenario 1: transición con checklist completo.
def test_enviar_a_tecnico_con_checklist_completo(db_session):
    project = project_service.create_project(db_session, GM_PAYLOAD)
    _archivar_todos_los_requeridos(db_session, project)

    updated = project_service.enviar_a_tecnico(db_session, Rol.IMPORTACIONES, project.crp_code)

    importaciones = next(m for m in updated.module_statuses if m.modulo == Modulo.IMPORTACIONES)
    tecnico = next(m for m in updated.module_statuses if m.modulo == Modulo.TECNICO)
    assert importaciones.estado == EstadoEtapa.CERRADO
    assert tecnico.estado == EstadoEtapa.EN_CURSO


def test_enviar_a_tecnico_con_checklist_completo_registra_evento(db_session):
    project = project_service.create_project(db_session, GM_PAYLOAD)
    _archivar_todos_los_requeridos(db_session, project)

    project_service.enviar_a_tecnico(db_session, Rol.IMPORTACIONES, project.crp_code)

    detail = project_service.get_project_detail(db_session, project.crp_code, Rol.IMPORTACIONES)
    assert any("Checklist de importación completo" in e.mensaje for e in detail.linea_de_tiempo)


# Escenario 3: bloqueado si el checklist tiene pendientes y no hay excepción.
def test_enviar_a_tecnico_bloqueado_con_pendientes_y_sin_justificacion(db_session):
    project = project_service.create_project(db_session, GM_PAYLOAD)

    with pytest.raises(project_service.TransitionBlockedError) as exc_info:
        project_service.enviar_a_tecnico(db_session, Rol.IMPORTACIONES, project.crp_code)

    assert "Detalle de Plano" in str(exc_info.value)


# Escenario 2: excepción de ingreso a bodega con checklist incompleto.
def test_enviar_a_tecnico_con_ingreso_a_bodega_y_justificacion(db_session):
    project = project_service.create_project(db_session, GM_PAYLOAD)

    updated = project_service.enviar_a_tecnico(
        db_session, Rol.IMPORTACIONES, project.crp_code, ingreso_bodega_nota="Cliente urgía la instalación"
    )

    tecnico = next(m for m in updated.module_statuses if m.modulo == Modulo.TECNICO)
    assert tecnico.estado == EstadoEtapa.EN_CURSO
    assert updated.ingreso_bodega_nota == "Cliente urgía la instalación"
    assert updated.ingreso_bodega_fecha is not None

    detail = project_service.get_project_detail(db_session, project.crp_code, Rol.IMPORTACIONES)
    assert any("Ingreso a bodega confirmado" in e.mensaje for e in detail.linea_de_tiempo)


def test_enviar_a_tecnico_con_nota_vacia_no_cuenta_como_excepcion(db_session):
    project = project_service.create_project(db_session, GM_PAYLOAD)

    with pytest.raises(project_service.TransitionBlockedError):
        project_service.enviar_a_tecnico(db_session, Rol.IMPORTACIONES, project.crp_code, ingreso_bodega_nota="   ")


# Restricción: solo aplica a proyectos GM (con checklist).
def test_enviar_a_tecnico_en_proyecto_stock_lanza_error(db_session):
    project = project_service.create_project(db_session, STOCK_PAYLOAD)

    with pytest.raises(project_service.NoChecklistError):
        project_service.enviar_a_tecnico(db_session, Rol.IMPORTACIONES, project.crp_code)


def test_otro_rol_no_puede_enviar_a_tecnico(db_session):
    project = project_service.create_project(db_session, GM_PAYLOAD)
    _archivar_todos_los_requeridos(db_session, project)

    with pytest.raises(project_service.ForbiddenError):
        project_service.enviar_a_tecnico(db_session, Rol.COMERCIAL, project.crp_code)


def test_proyecto_inexistente_lanza_error(db_session):
    with pytest.raises(project_service.ProjectNotFoundError):
        project_service.enviar_a_tecnico(db_session, Rol.IMPORTACIONES, "NO-EXISTE")
