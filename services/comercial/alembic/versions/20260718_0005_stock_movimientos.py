"""E6-H1: entradas/salidas de inventario y nuevos campos de referencia

Revision ID: 0005_stock_movimientos
Revises: 0004_stock_codigo_generado
Create Date: 2026-07-18

"""
from alembic import op
import sqlalchemy as sa

revision = "0005_stock_movimientos"
down_revision = "0004_stock_codigo_generado"
branch_labels = None
depends_on = None

tipo_movimiento_stock_enum = sa.Enum("ENTRADA", "SALIDA", name="tipo_movimiento_stock")


def upgrade() -> None:
    op.add_column("stock_items", sa.Column("nombre", sa.String(length=255), nullable=True))
    op.add_column("stock_items", sa.Column("descripcion", sa.Text(), nullable=True))
    op.add_column("stock_items", sa.Column("color", sa.String(length=64), nullable=True))
    op.add_column(
        "stock_items", sa.Column("unidad", sa.String(length=32), nullable=False, server_default="unidad")
    )
    op.alter_column("stock_items", "unidad", server_default=None)
    op.add_column(
        "stock_items", sa.Column("cantidad_total", sa.Integer(), nullable=False, server_default="0")
    )
    op.alter_column("stock_items", "cantidad_total", server_default=None)
    # Sincroniza el total con lo ya disponible para los ítems sembrados
    # antes de esta migración (E2-H4).
    op.execute("UPDATE stock_items SET cantidad_total = cantidad_disponible")

    op.create_table(
        "stock_movements",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("stock_item_id", sa.String(length=36), sa.ForeignKey("stock_items.id"), nullable=False),
        sa.Column("tipo", tipo_movimiento_stock_enum, nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.Column("fecha", sa.DateTime(), nullable=False),
        sa.Column("usuario_id", sa.String(length=36), nullable=False),
        sa.Column("usuario_nombre", sa.String(length=255), nullable=False),
        sa.Column("referencia_crp", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("stock_movements")
    op.drop_column("stock_items", "cantidad_total")
    op.drop_column("stock_items", "unidad")
    op.drop_column("stock_items", "color")
    op.drop_column("stock_items", "descripcion")
    op.drop_column("stock_items", "nombre")
    tipo_movimiento_stock_enum.drop(op.get_bind(), checkfirst=True)
