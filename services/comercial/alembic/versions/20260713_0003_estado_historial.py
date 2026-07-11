"""E2-H3/E2-H4: historial de cambios de estado y clasificación del lead

Revision ID: 0003_estado_historial
Revises: 0002_quotations
Create Date: 2026-07-13

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_estado_historial"
down_revision = "0002_quotations"
branch_labels = None
depends_on = None

# El tipo "estado_lead" ya existe (creado en 0001_init). sa.Enum(create_type=False)
# pierde la bandera al usarse dentro de create_table (falla con "type already
# exists"); postgresql.ENUM sí la respeta.
estado_lead_enum = postgresql.ENUM(
    "COTIZAR", "ENVIADA", "VENDIDO", name="estado_lead", create_type=False
)
tipo_clasificacion_enum = sa.Enum(
    "GM", "STOCK_MOBILITY", "STOCK_INDUSTRY", name="tipo_clasificacion"
)


def upgrade() -> None:
    # A diferencia de create_table, add_column no emite CREATE TYPE por su
    # cuenta: hay que crearlo explícitamente antes de usarlo en la columna.
    tipo_clasificacion_enum.create(op.get_bind(), checkfirst=True)
    op.add_column("leads", sa.Column("clasificacion", tipo_clasificacion_enum, nullable=True))

    op.create_table(
        "estado_historial",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("lead_id", sa.String(length=36), sa.ForeignKey("leads.id"), nullable=False),
        sa.Column("estado_anterior", estado_lead_enum, nullable=False),
        sa.Column("estado_nuevo", estado_lead_enum, nullable=False),
        sa.Column("usuario_id", sa.String(length=36), nullable=False),
        sa.Column("usuario_nombre", sa.String(length=255), nullable=False),
        sa.Column("fecha", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("estado_historial")
    op.drop_column("leads", "clasificacion")
    tipo_clasificacion_enum.drop(op.get_bind(), checkfirst=True)
