import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.domain import EstadoUsuario, LineaNegocio, Rol


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    role: Mapped[Rol] = mapped_column(SAEnum(Rol, name="rol"), nullable=False)
    linea_negocio: Mapped[LineaNegocio] = mapped_column(
        SAEnum(LineaNegocio, name="linea_negocio"), nullable=False
    )
    status: Mapped[EstadoUsuario] = mapped_column(
        SAEnum(EstadoUsuario, name="estado_usuario"),
        nullable=False,
        default=EstadoUsuario.ACTIVO,
    )

    activation_token: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    activation_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)

    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    last_access_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow
    )
