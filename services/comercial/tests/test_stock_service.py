"""E6-H1/E6-H2: módulo Stock (inventario)."""
import pytest

from app.domain import LineaNegocio, Rol
from app.schemas import StockEntryCreate
from app.services import stock_service


class _Actor:
    def __init__(self, id: str, name: str, role: Rol):
        self.id = id
        self.name = name
        self.role = role


BODEGA = _Actor("u1", "Andrea Avendaño", Rol.ADMINISTRATIVO)
GERENCIA = _Actor("u2", "Maya Lozada", Rol.GERENCIA)
OTRO_ROL = _Actor("u3", "Carlos Martínez", Rol.COMERCIAL)


# Escenario 1 (E6-H1): ingreso de lote sobre una referencia ya catalogada.
def test_registrar_entrada_sobre_referencia_existente(db_session):
    stock_service.registrar_entrada(
        db_session,
        BODEGA,
        StockEntryCreate(linea_negocio=LineaNegocio.MOBILITY, tipo_producto="SSE Recta", cantidad=5),
    )
    item = stock_service.registrar_entrada(
        db_session,
        BODEGA,
        StockEntryCreate(linea_negocio=LineaNegocio.MOBILITY, tipo_producto="SSE Recta", cantidad=3),
    )

    assert item.cantidad_total == 8
    assert item.cantidad_disponible == 8
    assert len(item.movimientos) == 2
    assert item.ultimo_movimiento.cantidad == 3


# Escenario 2 (E6-H1): referencia nueva no catalogada se crea con la entrada.
def test_registrar_entrada_crea_referencia_nueva(db_session):
    item = stock_service.registrar_entrada(
        db_session,
        BODEGA,
        StockEntryCreate(
            linea_negocio=LineaNegocio.INDUSTRY,
            tipo_producto="Montacargas",
            cantidad=10,
            nombre="Montacargas eléctrico",
            descripcion="Línea industrial",
            color="Amarillo",
            unidad="unidad",
        ),
    )

    assert item.nombre == "Montacargas eléctrico"
    assert item.cantidad_total == 10
    assert item.cantidad_disponible == 10


def test_gerencia_puede_registrar_entrada(db_session):
    item = stock_service.registrar_entrada(
        db_session,
        GERENCIA,
        StockEntryCreate(linea_negocio=LineaNegocio.MOBILITY, tipo_producto="SSE Curva", cantidad=2),
    )
    assert item.cantidad_disponible == 2


def test_otro_rol_no_puede_registrar_entrada(db_session):
    with pytest.raises(stock_service.ForbiddenError):
        stock_service.registrar_entrada(
            db_session,
            OTRO_ROL,
            StockEntryCreate(linea_negocio=LineaNegocio.MOBILITY, tipo_producto="SSE Recta", cantidad=1),
        )


def test_cantidad_no_positiva_lanza_error():
    with pytest.raises(Exception, match="mayor a cero"):
        StockEntryCreate(linea_negocio=LineaNegocio.MOBILITY, tipo_producto="SSE Recta", cantidad=0)


def test_list_stock_filtra_por_linea(db_session):
    stock_service.registrar_entrada(
        db_session, BODEGA, StockEntryCreate(linea_negocio=LineaNegocio.MOBILITY, tipo_producto="SSE Recta", cantidad=1)
    )
    stock_service.registrar_entrada(
        db_session, BODEGA, StockEntryCreate(linea_negocio=LineaNegocio.INDUSTRY, tipo_producto="Montacargas", cantidad=1)
    )

    mobility = stock_service.list_stock(db_session, LineaNegocio.MOBILITY)
    assert len(mobility) == 1
    assert mobility[0].tipo_producto == "SSE Recta"

    todos = stock_service.list_stock(db_session)
    assert len(todos) == 2


# Escenario 1 (E6-H2): descuento automático al reservar una unidad.
def test_reservar_unidad_descuenta_disponible(db_session):
    stock_service.registrar_entrada(
        db_session, BODEGA, StockEntryCreate(linea_negocio=LineaNegocio.MOBILITY, tipo_producto="SSE Recta", cantidad=5)
    )

    item = stock_service.reservar_unidad(db_session, LineaNegocio.MOBILITY, "SSE Recta")
    db_session.commit()

    assert item.cantidad_disponible == 4
    assert item.cantidad_total == 5  # el total no cambia, solo el disponible


def test_registrar_salida_venta_deja_constancia_con_el_crp(db_session):
    stock_service.registrar_entrada(
        db_session, BODEGA, StockEntryCreate(linea_negocio=LineaNegocio.MOBILITY, tipo_producto="SSE Recta", cantidad=1)
    )
    item = stock_service.reservar_unidad(db_session, LineaNegocio.MOBILITY, "SSE Recta")
    stock_service.registrar_salida_venta(db_session, item, BODEGA, "STMB26-01")
    db_session.commit()

    assert item.ultimo_movimiento.tipo.value == "SALIDA"
    assert item.ultimo_movimiento.referencia_crp == "STMB26-01"


# Escenario 2 (E6-H2): intento de venta sin stock.
def test_reservar_unidad_sin_stock_lanza_error(db_session):
    stock_service.registrar_entrada(
        db_session, BODEGA, StockEntryCreate(linea_negocio=LineaNegocio.MOBILITY, tipo_producto="SSE Recta", cantidad=1)
    )
    stock_service.reservar_unidad(db_session, LineaNegocio.MOBILITY, "SSE Recta")
    db_session.commit()

    with pytest.raises(stock_service.NoStockError, match=stock_service.MENSAJE_SIN_STOCK):
        stock_service.reservar_unidad(db_session, LineaNegocio.MOBILITY, "SSE Recta")


def test_reservar_unidad_de_referencia_inexistente_lanza_error(db_session):
    with pytest.raises(stock_service.NoStockError):
        stock_service.reservar_unidad(db_session, LineaNegocio.MOBILITY, "No existe")
