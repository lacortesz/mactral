"""init: leads, interacciones y contador de consecutivos

Revision ID: 0001_init
Revises:
Create Date: 2026-07-11

"""
from alembic import op
import sqlalchemy as sa

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None

# Sin create_type=False ni .create() manual: op.create_table ya emite el
# CREATE TYPE una sola vez al crear las columnas Enum (lección de la
# migración de services/projects: llamarlo a mano duplica la creación y
# falla con "type already exists").
linea_negocio_enum = sa.Enum("MOBILITY", "INDUSTRY", name="linea_negocio_comercial")
estado_lead_enum = sa.Enum("COTIZAR", "ENVIADA", "VENDIDO", name="estado_lead")


def upgrade() -> None:
    op.create_table(
        "lead_counters",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("linea_negocio", linea_negocio_enum, nullable=False),
        sa.Column("anio", sa.Integer(), nullable=False),
        sa.Column("ultimo_valor", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("linea_negocio", "anio", name="uq_lead_counter"),
    )

    op.create_table(
        "leads",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("codigo", sa.String(length=32), nullable=False),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column("telefono", sa.String(length=64), nullable=True),
        sa.Column("correo", sa.String(length=255), nullable=True),
        sa.Column("ciudad", sa.String(length=255), nullable=False),
        sa.Column("canal_entrada", sa.String(length=64), nullable=False),
        sa.Column("linea_negocio", linea_negocio_enum, nullable=False),
        sa.Column("tipo_producto", sa.String(length=255), nullable=False),
        sa.Column("marca", sa.String(length=255), nullable=False),
        sa.Column("estado", estado_lead_enum, nullable=False, server_default="COTIZAR"),
        sa.Column("vendedor_id", sa.String(length=36), nullable=False),
        sa.Column("vendedor_nombre", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_leads_codigo", "leads", ["codigo"], unique=True)

    op.create_table(
        "lead_interactions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("lead_id", sa.String(length=36), sa.ForeignKey("leads.id"), nullable=False),
        sa.Column("fecha", sa.DateTime(), nullable=False),
        sa.Column("canal", sa.String(length=64), nullable=False),
        sa.Column("resumen", sa.Text(), nullable=False),
        sa.Column("usuario_id", sa.String(length=36), nullable=False),
        sa.Column("usuario_nombre", sa.String(length=255), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("lead_interactions")
    op.drop_table("leads")
    op.drop_table("lead_counters")
    linea_negocio_enum.drop(op.get_bind(), checkfirst=True)
    estado_lead_enum.drop(op.get_bind(), checkfirst=True)
