"""E1-H2: inicio de sesión seguro."""
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.domain import EstadoUsuario
from app.mailer import build_activation_link, send_activation_email, send_password_reset_email
from app.models import User
from app.security import generate_token, hash_password, utcnow, verify_password


class InvalidCredentialsError(Exception):
    pass


class InactiveAccountError(Exception):
    pass


class InvalidActivationTokenError(Exception):
    pass


class AccountLockedError(Exception):
    def __init__(self, retry_after_seconds: int):
        self.retry_after_seconds = retry_after_seconds
        super().__init__(
            "La cuenta está bloqueada temporalmente por demasiados intentos fallidos."
        )


def _find_by_email(db: Session, email: str) -> User | None:
    return db.execute(select(User).where(User.email == email)).scalar_one_or_none()


def login(db: Session, email: str, password: str) -> User:
    user = _find_by_email(db, email)
    if user is None or not user.password_hash:
        # Escenario 2: correo o contraseña incorrectos (sin revelar cuál).
        raise InvalidCredentialsError("Correo o contraseña incorrectos")

    now = utcnow()

    if user.locked_until and user.locked_until > now:
        # Cuenta bloqueada tras 5 intentos fallidos (E1-H2, escenario 2).
        raise AccountLockedError(int((user.locked_until - now).total_seconds()))

    if user.locked_until and user.locked_until <= now:
        # El bloqueo ya expiró: se reinicia el contador antes de evaluar.
        user.failed_login_attempts = 0
        user.locked_until = None

    if not verify_password(password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.max_failed_login_attempts:
            user.locked_until = now + timedelta(minutes=settings.lockout_minutes)
            user.failed_login_attempts = 0
        db.commit()
        raise InvalidCredentialsError("Correo o contraseña incorrectos")

    if user.status != EstadoUsuario.ACTIVO:
        raise InactiveAccountError("La cuenta está inactiva")

    # Escenario 1: login exitoso, se reinician los contadores de bloqueo.
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_access_at = now
    db.commit()
    db.refresh(user)
    return user


def request_password_reset(db: Session, email: str) -> None:
    """Restricción E1-H2: recuperación de contraseña por correo.

    No revela si el correo existe o no (evita enumeración de usuarios):
    siempre retorna sin error, y solo envía el enlace cuando hay una
    cuenta asociada.
    """
    user = _find_by_email(db, email)
    if user is None:
        return

    token = generate_token()
    user.activation_token = token
    user.activation_token_expires_at = utcnow() + timedelta(hours=settings.reset_token_ttl_hours)
    db.commit()

    link = build_activation_link(token)
    send_password_reset_email(user.email, link)


def set_password_with_token(db: Session, token: str, password: str) -> User:
    user = db.execute(select(User).where(User.activation_token == token)).scalar_one_or_none()
    if (
        user is None
        or user.activation_token_expires_at is None
        or user.activation_token_expires_at < utcnow()
    ):
        raise InvalidActivationTokenError("El enlace de activación no es válido o expiró")

    user.password_hash = hash_password(password)
    user.activation_token = None
    user.activation_token_expires_at = None
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()
    db.refresh(user)
    return user
