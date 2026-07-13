import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.domain import EstadoLead, LineaNegocio, TipoClasificacion, TipoMovimientoStock, TipoPago


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

    # E2-H4: clasificación elegida al marcar el lead como Vendido. Es
    # inmutable una vez confirmada salvo anulación explícita de Gerencia
    # (ver ForbiddenError en estado_service.change_estado).
    clasificacion: Mapped[TipoClasificacion | None] = mapped_column(
        SAEnum(TipoClasificacion, name="tipo_clasificacion", values_callable=_values), nullable=True
    )
    # E2-H4: código del Registro Maestro (GM26-XX/STMB26-XX/STIN26-XX)
    # generado por services/projects al confirmar la clasificación.
    codigo_generado: Mapped[str | None] = mapped_column(String(32), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    interacciones: Mapped[list["LeadInteraction"]] = relationship(
        back_populates="lead", cascade="all, delete-orphan", order_by="LeadInteraction.fecha"
    )
    cotizaciones: Mapped[list["Quotation"]] = relationship(
        back_populates="lead", cascade="all, delete-orphan", order_by="Quotation.version"
    )
    historial_estados: Mapped[list["EstadoHistorial"]] = relationship(
        back_populates="lead", cascade="all, delete-orphan", order_by="EstadoHistorial.fecha"
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


class Quotation(Base):
    """E2-H2: cotización en PDF. Cada regeneración crea una versión nueva;
    las anteriores se conservan como historial (no se sobrescriben)."""

    __tablename__ = "quotations"
    __table_args__ = (UniqueConstraint("lead_id", "version", name="uq_quotation_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)

    valor_equipo: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo_pago: Mapped[TipoPago] = mapped_column(
        SAEnum(TipoPago, name="tipo_pago", values_callable=_values), nullable=False
    )
    anticipo_inicial_pct: Mapped[int] = mapped_column(Integer, nullable=False)
    segundo_anticipo_pct: Mapped[int] = mapped_column(Integer, nullable=False)
    saldo_final_pct: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_estimada_entrega: Mapped[date] = mapped_column(Date(), nullable=False)

    pdf_bytes: Mapped[bytes] = mapped_column(LargeBinary(), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(), default=datetime.utcnow)

    lead: Mapped["Lead"] = relationship(back_populates="cotizaciones")

    @property
    def numero_cotizacion(self) -> str:
        # Restricción E2-H2: el número de cotización es el consecutivo del lead.
        return f"{self.lead.codigo}-v{self.version}"


class StockItem(Base):
    """E2-H4/E6-H1: inventario disponible por línea de negocio y referencia
    (tipo_producto), para la clasificación Stock al cerrar venta y el
    registro manual de entradas por Bodega/Administrador."""

    __tablename__ = "stock_items"
    __table_args__ = (UniqueConstraint("linea_negocio", "tipo_producto", name="uq_stock_item"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    linea_negocio: Mapped[LineaNegocio] = mapped_column(
        SAEnum(LineaNegocio, name="linea_negocio_comercial", values_callable=_values), nullable=False
    )
    tipo_producto: Mapped[str] = mapped_column(String(255), nullable=False)
    nombre: Mapped[str | None] = mapped_column(String(255), nullable=True)
    descripcion: Mapped[str | None] = mapped_column(Text(), nullable=True)
    color: Mapped[str | None] = mapped_column(String(64), nullable=True)
    unidad: Mapped[str] = mapped_column(String(32), nullable=False, default="unidad")
    cantidad_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cantidad_disponible: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    movimientos: Mapped[list["StockMovement"]] = relationship(
        back_populates="item", cascade="all, delete-orphan", order_by="StockMovement.fecha"
    )

    @property
    def ultimo_movimiento(self) -> "StockMovement | None":
        return self.movimientos[-1] if self.movimientos else None


class StockMovement(Base):
    """E6-H1/E6-H2: historial de entradas (manuales) y salidas (automáticas
    al confirmar una venta Stock) de cada referencia."""

    __tablename__ = "stock_movements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    stock_item_id: Mapped[str] = mapped_column(ForeignKey("stock_items.id"), nullable=False)
    tipo: Mapped[TipoMovimientoStock] = mapped_column(
        SAEnum(TipoMovimientoStock, name="tipo_movimiento_stock", values_callable=_values), nullable=False
    )
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime(), default=datetime.utcnow)
    usuario_id: Mapped[str] = mapped_column(String(36), nullable=False)
    usuario_nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    referencia_crp: Mapped[str | None] = mapped_column(String(32), nullable=True)

    item: Mapped["StockItem"] = relationship(back_populates="movimientos")


class EstadoHistorial(Base):
    """E2-H3: registro de cada cambio de estado del lead (secuencial, no
    reversible), con fecha/hora y usuario que lo realizó."""

    __tablename__ = "estado_historial"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id"), nullable=False)
    estado_anterior: Mapped[EstadoLead] = mapped_column(
        SAEnum(EstadoLead, name="estado_lead", values_callable=_values), nullable=False
    )
    estado_nuevo: Mapped[EstadoLead] = mapped_column(
        SAEnum(EstadoLead, name="estado_lead", values_callable=_values), nullable=False
    )
    usuario_id: Mapped[str] = mapped_column(String(36), nullable=False)
    usuario_nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime(), default=datetime.utcnow)

    lead: Mapped["Lead"] = relationship(back_populates="historial_estados")
