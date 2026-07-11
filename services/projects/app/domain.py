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


def can_edit_checklist(role: Rol) -> bool:
    """Restricción E4-H1: solo el rol Importaciones (y Gerencia, con el
    mismo criterio usado en el resto de la plataforma) puede cambiar los
    estados del checklist."""
    return role in (Rol.IMPORTACIONES, Rol.GERENCIA)
