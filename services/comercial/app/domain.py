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


class TipoPago(str, Enum):
    CONTADO = "CONTADO"
    CREDITO = "CREDITO"


# E2-H4: clasificación al marcar un lead como Vendido. La generación de
# códigos (GM26-XX / STMB26-XX / STIN26-XX) se implementa en E2-H4; aquí solo
# se define el catálogo porque E2-H3 ya necesita pedirla al cerrar la venta.
class TipoClasificacion(str, Enum):
    GM = "GM"
    STOCK_MOBILITY = "STOCK_MOBILITY"
    STOCK_INDUSTRY = "STOCK_INDUSTRY"


LEAD_CODE_PREFIX: dict[LineaNegocio, str] = {
    LineaNegocio.MOBILITY: "MOB",
    LineaNegocio.INDUSTRY: "IND",
}

# E2-H3: transiciones válidas del estado del lead. Son secuenciales y no
# reversibles una vez avanzados (sin retrocesos ni saltos).
ESTADO_SIGUIENTE: dict[EstadoLead, EstadoLead] = {
    EstadoLead.COTIZAR: EstadoLead.ENVIADA,
    EstadoLead.ENVIADA: EstadoLead.VENDIDO,
}


def can_manage_leads(role: Rol) -> bool:
    """E2-H1 restricción: solo el vendedor (rol Comercial) y Gerencia
    pueden crear/editar leads."""
    return role in (Rol.COMERCIAL, Rol.GERENCIA)


# E6-H1: registro de entradas de inventario.
class TipoMovimientoStock(str, Enum):
    ENTRADA = "ENTRADA"
    SALIDA = "SALIDA"


def can_manage_stock(role: Rol) -> bool:
    """Restricción E6-H1: solo Bodega y Administrador pueden registrar
    entradas. La plataforma no tiene un rol "Bodega" independiente (E1-H1
    fija los roles en Comercial/Importaciones/Técnico/Administrativo/
    Gerencia), así que "Bodega" se mapea al rol Administrativo."""
    return role in (Rol.ADMINISTRATIVO, Rol.GERENCIA)
