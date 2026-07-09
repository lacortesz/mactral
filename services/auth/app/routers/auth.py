from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_user
from app.domain import accessible_modules
from app.schemas import (
    ForgotPasswordRequest,
    LoginOut,
    LoginRequest,
    SetPasswordRequest,
    UserOut,
)
from app.security import create_session_token
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginOut)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    try:
        user = auth_service.login(db, payload.email, payload.password)
    except auth_service.AccountLockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail={
                "message": "Cuenta bloqueada temporalmente por demasiados intentos fallidos.",
                "retry_after_seconds": exc.retry_after_seconds,
            },
        ) from exc
    except auth_service.InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except auth_service.InactiveAccountError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    token = create_session_token(user.id, user.name, user.email, user.role)
    return LoginOut(access_token=token, user=UserOut.model_validate(user))


@router.post("/refresh")
def refresh(current_user: CurrentUser = Depends(get_current_user)):
    """Renueva la sesión mientras el usuario esté activo (E1-H2: expiración
    tras 8 horas de *inactividad*, no de tiempo absoluto). El frontend lo
    llama periódicamente mientras hay actividad; si deja de llamarlo, el
    JWT expira 8 horas después de la última renovación.
    """
    token = create_session_token(
        current_user.id, current_user.name, current_user.email, current_user.role
    )
    return {"access_token": token}


@router.get("/me")
def me(current_user: CurrentUser = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
        "accessible_modules": [m.value for m in accessible_modules(current_user.role)],
    }


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    auth_service.request_password_reset(db, payload.email)
    # Respuesta genérica siempre: no debe revelar si el correo existe.
    return {"message": "Si el correo existe, recibirás un enlace para restablecer tu contraseña."}


@router.post("/set-password")
def set_password(payload: SetPasswordRequest, db: Session = Depends(get_db)):
    try:
        auth_service.set_password_with_token(db, payload.token, payload.password)
    except auth_service.InvalidActivationTokenError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"message": "Contraseña establecida correctamente"}
