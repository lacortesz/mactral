from datetime import date, datetime

from pydantic import BaseModel, model_validator

from app.domain import EstadoLead, LineaNegocio, TipoPago

REQUIRED_FIELDS_MESSAGE = "Completa los campos requeridos"


class LeadCreate(BaseModel):
    nombre: str = ""
    telefono: str | None = None
    correo: str | None = None
    ciudad: str = ""
    canal_entrada: str = ""
    linea_negocio: LineaNegocio
    tipo_producto: str = ""
    marca: str = ""

    @model_validator(mode="after")
    def check_required_fields(self):
        # Escenario 2 (E2-H1): nombre y al menos un dato de contacto
        # (teléfono o correo) son obligatorios, además del resto de campos
        # del formulario.
        has_name = bool(self.nombre and self.nombre.strip())
        has_contact = bool((self.telefono and self.telefono.strip()) or (self.correo and self.correo.strip()))
        has_rest = all(
            bool(v and v.strip())
            for v in [self.ciudad, self.canal_entrada, self.tipo_producto, self.marca]
        )
        if not (has_name and has_contact and has_rest):
            raise ValueError(REQUIRED_FIELDS_MESSAGE)
        return self


class LeadListItem(BaseModel):
    id: str
    codigo: str
    nombre: str
    ciudad: str
    tipo_producto: str
    linea_negocio: LineaNegocio
    vendedor_nombre: str
    estado: EstadoLead
    created_at: datetime

    model_config = {"from_attributes": True}


class InteractionOut(BaseModel):
    fecha: datetime
    canal: str
    resumen: str
    usuario_nombre: str

    model_config = {"from_attributes": True}


class QuotationCreate(BaseModel):
    valor_equipo: int
    tipo_pago: TipoPago
    anticipo_inicial_pct: int
    segundo_anticipo_pct: int
    saldo_final_pct: int
    fecha_estimada_entrega: date

    @model_validator(mode="after")
    def check_values(self):
        # Restricción E2-H2: la calculadora usa el formato oficial, no es
        # texto libre — el desglose siempre debe sumar el 100% del contrato.
        if self.valor_equipo <= 0:
            raise ValueError("El valor del equipo debe ser mayor a cero")
        total_pct = self.anticipo_inicial_pct + self.segundo_anticipo_pct + self.saldo_final_pct
        if total_pct != 100:
            raise ValueError("Los porcentajes de anticipo deben sumar 100%")
        return self


class QuotationOut(BaseModel):
    version: int
    numero_cotizacion: str
    valor_equipo: int
    tipo_pago: TipoPago
    anticipo_inicial_pct: int
    segundo_anticipo_pct: int
    saldo_final_pct: int
    fecha_estimada_entrega: date
    created_at: datetime

    model_config = {"from_attributes": True}


class LeadDetailOut(BaseModel):
    id: str
    codigo: str
    nombre: str
    telefono: str | None
    correo: str | None
    ciudad: str
    canal_entrada: str
    linea_negocio: LineaNegocio
    tipo_producto: str
    marca: str
    estado: EstadoLead
    vendedor_id: str
    vendedor_nombre: str
    created_at: datetime
    interacciones: list[InteractionOut]
    cotizaciones: list[QuotationOut] = []

    model_config = {"from_attributes": True}


class InteractionCreate(BaseModel):
    canal: str
    resumen: str

    @model_validator(mode="after")
    def check_required(self):
        if not (self.canal and self.canal.strip()) or not (self.resumen and self.resumen.strip()):
            raise ValueError(REQUIRED_FIELDS_MESSAGE)
        return self
