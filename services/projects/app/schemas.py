from datetime import datetime

from pydantic import BaseModel, model_validator

from app.domain import EstadoEtapa, EstadoItemChecklist, Modulo, SemaforoColor, TipoItemChecklist


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
