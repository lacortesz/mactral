import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.domain import (
    EstadoCuentaPorPagar,
    EstadoCuota,
    EstadoEtapa,
    EstadoInstalacion,
    EstadoItemChecklist,
    Modulo,
    SemaforoColor,
    TipoGastoLogistico,
    TipoItemChecklist,
)


def _values(enum_cls):
    return [e.value for e in enum_cls]


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

    # E4-H2: evita disparar la notificación de Anticipo 2 más de una vez.
    notificado_anticipo2: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # E4-H3 escenario 2: excepción de "ingreso a bodega" cuando el checklist
    # queda con ítems pendientes pero se confirma el ingreso igualmente.
    ingreso_bodega_fecha: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    ingreso_bodega_nota: Mapped[str | None] = mapped_column(Text(), nullable=True)

    # E7-H1: valor del contrato y costo de fabricación, definidos por
    # Administrativo al configurar las cuotas (base del margen bruto de
    # E7-H2). No se pueden modificar sin aprobación de Gerencia.
    valor_contrato: Mapped[int | None] = mapped_column(Integer, nullable=True)
    costo_fabricacion: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # E7-H5: fecha de aprobación de planos, dispara la solicitud de Anticipo 1.
    planos_aprobados_fecha: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    # E7-H5: confirmación manual del Administrador de que la solicitud de
    # Anticipo 1 ya fue enviada al cliente (queda en la línea de tiempo).
    anticipo1_solicitud_confirmada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    module_statuses: Mapped[list["ProjectModuleStatus"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="ProjectModuleStatus.modulo"
    )
    events: Mapped[list["ProjectEvent"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="ProjectEvent.fecha"
    )
    checklist_items: Mapped[list["ImportChecklistItem"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="ImportChecklistItem.orden"
    )
    instalacion: Mapped["Installation | None"] = relationship(
        back_populates="project", cascade="all, delete-orphan", uselist=False
    )
    cuotas: Mapped[list["Cuota"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="Cuota.numero"
    )
    cuentas_por_pagar: Mapped[list["CuentaPorPagar"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="CuentaPorPagar.fecha_vencimiento"
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


class ImportChecklistItem(Base):
    """E4-H1: checklist documental de importación (solo proyectos GM)."""

    __tablename__ = "import_checklist_items"
    __table_args__ = (UniqueConstraint("project_id", "numero", name="uq_checklist_item"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False)
    numero: Mapped[str] = mapped_column(String(8), nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    tipo: Mapped[TipoItemChecklist] = mapped_column(
        SAEnum(TipoItemChecklist, name="tipo_item_checklist", values_callable=_values), nullable=False
    )
    estado: Mapped[EstadoItemChecklist] = mapped_column(
        SAEnum(EstadoItemChecklist, name="estado_item_checklist", values_callable=_values),
        nullable=False,
        default=EstadoItemChecklist.PENDIENTE,
    )
    fecha: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    nota: Mapped[str | None] = mapped_column(Text(), nullable=True)
    adjunto_bytes: Mapped[bytes | None] = mapped_column(LargeBinary(), nullable=True)
    adjunto_nombre: Mapped[str | None] = mapped_column(String(255), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="checklist_items")

    @property
    def tiene_adjunto(self) -> bool:
        return self.adjunto_bytes is not None


class Installation(Base):
    """E5-H1/E5-H2: programación de instalación y acta de entrega (módulo
    Técnico). Relación 1:1 con Project — un proyecto tiene una sola
    instalación, reprogramable."""

    __tablename__ = "installations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), unique=True, nullable=False)
    fecha_instalacion: Mapped[date] = mapped_column(Date(), nullable=False)
    tecnico_id: Mapped[str] = mapped_column(String(36), nullable=False)
    tecnico_nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    ciudad: Mapped[str] = mapped_column(String(255), nullable=False)
    estado: Mapped[EstadoInstalacion] = mapped_column(
        SAEnum(EstadoInstalacion, name="estado_instalacion", values_callable=_values),
        nullable=False,
        default=EstadoInstalacion.PROGRAMADO,
    )

    # E5-H2: acta de entrega.
    fecha_real_entrega: Mapped[date | None] = mapped_column(Date(), nullable=True)
    acta_bytes: Mapped[bytes | None] = mapped_column(LargeBinary(), nullable=True)
    acta_nombre: Mapped[str | None] = mapped_column(String(255), nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text(), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    project: Mapped["Project"] = relationship(back_populates="instalacion")
    historial: Mapped[list["InstallationReprogramming"]] = relationship(
        back_populates="installation", cascade="all, delete-orphan", order_by="InstallationReprogramming.fecha_cambio"
    )

    @property
    def tiene_acta(self) -> bool:
        return self.acta_bytes is not None


class InstallationReprogramming(Base):
    """E5-H1 escenario 2: historial de reprogramaciones de la instalación."""

    __tablename__ = "installation_reprogrammings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    installation_id: Mapped[str] = mapped_column(ForeignKey("installations.id"), nullable=False)
    fecha_anterior: Mapped[date] = mapped_column(Date(), nullable=False)
    fecha_nueva: Mapped[date] = mapped_column(Date(), nullable=False)
    motivo: Mapped[str] = mapped_column(Text(), nullable=False)
    usuario_id: Mapped[str] = mapped_column(String(36), nullable=False)
    usuario_nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    fecha_cambio: Mapped[datetime] = mapped_column(DateTime(), default=datetime.utcnow)

    installation: Mapped["Installation"] = relationship(back_populates="historial")


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


class Cuota(Base):
    """E7-H1: cuotas/anticipos del contrato (cuenta por cobrar al cliente),
    máximo 3 por proyecto."""

    __tablename__ = "cuotas"
    __table_args__ = (UniqueConstraint("project_id", "numero", name="uq_cuota_numero"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    etiqueta: Mapped[str] = mapped_column(String(64), nullable=False)
    monto: Mapped[int] = mapped_column(Integer, nullable=False)
    porcentaje: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_vencimiento: Mapped[date] = mapped_column(Date(), nullable=False)
    estado: Mapped[EstadoCuota] = mapped_column(
        SAEnum(EstadoCuota, name="estado_cuota", values_callable=_values),
        nullable=False,
        default=EstadoCuota.PENDIENTE,
    )
    fecha_pago: Mapped[date | None] = mapped_column(Date(), nullable=True)
    monto_pagado: Mapped[int | None] = mapped_column(Integer, nullable=True)
    referencia_bancaria: Mapped[str | None] = mapped_column(String(255), nullable=True)
    comprobante_bytes: Mapped[bytes | None] = mapped_column(LargeBinary(), nullable=True)
    comprobante_nombre: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # E7-H4: evita duplicar las alertas de "por vencer"/"vencida".
    alertada_proxima: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    alertada_vencida: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    project: Mapped["Project"] = relationship(back_populates="cuotas")

    @property
    def tiene_comprobante(self) -> bool:
        return self.comprobante_bytes is not None


class CuentaPorPagar(Base):
    """E7-H3/E8-H1: gasto logístico / obligación con un proveedor, imputada
    automáticamente al proyecto (E8-H3) y consolidada en el tablero de CxP
    (E7-H3)."""

    __tablename__ = "cuentas_por_pagar"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    tipo: Mapped[TipoGastoLogistico] = mapped_column(
        SAEnum(TipoGastoLogistico, name="tipo_gasto_logistico", values_callable=_values), nullable=False
    )
    proveedor: Mapped[str] = mapped_column(String(255), nullable=False)
    concepto: Mapped[str] = mapped_column(String(255), nullable=False)
    monto: Mapped[int] = mapped_column(Integer, nullable=False)
    moneda: Mapped[str] = mapped_column(String(8), nullable=False, default="COP")
    tasa_cop: Mapped[float | None] = mapped_column(Float(), nullable=True)
    fecha_vencimiento: Mapped[date] = mapped_column(Date(), nullable=False)
    estado: Mapped[EstadoCuentaPorPagar] = mapped_column(
        SAEnum(EstadoCuentaPorPagar, name="estado_cuenta_por_pagar", values_callable=_values),
        nullable=False,
        default=EstadoCuentaPorPagar.PENDIENTE,
    )
    fecha_pago: Mapped[date | None] = mapped_column(Date(), nullable=True)
    soporte_bytes: Mapped[bytes | None] = mapped_column(LargeBinary(), nullable=True)
    soporte_nombre: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # E8-H1 restricción: los viáticos requieren autorización obligatoria del GG.
    autorizado_gg: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(), default=datetime.utcnow)

    project: Mapped["Project"] = relationship(back_populates="cuentas_por_pagar")

    @property
    def tiene_soporte(self) -> bool:
        return self.soporte_bytes is not None

    @property
    def monto_cop(self) -> float:
        return self.monto * self.tasa_cop if self.tasa_cop else float(self.monto)
