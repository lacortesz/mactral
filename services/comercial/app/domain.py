"""Catálogos de negocio para E2-H1 (registro de lead).

Rol y LineaNegocio son una copia mínima de los mismos catálogos en
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


class LineaNegocio(str, Enum):
    MOBILITY = "MOBILITY"
    INDUSTRY = "INDUSTRY"


class EstadoLead(str, Enum):
    COTIZAR = "COTIZAR"
    ENVIADA = "ENVIADA"
    VENDIDO = "VENDIDO"


LEAD_CODE_PREFIX: dict[LineaNegocio, str] = {
    LineaNegocio.MOBILITY: "MOB",
    LineaNegocio.INDUSTRY: "IND",
}


def can_manage_leads(role: Rol) -> bool:
    """E2-H1 restricción: solo el vendedor (rol Comercial) y Gerencia
    pueden crear/editar leads."""
    return role in (Rol.COMERCIAL, Rol.GERENCIA)
