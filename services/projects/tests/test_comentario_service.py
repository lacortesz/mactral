"""E9-H3: comentarios por proyecto, con menciones @usuario."""
import pytest

from app.domain import Modulo, Rol
from app.schemas import ComentarioCreate, ModuleStatusIn, ProjectCreate
from app.services import comentario_service, project_service


class _Actor:
    def __init__(self, id: str, name: str, role: Rol):
        self.id = id
        self.name = name
        self.role = role


COMERCIAL = _Actor("u1", "Carlos Martínez", Rol.COMERCIAL)
TECNICO = _Actor("u2", "Andrés Pérez", Rol.TECNICO)

GM_PAYLOAD = ProjectCreate(
    crp_prefix="GM",
    tipo="GM - Importación",
    cliente="Clínica San Pedro",
    ciudad="Medellín",
    producto="SSE Curva",
    marca="Stannah",
    modulos=[ModuleStatusIn(modulo=Modulo.COMERCIAL, estado="CERRADO")],
    evento_origen="Comercial",
    evento_mensaje="Venta cerrada",
)


def _make_project(db_session):
    return project_service.create_project(db_session, GM_PAYLOAD)


def test_crear_comentario(db_session):
    project = _make_project(db_session)

    comentario = comentario_service.crear_comentario(
        db_session, COMERCIAL, project.crp_code, ComentarioCreate(mensaje="Cliente pide adelantar la instalación")
    )

    assert comentario.autor_nombre == "Carlos Martínez"
    assert comentario.mensaje == "Cliente pide adelantar la instalación"


def test_listar_comentarios_en_orden_cronologico(db_session):
    project = _make_project(db_session)
    comentario_service.crear_comentario(db_session, COMERCIAL, project.crp_code, ComentarioCreate(mensaje="Primero"))
    comentario_service.crear_comentario(db_session, TECNICO, project.crp_code, ComentarioCreate(mensaje="Segundo"))

    comentarios = comentario_service.list_comentarios(db_session, project.crp_code)

    assert [c.mensaje for c in comentarios] == ["Primero", "Segundo"]


def test_extraer_menciones_de_un_comentario():
    menciones = comentario_service.extraer_menciones("Hola @andres_perez y @carla, revisen esto por favor")
    assert menciones == ["andres_perez", "carla"]


def test_comentario_sin_menciones_devuelve_lista_vacia():
    assert comentario_service.extraer_menciones("Sin menciones aquí") == []


def test_comentario_vacio_lanza_error():
    with pytest.raises(ValueError, match="no puede estar vacío"):
        ComentarioCreate(mensaje="   ")


def test_crear_comentario_de_proyecto_inexistente_lanza_error(db_session):
    with pytest.raises(project_service.ProjectNotFoundError):
        comentario_service.crear_comentario(
            db_session, COMERCIAL, "GM26-999", ComentarioCreate(mensaje="Hola")
        )


def test_listar_comentarios_de_proyecto_inexistente_lanza_error(db_session):
    with pytest.raises(project_service.ProjectNotFoundError):
        comentario_service.list_comentarios(db_session, "GM26-999")
