"""E4-H1: checklist documental de importación."""
import pytest
from pydantic import ValidationError

from app.domain import EstadoItemChecklist, Modulo, Rol, TipoItemChecklist
from app.schemas import ChecklistItemUpdate, ModuleStatusIn, ProjectCreate
from app.services import project_service

GM_PAYLOAD = ProjectCreate(
    crp_prefix="GM",
    tipo="GM - Importación",
    cliente="Residencias El Pinar",
    ciudad="Pereira",
    producto="SSE Recta",
    marca="Stannah",
    modulos=[ModuleStatusIn(modulo=Modulo.IMPORTACIONES, estado="EN_CURSO")],
    evento_origen="Comercial",
    evento_mensaje="Venta cerrada",
)

STOCK_PAYLOAD = GM_PAYLOAD.model_copy(update={"crp_prefix": "STMB", "tipo": "Stock - Mobility"})


# Escenario base: el checklist se crea automáticamente con el proyecto GM.
def test_crear_proyecto_gm_siembra_los_14_items_del_checklist(db_session):
    project = project_service.create_project(db_session, GM_PAYLOAD)

    assert len(project.checklist_items) == 14
    assert project.checklist_items[0].numero == "1"
    assert project.checklist_items[0].nombre == "Detalle de Plano"
    assert all(item.estado == EstadoItemChecklist.PENDIENTE for item in project.checklist_items)


# Restricción E4-H3 (aplicada aquí porque nace en la creación): los
# proyectos Stock no llevan checklist de importación.
def test_crear_proyecto_stock_no_genera_checklist(db_session):
    project = project_service.create_project(db_session, STOCK_PAYLOAD)
    assert project.checklist_items == []


# Escenario 1: marcado como Archivado con adjunto.
def test_marcar_item_como_archivado_con_adjunto(db_session):
    project = project_service.create_project(db_session, GM_PAYLOAD)

    item = project_service.update_checklist_item(
        db_session,
        Rol.IMPORTACIONES,
        project.crp_code,
        "4",
        ChecklistItemUpdate(estado=EstadoItemChecklist.ARCHIVADO),
        adjunto_bytes=b"%PDF-fake",
        adjunto_nombre="swift.pdf",
    )

    assert item.estado == EstadoItemChecklist.ARCHIVADO
    assert item.fecha is not None
    assert item.tiene_adjunto is True

    recuperado = project_service.get_checklist_attachment(db_session, project.crp_code, "4")
    assert recuperado.adjunto_bytes == b"%PDF-fake"
    assert recuperado.adjunto_nombre == "swift.pdf"


# Escenario 2: marcado como No Aplica con justificación.
def test_marcar_item_como_no_aplica_requiere_nota(db_session):
    with pytest.raises(ValidationError, match="justificación"):
        ChecklistItemUpdate(estado=EstadoItemChecklist.NO_APLICA)


def test_marcar_item_como_no_aplica_con_nota_queda_registrado(db_session):
    project = project_service.create_project(db_session, GM_PAYLOAD)

    item = project_service.update_checklist_item(
        db_session,
        Rol.IMPORTACIONES,
        project.crp_code,
        "12",
        ChecklistItemUpdate(estado=EstadoItemChecklist.NO_APLICA, nota="Envío terrestre, no aplica flete internacional"),
    )

    assert item.estado == EstadoItemChecklist.NO_APLICA
    assert item.nota == "Envío terrestre, no aplica flete internacional"


# Restricción: solo Importaciones (o Gerencia) puede cambiar el checklist.
def test_otro_rol_no_puede_cambiar_el_checklist(db_session):
    project = project_service.create_project(db_session, GM_PAYLOAD)

    with pytest.raises(project_service.ForbiddenError):
        project_service.update_checklist_item(
            db_session,
            Rol.COMERCIAL,
            project.crp_code,
            "1",
            ChecklistItemUpdate(estado=EstadoItemChecklist.ARCHIVADO),
        )


def test_gerencia_puede_cambiar_el_checklist(db_session):
    project = project_service.create_project(db_session, GM_PAYLOAD)

    item = project_service.update_checklist_item(
        db_session, Rol.GERENCIA, project.crp_code, "1", ChecklistItemUpdate(estado=EstadoItemChecklist.ARCHIVADO)
    )
    assert item.estado == EstadoItemChecklist.ARCHIVADO


def test_item_inexistente_lanza_error(db_session):
    project = project_service.create_project(db_session, GM_PAYLOAD)

    with pytest.raises(project_service.ChecklistItemNotFoundError):
        project_service.update_checklist_item(
            db_session,
            Rol.IMPORTACIONES,
            project.crp_code,
            "99",
            ChecklistItemUpdate(estado=EstadoItemChecklist.ARCHIVADO),
        )


def test_proyecto_inexistente_lanza_error(db_session):
    with pytest.raises(project_service.ProjectNotFoundError):
        project_service.update_checklist_item(
            db_session,
            Rol.IMPORTACIONES,
            "NO-EXISTE",
            "1",
            ChecklistItemUpdate(estado=EstadoItemChecklist.ARCHIVADO),
        )


# El checklist viaja en la ficha del proyecto (get_project_detail).
def test_checklist_aparece_en_la_ficha_del_proyecto(db_session):
    project = project_service.create_project(db_session, GM_PAYLOAD)
    project_service.update_checklist_item(
        db_session, Rol.IMPORTACIONES, project.crp_code, "4", ChecklistItemUpdate(estado=EstadoItemChecklist.ARCHIVADO)
    )

    detail = project_service.get_project_detail(db_session, project.crp_code, Rol.IMPORTACIONES)

    assert len(detail.checklist) == 14
    item_4 = next(i for i in detail.checklist if i.numero == "4")
    assert item_4.estado == EstadoItemChecklist.ARCHIVADO
    assert item_4.tipo == TipoItemChecklist.REQUERIDO
