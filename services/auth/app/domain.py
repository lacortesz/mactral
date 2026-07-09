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
    ADMINISTRACION = "administracion"


ROLE_MODULE_ACCESS: dict[Rol, set[Modulo]] = {
    Rol.GERENCIA: set(Modulo),
    Rol.COMERCIAL: {Modulo.COMERCIAL, Modulo.REG_MAESTRO},
    Rol.IMPORTACIONES: {Modulo.IMPORTACIONES, Modulo.REG_MAESTRO},
    Rol.TECNICO: {Modulo.TECNICO, Modulo.STOCK, Modulo.REG_MAESTRO},
    Rol.ADMINISTRATIVO: {Modulo.FINANCIERO, Modulo.REG_MAESTRO},
}


def can_manage_users(role: Rol) -> bool:
    """E1-H1: solo Gerencia/Administrador puede crear o modificar usuarios."""
    return role == Rol.GERENCIA


def can_access_module(role: Rol, module: Modulo) -> bool:
    """E1-H2 escenario 3: acceso a módulo no autorizado."""
    return module in ROLE_MODULE_ACCESS.get(role, set())


def accessible_modules(role: Rol) -> list[Modulo]:
    return sorted(ROLE_MODULE_ACCESS.get(role, set()), key=lambda m: m.value)
