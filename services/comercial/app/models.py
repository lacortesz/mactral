import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.domain import EstadoLead, LineaNegocio


def _values(enum_cls):
    return [e.value for e in enum_cls]


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    codigo: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)

    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    telefono: Mapped[str | None] = mapped_column(String(64), nullable=True)
    correo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ciudad: Mapped[str] = mapped_column(String(255), nullable=False)
    canal_entrada: Mapped[str] = mapped_column(String(64), nullable=False)
    linea_negocio: Mapped[LineaNegocio] = mapped_column(
        SAEnum(LineaNegocio, name="linea_negocio_comercial", values_callable=_values), nullable=False
    )
    tipo_producto: Mapped[str] = mapped_column(String(255), nullable=False)
    marca: Mapped[str] = mapped_column(String(255), nullable=False)

    estado: Mapped[EstadoLead] = mapped_column(
        SAEnum(EstadoLead, name="estado_lead", values_callable=_values),
        nullable=False,
        default=EstadoLead.COTIZAR,
    )

    vendedor_id: Mapped[str] = mapped_column(String(36), nullable=False)
    vendedor_nombre: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    interacciones: Mapped[list["LeadInteraction"]] = relationship(
        back_populates="lead", cascade="all, delete-orphan", order_by="LeadInteraction.fecha"
    )


class LeadInteraction(Base):
    __tablename__ = "lead_interactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id"), nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime(), default=datetime.utcnow)
    canal: Mapped[str] = mapped_column(String(64), nullable=False)
    resumen: Mapped[str] = mapped_column(Text(), nullable=False)
    usuario_id: Mapped[str] = mapped_column(String(36), nullable=False)
    usuario_nombre: Mapped[str] = mapped_column(String(255), nullable=False)

    lead: Mapped["Lead"] = relationship(back_populates="interacciones")


class LeadCounter(Base):
    """Consecutivo por línea de negocio y año (ej. MOB26-001). Se
    incrementa con un lock de fila para evitar duplicados ante altas
    concurrentes (mismo enfoque que exige E3-H1 para el código de proyecto).
    """

    __tablename__ = "lead_counters"
    __table_args__ = (UniqueConstraint("linea_negocio", "anio", name="uq_lead_counter"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    linea_negocio: Mapped[LineaNegocio] = mapped_column(
        SAEnum(LineaNegocio, name="linea_negocio_comercial", values_callable=_values), nullable=False
    )
    anio: Mapped[int] = mapped_column(Integer, nullable=False)
    ultimo_valor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
