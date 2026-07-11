"""Catálogos de negocio (roles, líneas de negocio, estado, módulos).

Fuente única de verdad para las reglas de E1-H1 (gestión de usuarios) y
E1-H2 (control de acceso por módulo). El frontend mantiene una copia
mínima de ROLE_MODULE_ACCESS para filtrar la navegación; aquí es donde se
aplica realmente la autorización.
"""
from enum import Enum


class Rol(str, Enum):
    COMERCIAL = "COMERCIAL"
    IMPORTACIONES = "IMPORTACIONES"
    TECNICO = "TECNICO"
    ADMINISTRATIVO = "ADMINISTRATIVO"
    GERENCIA = "GERENCIA"


class LineaNegocio(str, Enum):
    MOBILITY = "MOBILITY"
    INDUSTRY = "INDUSTRY"
    AMBAS = "AMBAS"


class EstadoUsuario(str, Enum):
    ACTIVO = "ACTIVO"
    INACTIVO = "INACTIVO"


class Modulo(str, Enum):
    COMERCIAL = "comercial"
    REG_MAESTRO = "reg-maestro"
    IMPORTACIONES = "importaciones"
    TECNICO = "tecnico"
    STOCK = "stock"
    FINANCIERO = "financiero"
    LOGISTICA = "logistica"
    ADMINISTRACION = "administracion"


ROLE_MODULE_ACCESS: dict[Rol, set[Modulo]] = {
    Rol.GERENCIA: set(Modulo),
    # E6-H1: Comercial consulta la disponibilidad de stock (no la edita) al
    # clasificar una venta como Stock — Mobility/Industry.
    Rol.COMERCIAL: {Modulo.COMERCIAL, Modulo.REG_MAESTRO, Modulo.STOCK},
    Rol.IMPORTACIONES: {Modulo.IMPORTACIONES, Modulo.REG_MAESTRO},
    Rol.TECNICO: {Modulo.TECNICO, Modulo.STOCK, Modulo.REG_MAESTRO},
    # E6-H1/E8-H1: "Bodega"/"Logística" no son roles propios de la plataforma
    # (E1-H1 fija los roles); se mapean a Administrativo, que además ya
    # administra Financiero.
    Rol.ADMINISTRATIVO: {Modulo.FINANCIERO, Modulo.REG_MAESTRO, Modulo.STOCK, Modulo.LOGISTICA},
}


def can_manage_users(role: Rol) -> bool:
    """E1-H1: solo Gerencia/Administrador puede crear o modificar usuarios."""
    return role == Rol.GERENCIA


def can_access_module(role: Rol, module: Modulo) -> bool:
    """E1-H2 escenario 3: acceso a módulo no autorizado."""
    return module in ROLE_MODULE_ACCESS.get(role, set())


def accessible_modules(role: Rol) -> list[Modulo]:
    return sorted(ROLE_MODULE_ACCESS.get(role, set()), key=lambda m: m.value)
