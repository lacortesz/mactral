from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_user
from app.schemas import ComentarioCreate, ComentarioOut
from app.services import comentario_service, project_service

router = APIRouter(prefix="/projects/{crp_code}/comentarios", tags=["comentarios"])


def _to_out(comentario) -> ComentarioOut:
    return ComentarioOut(
        id=comentario.id,
        autor_nombre=comentario.autor_nombre,
        mensaje=comentario.mensaje,
        fecha=comentario.fecha,
        menciones=comentario_service.extraer_menciones(comentario.mensaje),
    )


@router.get("", response_model=list[ComentarioOut])
def list_comentarios(
    crp_code: str,
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(get_current_user),
):
    try:
        rows = comentario_service.list_comentarios(db, crp_code)
    except project_service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return [_to_out(c) for c in rows]


@router.post("", response_model=ComentarioOut, status_code=status.HTTP_201_CREATED)
def crear_comentario(
    crp_code: str,
    payload: ComentarioCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        comentario = comentario_service.crear_comentario(db, current_user, crp_code, payload)
        return _to_out(comentario)
    except project_service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
