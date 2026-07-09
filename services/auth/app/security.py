import secrets
from datetime import datetime, timedelta

import bcrypt
import jwt

from app.config import settings
from app.domain import Rol

JWT_ALGORITHM = "HS256"


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def generate_token() -> str:
    return secrets.token_hex(24)


def utcnow() -> datetime:
    """UTC *naive* (sin tzinfo) a propósito: SQLite descarta el offset de
    tzinfo al releer columnas DateTime, así que mezclar naive/aware rompe
    las comparaciones. Se mantiene naive de forma consistente en todo el
    servicio; Postgres guarda estos valores igualmente como UTC.
    """
    return datetime.utcnow()


def create_session_token(user_id: str, name: str, email: str, role: Rol) -> str:
    payload = {
        "sub": user_id,
        "name": name,
        "email": email,
        "role": role.value,
        "iat": utcnow(),
        "exp": utcnow() + timedelta(hours=settings.session_ttl_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def decode_session_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
