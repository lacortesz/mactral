from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_user
from app.schemas import ProjectCreate, ProjectCreateOut, ProjectDetailOut, ProjectSearchResult
from app.services import project_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/search", response_model=list[ProjectSearchResult])
def search(
    q: str = Query(min_length=1),
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(get_current_user),
):
    return project_service.search_projects(db, q)


@router.post("", response_model=ProjectCreateOut, status_code=status.HTTP_201_CREATED)
def create(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    # E2-H4: el actor conceptual es "Sistema", pero técnicamente quien llama
    # es el servicio comercial reenviando el JWT del vendedor que cerró la
    # venta; cualquier usuario autenticado puede activar el Registro Maestro.
    _current_user: CurrentUser = Depends(get_current_user),
):
    return project_service.create_project(db, payload)


@router.get("/{crp_code}", response_model=ProjectDetailOut)
def detail(
    crp_code: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        return project_service.get_project_detail(db, crp_code, current_user.role)
    except project_service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
