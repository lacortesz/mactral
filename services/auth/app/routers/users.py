from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_module_access
from app.domain import Modulo
from app.schemas import StatusUpdate, UserCreate, UserCreateOut, UserOut
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])

# La gestión de usuarios es su propio módulo ("administracion"): además de
# la restricción de negocio de E1-H1 (solo Gerencia crea/modifica), E1-H2
# exige que el acceso directo por URL/API de un rol no autorizado también
# quede bloqueado (escenario 3), no solo oculto en la navegación.
require_admin_module = require_module_access(Modulo.ADMINISTRACION)


@router.get("", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_admin_module),
):
    return user_service.list_users(db)


@router.post("", response_model=UserCreateOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin_module),
):
    try:
        user, activation_link = user_service.create_user(db, current_user.role, payload)
    except user_service.ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except user_service.DuplicateEmailError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return UserCreateOut(**UserOut.model_validate(user).model_dump(), activation_link=activation_link)


@router.patch("/{user_id}", response_model=UserOut)
def update_status(
    user_id: str,
    payload: StatusUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin_module),
):
    try:
        if payload.status.value == "INACTIVO":
            user = user_service.deactivate_user(db, current_user.role, user_id)
        else:
            user = user_service.activate_user(db, current_user.role, user_id)
    except user_service.ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except user_service.UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return user
