"""E2-H4: disponibilidad de stock al clasificar un lead como Vendido."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import LineaNegocio
from app.models import StockItem

MENSAJE_SIN_STOCK = "No hay unidades disponibles"


class NoStockError(Exception):
    pass


def reservar_unidad(db: Session, linea_negocio: LineaNegocio, tipo_producto: str) -> None:
    # Mismo principio de lock de fila que LeadCounter: dos ventas cerrándose
    # a la vez sobre el último cupo no deben reservar la misma unidad.
    item = db.execute(
        select(StockItem)
        .where(StockItem.linea_negocio == linea_negocio, StockItem.tipo_producto == tipo_producto)
        .with_for_update()
    ).scalar_one_or_none()

    if item is None or item.cantidad_disponible <= 0:
        raise NoStockError(MENSAJE_SIN_STOCK)

    item.cantidad_disponible -= 1
