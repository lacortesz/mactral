"""E9-H3: comentarios por proyecto, con menciones @usuario."""
import re
from datetime import datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import Rol
from app.models import Comentario
from app.schemas import ComentarioCreate
from app.services.project_service import get_project_by_code

MENCION_RE = re.compile(r"@(\w+)")


class Actor(Protocol):
    id: str
    name: str
    role: Rol


def extraer_menciones(mensaje: str) -> list[str]:
    return MENCION_RE.findall(mensaje)


def list_comentarios(db: Session, crp_code: str) -> list[Comentario]:
    project = get_project_by_code(db, crp_code)
    stmt = select(Comentario).where(Comentario.project_id == project.id).order_by(Comentario.fecha)
    return list(db.execute(stmt).scalars())


def crear_comentario(db: Session, actor: Actor, crp_code: str, data: ComentarioCreate) -> Comentario:
    project = get_project_by_code(db, crp_code)
    comentario = Comentario(
        project_id=project.id,
        autor_id=actor.id,
        autor_nombre=actor.name,
        mensaje=data.mensaje.strip(),
        fecha=datetime.utcnow(),
    )
    db.add(comentario)
    db.commit()
    db.refresh(comentario)
    return comentario
