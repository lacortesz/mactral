from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_user
from app.domain import EstadoItemChecklist
from app.schemas import (
    ActaEntregaCreate,
    ChecklistItemOut,
    ChecklistItemUpdate,
    EnviarTecnicoIn,
    InstallationCreate,
    InstallationOut,
    InstallationReprogram,
    ProjectCreate,
    ProjectCreateOut,
    ProjectDetailOut,
    ProjectSearchResult,
)
from app.services import installation_service, project_service

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


@router.patch("/{crp_code}/checklist/{numero}", response_model=ChecklistItemOut)
async def update_checklist_item(
    crp_code: str,
    numero: str,
    estado: EstadoItemChecklist = Form(...),
    nota: str | None = Form(None),
    archivo: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        payload = ChecklistItemUpdate(estado=estado, nota=nota)
    except Exception as exc:  # pydantic ValidationError -> 422 con el mensaje de negocio
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    adjunto_bytes = await archivo.read() if archivo is not None else None
    adjunto_nombre = archivo.filename if archivo is not None else None

    try:
        return project_service.update_checklist_item(
            db, current_user.role, crp_code, numero, payload, adjunto_bytes, adjunto_nombre
        )
    except project_service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except project_service.ChecklistItemNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except project_service.ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/{crp_code}/checklist/{numero}/adjunto")
def get_checklist_attachment(
    crp_code: str,
    numero: str,
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(get_current_user),
):
    try:
        item = project_service.get_checklist_attachment(db, crp_code, numero)
    except project_service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except project_service.ChecklistItemNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if item.adjunto_bytes is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El ítem no tiene un adjunto")

    return Response(
        content=item.adjunto_bytes,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{item.adjunto_nombre or numero}"'},
    )


@router.post("/{crp_code}/enviar-tecnico", response_model=ProjectDetailOut)
def enviar_a_tecnico(
    crp_code: str,
    payload: EnviarTecnicoIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        project_service.enviar_a_tecnico(db, current_user.role, crp_code, payload.ingreso_bodega_nota)
        return project_service.get_project_detail(db, crp_code, current_user.role)
    except project_service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except project_service.ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except project_service.NoChecklistError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except project_service.TransitionBlockedError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post("/{crp_code}/instalacion", response_model=InstallationOut, status_code=status.HTTP_201_CREATED)
def programar_instalacion(
    crp_code: str,
    payload: InstallationCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        return installation_service.programar_instalacion(db, current_user, crp_code, payload)
    except project_service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except project_service.ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except installation_service.InstallationAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except installation_service.InvalidInstallationDateError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.patch("/{crp_code}/instalacion", response_model=InstallationOut)
def reprogramar_instalacion(
    crp_code: str,
    payload: InstallationReprogram,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        return installation_service.reprogramar_instalacion(db, current_user, crp_code, payload)
    except project_service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except project_service.ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except installation_service.InstallationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except installation_service.InvalidInstallationDateError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.patch("/{crp_code}/instalacion/acta", response_model=InstallationOut)
async def registrar_acta(
    crp_code: str,
    fecha_real_entrega: str = Form(...),
    observaciones: str | None = Form(None),
    acta: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        payload = ActaEntregaCreate(fecha_real_entrega=fecha_real_entrega, observaciones=observaciones)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    acta_bytes = await acta.read() if acta is not None else None
    acta_nombre = acta.filename if acta is not None else None

    try:
        return installation_service.registrar_acta(
            db, current_user, crp_code, payload, acta_bytes, acta_nombre
        )
    except project_service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except project_service.ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except installation_service.InstallationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{crp_code}/instalacion/acta")
def get_acta_attachment(
    crp_code: str,
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(get_current_user),
):
    try:
        installation = installation_service.get_acta_attachment(db, crp_code)
    except project_service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except installation_service.InstallationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if installation.acta_bytes is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El acta no ha sido adjuntada")

    return Response(
        content=installation.acta_bytes,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{installation.acta_nombre or "acta"}"'},
    )
