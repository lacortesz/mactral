"""E4-H2: notificación de BL/guía aérea para anticipo 2."""
from app.domain import EstadoItemChecklist, Modulo, Rol
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


# Escenario 1: archivar el ítem #8 (HAWBL/BL) dispara la notificación.
def test_archivar_bl_dispara_notificacion_de_anticipo2(db_session):
    project = project_service.create_project(db_session, GM_PAYLOAD)
    eventos_previos = len(project.events)

    project_service.update_checklist_item(
        db_session, Rol.IMPORTACIONES, project.crp_code, "8", ChecklistItemUpdate(estado=EstadoItemChecklist.ARCHIVADO)
    )

    detail = project_service.get_project_detail(db_session, project.crp_code, Rol.IMPORTACIONES)
    mensajes = [e.mensaje for e in detail.linea_de_tiempo]
    assert any("BL recibido" in m and "Anticipo 2" in m for m in mensajes)
    assert any("Correo enviado" in m for m in mensajes)
    assert len(detail.linea_de_tiempo) == eventos_previos + 2


def test_archivar_otro_item_no_dispara_la_notificacion(db_session):
    project = project_service.create_project(db_session, GM_PAYLOAD)

    project_service.update_checklist_item(
        db_session, Rol.IMPORTACIONES, project.crp_code, "4", ChecklistItemUpdate(estado=EstadoItemChecklist.ARCHIVADO)
    )

    detail = project_service.get_project_detail(db_session, project.crp_code, Rol.IMPORTACIONES)
    mensajes = [e.mensaje for e in detail.linea_de_tiempo]
    assert not any("Anticipo 2" in m for m in mensajes)


# Restricción: la notificación solo se dispara una vez por proyecto.
def test_la_notificacion_solo_se_dispara_una_vez(db_session):
    project = project_service.create_project(db_session, GM_PAYLOAD)

    project_service.update_checklist_item(
        db_session, Rol.IMPORTACIONES, project.crp_code, "8", ChecklistItemUpdate(estado=EstadoItemChecklist.ARCHIVADO)
    )
    # Reabrir y volver a archivar (p. ej. corrección de un adjunto) no debe
    # duplicar el disparo.
    project_service.update_checklist_item(
        db_session, Rol.IMPORTACIONES, project.crp_code, "8", ChecklistItemUpdate(estado=EstadoItemChecklist.PENDIENTE)
    )
    project_service.update_checklist_item(
        db_session, Rol.IMPORTACIONES, project.crp_code, "8", ChecklistItemUpdate(estado=EstadoItemChecklist.ARCHIVADO)
    )

    detail = project_service.get_project_detail(db_session, project.crp_code, Rol.IMPORTACIONES)
    mensajes = [e.mensaje for e in detail.linea_de_tiempo if "BL recibido" in e.mensaje]
    assert len(mensajes) == 1
