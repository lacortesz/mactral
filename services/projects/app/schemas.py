from datetime import date, datetime

from pydantic import BaseModel, model_validator

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


class ProjectSearchResult(BaseModel):
    id: str
    crp_code: str
    cliente: str
    ciudad: str
    etapa_actual: EstadoEtapa
    semaforo_color: SemaforoColor

    model_config = {"from_attributes": True}


class ModuleStatusOut(BaseModel):
    modulo: Modulo
    estado: EstadoEtapa
    bloqueado_por_cierre: bool
    editable_por_mi_rol: bool


class TimelineEventOut(BaseModel):
    fecha: datetime
    origen: str
    mensaje: str

    model_config = {"from_attributes": True}


PREFIJOS_VALIDOS = {"GM", "STMB", "STIN"}


class ModuleStatusIn(BaseModel):
    modulo: Modulo
    estado: EstadoEtapa


class ProjectCreate(BaseModel):
    """E2-H4: alta del Registro Maestro al clasificar un lead como Vendido.
    services/projects no conoce las reglas de negocio de Comercial (qué
    módulos abrir según GM/Stock): el llamador las decide y las envía."""

    crp_prefix: str
    tipo: str
    cliente: str
    ciudad: str
    producto: str
    marca: str
    semaforo_detalle: str = "En fecha"
    modulos: list[ModuleStatusIn]
    evento_origen: str
    evento_mensaje: str

    @model_validator(mode="after")
    def check_prefix(self):
        if self.crp_prefix not in PREFIJOS_VALIDOS:
            raise ValueError(f"Prefijo inválido: debe ser uno de {sorted(PREFIJOS_VALIDOS)}")
        return self


class ProjectCreateOut(BaseModel):
    id: str
    crp_code: str


class ChecklistItemOut(BaseModel):
    numero: str
    nombre: str
    tipo: TipoItemChecklist
    estado: EstadoItemChecklist
    fecha: datetime | None
    nota: str | None
    tiene_adjunto: bool

    model_config = {"from_attributes": True}


class ChecklistItemUpdate(BaseModel):
    estado: EstadoItemChecklist
    nota: str | None = None

    @model_validator(mode="after")
    def check_nota_obligatoria_en_no_aplica(self):
        # Escenario 2 (E4-H1): "No Aplica" siempre requiere justificación.
        if self.estado == EstadoItemChecklist.NO_APLICA and not (self.nota and self.nota.strip()):
            raise ValueError("Escribe una justificación para marcar el ítem como No Aplica")
        return self


class EnviarTecnicoIn(BaseModel):
    # E4-H3 escenario 2: si el checklist queda incompleto, esta nota es la
    # justificación obligatoria del ingreso a bodega excepcional.
    ingreso_bodega_nota: str | None = None


class InstallationCreate(BaseModel):
    fecha_instalacion: date
    tecnico_id: str
    tecnico_nombre: str
    ciudad: str


class InstallationReprogram(BaseModel):
    fecha_instalacion: date
    motivo: str

    @model_validator(mode="after")
    def check_motivo(self):
        if not self.motivo.strip():
            raise ValueError("Escribe el motivo de la reprogramación")
        return self


class InstallationReprogrammingOut(BaseModel):
    fecha_anterior: date
    fecha_nueva: date
    motivo: str
    usuario_nombre: str
    fecha_cambio: datetime

    model_config = {"from_attributes": True}


class ActaEntregaCreate(BaseModel):
    fecha_real_entrega: date
    observaciones: str | None = None


class InstallationOut(BaseModel):
    fecha_instalacion: date
    tecnico_nombre: str
    ciudad: str
    estado: EstadoInstalacion
    historial: list[InstallationReprogrammingOut] = []
    fecha_real_entrega: date | None = None
    tiene_acta: bool = False
    observaciones: str | None = None

    model_config = {"from_attributes": True}


class CuotaIn(BaseModel):
    numero: int
    etiqueta: str
    monto: int
    porcentaje: int
    fecha_vencimiento: date


class CuotasConfigCreate(BaseModel):
    """E7-H1: configuración del esquema de pagos. Máximo 3 cuotas; la suma
    de montos debe igualar el valor del contrato (validación automática)."""

    valor_contrato: int
    costo_fabricacion: int = 0
    cuotas: list[CuotaIn]

    @model_validator(mode="after")
    def check_cuotas(self):
        if not (1 <= len(self.cuotas) <= 3):
            raise ValueError("Máximo 3 cuotas por proyecto")
        if self.valor_contrato <= 0:
            raise ValueError("El valor del contrato debe ser mayor a cero")
        suma = sum(c.monto for c in self.cuotas)
        if suma != self.valor_contrato:
            raise ValueError("La suma de las cuotas debe igualar el valor del contrato")
        numeros = sorted(c.numero for c in self.cuotas)
        if numeros != list(range(1, len(self.cuotas) + 1)):
            raise ValueError("Las cuotas deben numerarse consecutivamente desde 1")
        return self


class CuotaPagoCreate(BaseModel):
    fecha_pago: date
    monto_pagado: int
    referencia_bancaria: str | None = None


class CuotaOut(BaseModel):
    numero: int
    etiqueta: str
    monto: int
    porcentaje: int
    fecha_vencimiento: date
    estado: EstadoCuota
    fecha_pago: date | None
    monto_pagado: int | None
    referencia_bancaria: str | None
    tiene_comprobante: bool
    alertada_proxima: bool
    alertada_vencida: bool

    model_config = {"from_attributes": True}


class TasaCambioOut(BaseModel):
    moneda: str
    tasa_cop: float


class TableroFinancieroOut(BaseModel):
    """E7-H2: tablero financiero por proyecto."""

    crp_code: str
    valor_contrato: int | None
    costo_fabricacion: int
    total_cobrado: int
    total_por_cobrar: int
    total_gastos_logisticos_cop: float
    margen_bruto: float | None
    semaforo_pago: SemaforoColor
    cuotas: list[CuotaOut]
    tasas_cambio: list[TasaCambioOut]
    planos_aprobados_fecha: datetime | None
    anticipo1_solicitud_confirmada: bool


class ComentarioCreate(BaseModel):
    mensaje: str

    @model_validator(mode="after")
    def check_mensaje(self):
        if not self.mensaje.strip():
            raise ValueError("El comentario no puede estar vacío")
        return self


class ComentarioOut(BaseModel):
    id: str
    autor_nombre: str
    mensaje: str
    fecha: datetime
    menciones: list[str]

    model_config = {"from_attributes": True}


class SemaforoConteoOut(BaseModel):
    color: SemaforoColor
    cantidad: int


class EtapaConteoOut(BaseModel):
    etapa: EstadoEtapa
    cantidad: int


class DashboardOut(BaseModel):
    """E10-H1: dashboard global de proyectos activos."""

    total_activos: int
    total_entregados: int
    por_semaforo: list[SemaforoConteoOut]
    por_etapa: list[EtapaConteoOut]
    proyectos: list[ProjectSearchResult]


class RentabilidadProyectoOut(BaseModel):
    """E10-H2: vista gerencial de rentabilidad por proyecto."""

    crp_code: str
    cliente: str
    valor_contrato: int
    costo_fabricacion: int
    gastos_logisticos_cop: float
    margen_bruto: float
    margen_pct: float


class RentabilidadOut(BaseModel):
    proyectos: list[RentabilidadProyectoOut]
    margen_bruto_total: float
    valor_contrato_total: int


class NotificacionOut(BaseModel):
    """E9-H2: bandeja de notificaciones — asignación e inactividad."""

    id: str
    crp_code: str
    modulo: Modulo
    tipo: str
    mensaje: str
    fecha: datetime
    leida: bool

    model_config = {"from_attributes": True}


class CuentaPorPagarCreate(BaseModel):
    """E8-H1: registro de un gasto logístico (vuelo/hospedaje/transporte/
    viáticos/otro), que a la vez es la cuenta por pagar consolidada de
    E7-H3 imputada automáticamente al proyecto — E8-H3."""

    tipo: TipoGastoLogistico
    proveedor: str
    concepto: str
    monto: int
    moneda: str = "COP"
    tasa_cop: float | None = None
    fecha_vencimiento: date
    autorizado_gg: bool = False

    @model_validator(mode="after")
    def check_viaticos_requiere_autorizacion(self):
        if self.monto <= 0:
            raise ValueError("El monto debe ser mayor a cero")
        if self.tipo == TipoGastoLogistico.VIATICOS and not self.autorizado_gg:
            raise ValueError("Los viáticos requieren autorización obligatoria del Gerente General")
        return self


class CuentaPorPagarOut(BaseModel):
    """E7-H3: fila del tablero consolidado de cuentas por pagar (también es
    la fuente del registro de gasto logístico de E8-H1, imputado
    automáticamente al proyecto por su project_id — E8-H3)."""

    id: str
    crp_code: str
    tipo: TipoGastoLogistico
    proveedor: str
    concepto: str
    monto: int
    moneda: str
    tasa_cop: float | None
    monto_cop: float
    fecha_vencimiento: date
    estado: EstadoCuentaPorPagar
    fecha_pago: date | None
    tiene_soporte: bool
    autorizado_gg: bool

    model_config = {"from_attributes": True}


class CuentasPorPagarConsolidadoOut(BaseModel):
    items: list[CuentaPorPagarOut]
    total_pendiente_cop: float
    total_pagado_cop: float


class ProjectDetailOut(BaseModel):
    id: str
    crp_code: str
    tipo: str
    cliente: str
    ciudad: str
    producto: str
    marca: str
    etapa_actual: EstadoEtapa
    semaforo_color: SemaforoColor
    semaforo_detalle: str
    modulos: list[ModuleStatusOut]
    linea_de_tiempo: list[TimelineEventOut]
    checklist: list[ChecklistItemOut] = []
    ingreso_bodega_fecha: datetime | None = None
    ingreso_bodega_nota: str | None = None
    instalacion: InstallationOut | None = None

