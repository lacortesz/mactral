"""E5-H2: acta de entrega + estado ENTREGADO del proyecto

Revision ID: 0005_acta_entrega
Revises: 0004_instalacion
Create Date: 2026-07-17

"""
from alembic import op
import sqlalchemy as sa

revision = "0005_acta_entrega"
down_revision = "0004_instalacion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("installations", sa.Column("fecha_real_entrega", sa.Date(), nullable=True))
    op.add_column("installations", sa.Column("acta_bytes", sa.LargeBinary(), nullable=True))
    op.add_column("installations", sa.Column("acta_nombre", sa.String(length=255), nullable=True))
    op.add_column("installations", sa.Column("observaciones", sa.Text(), nullable=True))

    # Postgres 12+ permite ALTER TYPE ... ADD VALUE dentro de una
    # transacción siempre que el valor no se use en la misma transacción.
    op.execute("ALTER TYPE estado_etapa ADD VALUE IF NOT EXISTS 'ENTREGADO'")


def downgrade() -> None:
    # No se puede quitar un valor de un enum de Postgres sin recrear el
    # tipo; para el downgrade basta con dejar de usarlo (no se elimina).
    op.drop_column("installations", "observaciones")
    op.drop_column("installations", "acta_nombre")
    op.drop_column("installations", "acta_bytes")
    op.drop_column("installations", "fecha_real_entrega")
