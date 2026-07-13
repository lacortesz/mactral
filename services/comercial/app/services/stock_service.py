"""E6-H1/E6-H2: inventario (módulo Stock)."""
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import LineaNegocio, Rol, TipoMovimientoStock, can_manage_stock
from app.models import StockItem, StockMovement
from app.schemas import StockEntryCreate

MENSAJE_SIN_STOCK = "No hay unidades disponibles"


class Actor(Protocol):
    id: str
    name: str
    role: Rol


class NoStockError(Exception):
    pass


class ForbiddenError(Exception):
    pass


def list_stock(db: Session, linea_negocio: LineaNegocio | None = None) -> list[StockItem]:
    stmt = select(StockItem).order_by(StockItem.linea_negocio, StockItem.tipo_producto)
    if linea_negocio is not None:
        stmt = stmt.where(StockItem.linea_negocio == linea_negocio)
    return list(db.execute(stmt).scalars())


def _get_or_create_item(db: Session, data: StockEntryCreate) -> tuple[StockItem, bool]:
    item = db.execute(
        select(StockItem)
        .where(StockItem.linea_negocio == data.linea_negocio, StockItem.tipo_producto == data.tipo_producto)
        .with_for_update()
    ).scalar_one_or_none()

    if item is not None:
        return item, False

    # Escenario 2 (E6-H1): referencia nueva no catalogada — se crea con los
    # datos del formulario antes de registrar la entrada.
    item = StockItem(
        linea_negocio=data.linea_negocio,
        tipo_producto=data.tipo_producto,
        nombre=data.nombre,
        descripcion=data.descripcion,
        color=data.color,
        unidad=data.unidad,
        cantidad_total=0,
        cantidad_disponible=0,
    )
    db.add(item)
    db.flush()
    return item, True


def registrar_entrada(db: Session, actor: Actor, data: StockEntryCreate) -> StockItem:
    if not can_manage_stock(actor.role):
        raise ForbiddenError("Solo Bodega/Administrador (o Gerencia) pueden registrar entradas de inventario.")

    item, _ = _get_or_create_item(db, data)
    item.cantidad_total += data.cantidad
    item.cantidad_disponible += data.cantidad

    db.add(
        StockMovement(
            stock_item_id=item.id,
            tipo=TipoMovimientoStock.ENTRADA,
            cantidad=data.cantidad,
            usuario_id=actor.id,
            usuario_nombre=actor.name,
        )
    )
    db.commit()
    db.refresh(item)
    return item


def reservar_unidad(db: Session, linea_negocio: LineaNegocio, tipo_producto: str) -> StockItem:
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
    return item


def registrar_salida_venta(db: Session, item: StockItem, actor: Actor, crp_code: str) -> None:
    """E6-H2: registra en el historial la unidad descontada al confirmar una
    venta Stock (el descuento en sí ya ocurrió en reservar_unidad, dentro de
    la misma transacción de cierre de venta)."""
    db.add(
        StockMovement(
            stock_item_id=item.id,
            tipo=TipoMovimientoStock.SALIDA,
            cantidad=1,
            usuario_id=actor.id,
            usuario_nombre=actor.name,
            referencia_crp=crp_code,
        )
    )
