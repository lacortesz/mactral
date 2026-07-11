from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.domain import Rol
from app.security import decode_session_token

bearer_scheme = HTTPBearer(auto_error=False)


class CurrentUser:
    def __init__(self, id: str, name: str, email: str, role: Rol, raw_token: str):
        self.id = id
        self.name = name
        self.email = email
        self.role = role
        # E2-H4: se reenvía tal cual a services/projects al crear el
        # Registro Maestro, para que "Sistema" actúe con la identidad del
        # vendedor que cerró la venta (mismo JWT_SECRET compartido).
        self.raw_token = raw_token


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")

    payload = decode_session_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión inválida o expirada")

    return CurrentUser(
        id=payload["sub"],
        name=payload["name"],
        email=payload["email"],
        role=Rol(payload["role"]),
        raw_token=credentials.credentials,
    )


def require_comercial_module(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Módulo Comercial: accesible para GERENCIA y COMERCIAL (ver
    ROLE_MODULE_ACCESS en services/auth/app/domain.py)."""
    if current_user.role not in (Rol.COMERCIAL, Rol.GERENCIA):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para acceder a este módulo.",
        )
    return current_user
