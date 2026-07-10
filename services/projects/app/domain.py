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
