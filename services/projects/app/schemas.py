from datetime import datetime

from pydantic import BaseModel

from app.domain import EstadoEtapa, Modulo, SemaforoColor


class ProjectSearchResult(BaseModel):
    id: str
    crp_code: str
    cliente: str
    ciudad: str

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
