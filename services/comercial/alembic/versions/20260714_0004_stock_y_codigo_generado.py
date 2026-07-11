"""E2-H4: stock disponible y código del Registro Maestro por lead

Revision ID: 0004_stock_codigo_generado
Revises: 0003_estado_historial
Create Date: 2026-07-14

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_stock_codigo_generado"
down_revision = "0003_estado_historial"
branch_labels = None
depends_on = None

# El tipo "linea_negocio_comercial" ya existe (creado en 0001_init).
linea_negocio_enum = postgresql.ENUM(
    "MOBILITY", "INDUSTRY", name="linea_negocio_comercial", create_type=False
)


def upgrade() -> None:
    op.add_column("leads", sa.Column("codigo_generado", sa.String(length=32), nullable=True))

    op.create_table(
        "stock_items",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("linea_negocio", linea_negocio_enum, nullable=False),
        sa.Column("tipo_producto", sa.String(length=255), nullable=False),
        sa.Column("cantidad_disponible", sa.Integer(), nullable=False),
        sa.UniqueConstraint("linea_negocio", "tipo_producto", name="uq_stock_item"),
    )


def downgrade() -> None:
    op.drop_table("stock_items")
    op.drop_column("leads", "codigo_generado")
