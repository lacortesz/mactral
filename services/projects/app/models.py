import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.domain import EstadoEtapa, Modulo, SemaforoColor


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    crp_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(255), nullable=False)
    cliente: Mapped[str] = mapped_column(String(255), nullable=False)
    ciudad: Mapped[str] = mapped_column(String(255), nullable=False)
    producto: Mapped[str] = mapped_column(String(255), nullable=False)
    marca: Mapped[str] = mapped_column(String(255), nullable=False)

    etapa_actual: Mapped[EstadoEtapa] = mapped_column(SAEnum(EstadoEtapa, name="estado_etapa"), nullable=False)
    semaforo_color: Mapped[SemaforoColor] = mapped_column(
        SAEnum(SemaforoColor, name="semaforo_color"), nullable=False
    )
    semaforo_detalle: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    module_statuses: Mapped[list["ProjectModuleStatus"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="ProjectModuleStatus.modulo"
    )
    events: Mapped[list["ProjectEvent"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="ProjectEvent.fecha"
    )


class ProjectModuleStatus(Base):
    __tablename__ = "project_module_status"
    __table_args__ = (UniqueConstraint("project_id", "modulo", name="uq_project_modulo"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    # values_callable: Modulo tiene nombres en MAYÚSCULAS pero valores en
    # minúsculas-con-guion ("comercial", "reg-maestro"...); sin esto,
    # SQLAlchemy manda el *nombre* del enum a la base de datos en vez del
    # valor, y el CREATE TYPE de la migración usa los valores.
    modulo: Mapped[Modulo] = mapped_column(
        SAEnum(Modulo, name="modulo", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
    )
    estado: Mapped[EstadoEtapa] = mapped_column(SAEnum(EstadoEtapa, name="estado_etapa_modulo"), nullable=False)

    project: Mapped["Project"] = relationship(back_populates="module_statuses")


class ProjectEvent(Base):
    __tablename__ = "project_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    origen: Mapped[str] = mapped_column(String(64), nullable=False)
    mensaje: Mapped[str] = mapped_column(Text(), nullable=False)

    project: Mapped["Project"] = relationship(back_populates="events")


class ProjectCounter(Base):
    """E2-H4: consecutivo por prefijo (GM/STMB/STIN) y año, ej. GM26-001.
    Mismo patrón de lock de fila que LeadCounter en services/comercial para
    evitar duplicados con altas concurrentes."""

    __tablename__ = "project_counters"
    __table_args__ = (UniqueConstraint("prefijo", "anio", name="uq_project_counter"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    prefijo: Mapped[str] = mapped_column(String(16), nullable=False)
    anio: Mapped[int] = mapped_column(Integer, nullable=False)
    ultimo_valor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
