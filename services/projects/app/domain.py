"""Catálogos de negocio para E1-H3 (ficha central del proyecto).

Rol y ROLE_MODULE_ACCESS son una copia mínima de los mismos catálogos en
services/auth/app/domain.py: cada microservicio valida su propio JWT (mismo
JWT_SECRET compartido) sin depender del código interno de otro servicio.
"""
from enum import Enum


class Rol(str, Enum):
    COMERCIAL = "COMERCIAL"
    IMPORTACIONES = "IMPORTACIONES"
    TECNICO = "TECNICO"
    ADMINISTRATIVO = "ADMINISTRATIVO"
    GERENCIA = "GERENCIA"


class Modulo(str, Enum):
    COMERCIAL = "comercial"
    REG_MAESTRO = "reg-maestro"
    IMPORTACIONES = "importaciones"
    TECNICO = "tecnico"


class EstadoEtapa(str, Enum):
    PENDIENTE = "PENDIENTE"
    EN_CURSO = "EN_CURSO"
    CERRADO = "CERRADO"
    BLOQUEADO = "BLOQUEADO"
    # E5-H2: estado final del proyecto al registrar el acta de entrega. Solo
    # se usa en Project.etapa_actual (no en el estado por módulo, que tiene
    # su propio enum "estado_etapa_modulo").
    ENTREGADO = "ENTREGADO"


class SemaforoColor(str, Enum):
    VERDE = "VERDE"
    AMARILLO = "AMARILLO"
    ROJO = "ROJO"


ROLE_MODULE_ACCESS: dict[Rol, set[Modulo]] = {
    Rol.GERENCIA: {Modulo.COMERCIAL, Modulo.REG_MAESTRO, Modulo.IMPORTACIONES, Modulo.TECNICO},
    Rol.COMERCIAL: {Modulo.COMERCIAL, Modulo.REG_MAESTRO},
    Rol.IMPORTACIONES: {Modulo.IMPORTACIONES, Modulo.REG_MAESTRO},
    Rol.TECNICO: {Modulo.TECNICO, Modulo.REG_MAESTRO},
    Rol.ADMINISTRATIVO: {Modulo.REG_MAESTRO},
}


def editable_modules(role: Rol) -> set[Modulo]:
    """Restricción E1-H3: la ficha es igual para todos los roles, solo
    cambia qué secciones puede editar cada uno (hoy es informativo: el
    formulario de edición por módulo pertenece a historias futuras)."""
    return ROLE_MODULE_ACCESS.get(role, set())


# E4-H1: checklist documental de importación (solo aplica a proyectos GM;
# los STMB/STIN van directo a Técnico, restricción de E4-H3).
class TipoItemChecklist(str, Enum):
    REQUERIDO = "REQUERIDO"
    OPCIONAL = "OPCIONAL"


class EstadoItemChecklist(str, Enum):
    PENDIENTE = "PENDIENTE"
    ARCHIVADO = "ARCHIVADO"
    NO_APLICA = "NO_APLICA"


# (número de referencia, nombre, tipo) en el orden del checklist oficial.
CHECKLIST_ITEMS: list[tuple[str, str, TipoItemChecklist]] = [
    ("1", "Detalle de Plano", TipoItemChecklist.REQUERIDO),
    ("2", "Planos / OT", TipoItemChecklist.REQUERIDO),
    ("3", "Proforma / Factura", TipoItemChecklist.REQUERIDO),
    ("4", "SWIFT", TipoItemChecklist.REQUERIDO),
    ("5", "DC", TipoItemChecklist.REQUERIDO),
    ("6", "LIQ", TipoItemChecklist.REQUERIDO),
    ("7", "Lista de Empaque", TipoItemChecklist.REQUERIDO),
    ("8", "HAWBL / BL", TipoItemChecklist.REQUERIDO),
    ("9", "DIM 500", TipoItemChecklist.REQUERIDO),
    ("10", "Aclaración y Complemento", TipoItemChecklist.REQUERIDO),
    ("11", "MDS", TipoItemChecklist.OPCIONAL),
    ("11.1", "Cert. EUR1", TipoItemChecklist.OPCIONAL),
    ("11.2", "Cert. Seguro", TipoItemChecklist.OPCIONAL),
    ("12", "Cotización Flete Internacional", TipoItemChecklist.REQUERIDO),
]

# E4-H2: al archivar este ítem se dispara la notificación de Anticipo 2.
NUMERO_ITEM_BL = "8"

# E7-H5: cuando ambos ítems de plano quedan archivados se consideran los
# "planos aprobados" y se dispara la solicitud de Anticipo 1.
NUMEROS_ITEM_PLANOS = ("1", "2")


def can_edit_checklist(role: Rol) -> bool:
    """Restricción E4-H1: solo el rol Importaciones (y Gerencia, con el
    mismo criterio usado en el resto de la plataforma) puede cambiar los
    estados del checklist."""
    return role in (Rol.IMPORTACIONES, Rol.GERENCIA)


# E5-H1/E5-H2: instalación y entrega (módulo Técnico).
class EstadoInstalacion(str, Enum):
    PROGRAMADO = "PROGRAMADO"
    COMPLETADO = "COMPLETADO"


def can_manage_installation(role: Rol) -> bool:
    """Restricción E5-H1/E5-H2: solo el Coordinador técnico (rol Técnico) y
    Gerencia pueden programar instalaciones y registrar el acta de entrega."""
    return role in (Rol.TECNICO, Rol.GERENCIA)


# E7-H1/E7-H2/E7-H3: cuotas/anticipos (cuentas por cobrar) y cuentas por
# pagar a proveedores (tablero financiero por proyecto).
class EstadoCuota(str, Enum):
    PENDIENTE = "PENDIENTE"
    PAGADO = "PAGADO"


# E8-H1: tipos de gasto logístico (también son la fuente de las cuentas por
# pagar consolidadas de E7-H3 — cada gasto logístico ES una cuenta por
# pagar a un proveedor, imputada automáticamente al proyecto — E8-H3).
class TipoGastoLogistico(str, Enum):
    VUELO = "VUELO"
    HOSPEDAJE = "HOSPEDAJE"
    TRANSPORTE = "TRANSPORTE"
    VIATICOS = "VIATICOS"
    OTRO = "OTRO"


class EstadoCuentaPorPagar(str, Enum):
    PENDIENTE = "PENDIENTE"
    PAGADA = "PAGADA"


def can_manage_financiero(role: Rol) -> bool:
    """Restricción E7-H1/E7-H2: solo Administrativo (Administrador
    financiero) y Gerencia gestionan cuotas, pagos y el tablero financiero."""
    return role in (Rol.ADMINISTRATIVO, Rol.GERENCIA)


def can_manage_logistica(role: Rol) -> bool:
    """Restricción E8-H1: mismo actor que gestiona lo financiero
    (Administrativo/Logística se mapea al rol Administrativo) o Gerencia."""
    return role in (Rol.ADMINISTRATIVO, Rol.GERENCIA)


# E7-H2: tasas de referencia para convertir gastos logísticos en moneda
# extranjera a COP (vista informativa del tablero financiero; no son tasas
# en vivo — no hay integración con un proveedor de tasas de cambio).
TASAS_CAMBIO_REFERENCIA: dict[str, float] = {
    "USD": 4050.0,
    "EUR": 4400.0,
    "GBP": 5150.0,
    "CNY": 560.0,
}


def calcular_semaforo_pago(cuotas: list) -> SemaforoColor:
    """E7-H2: semáforo de pago del proyecto según el estado de sus cuotas.
    ROJO si alguna cuota pendiente ya venció, AMARILLO si alguna vence dentro
    de los próximos 7 días, VERDE en cualquier otro caso (incluye "sin
    cuotas configuradas todavía")."""
    from datetime import date, timedelta

    hoy = date.today()
    pendientes = [c for c in cuotas if c.estado == EstadoCuota.PENDIENTE]
    if any(c.fecha_vencimiento < hoy for c in pendientes):
        return SemaforoColor.ROJO
    if any(c.fecha_vencimiento <= hoy + timedelta(days=7) for c in pendientes):
        return SemaforoColor.AMARILLO
    return SemaforoColor.VERDE
