"""E1-H1: gestión de usuarios y roles."""
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.domain import EstadoUsuario, Rol, can_manage_users
from app.mailer import build_activation_link, send_activation_email
from app.models import User
from app.schemas import UserCreate
from app.security import generate_token, utcnow


class ForbiddenError(Exception):
    pass


class DuplicateEmailError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


def list_users(db: Session) -> list[User]:
    return list(db.execute(select(User).order_by(User.created_at.desc())).scalars())


def create_user(db: Session, actor_role: Rol, data: UserCreate) -> tuple[User, str]:
    # Escenario E1-H1: solo Gerencia/Administrador puede crear usuarios.
    if not can_manage_users(actor_role):
        raise ForbiddenError(
            "Solo el rol Gerencia/Administrador puede crear o modificar usuarios."
        )

    existing = db.execute(select(User).where(User.email == data.email)).scalar_one_or_none()
    if existing:
        # Escenario 2: correo duplicado, no se crea registro.
        raise DuplicateEmailError("Ya existe un usuario con ese correo")

    token = generate_token()
    user = User(
        name=data.name,
        email=data.email,
        role=data.role,
        linea_negocio=data.linea_negocio,
        status=EstadoUsuario.ACTIVO,
        activation_token=token,
        activation_token_expires_at=utcnow() + timedelta(hours=settings.activation_token_ttl_hours),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    link = build_activation_link(token)
    send_activation_email(user.email, link)
    return user, link


def _set_status(db: Session, actor_role: Rol, user_id: str, status: EstadoUsuario) -> User:
    if not can_manage_users(actor_role):
        raise ForbiddenError(
            "Solo el rol Gerencia/Administrador puede crear o modificar usuarios."
        )

    user = db.get(User, user_id)
    if user is None:
        raise UserNotFoundError("Usuario no encontrado")

    # Escenario 3: desactivar/activar solo cambia el estado; el historial
    # y los demás datos permanecen intactos.
    user.status = status
    db.commit()
    db.refresh(user)
    return user


def deactivate_user(db: Session, actor_role: Rol, user_id: str) -> User:
    return _set_status(db, actor_role, user_id, EstadoUsuario.INACTIVO)


def activate_user(db: Session, actor_role: Rol, user_id: str) -> User:
    return _set_status(db, actor_role, user_id, EstadoUsuario.ACTIVO)
