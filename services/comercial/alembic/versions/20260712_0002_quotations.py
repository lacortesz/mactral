"""E2-H2: cotizaciones en PDF por lead

Revision ID: 0002_quotations
Revises: 0001_init
Create Date: 2026-07-12

"""
from alembic import op
import sqlalchemy as sa

revision = "0002_quotations"
down_revision = "0001_init"
branch_labels = None
depends_on = None

tipo_pago_enum = sa.Enum("CONTADO", "CREDITO", name="tipo_pago")


def upgrade() -> None:
    op.create_table(
        "quotations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("lead_id", sa.String(length=36), sa.ForeignKey("leads.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("valor_equipo", sa.Integer(), nullable=False),
        sa.Column("tipo_pago", tipo_pago_enum, nullable=False),
        sa.Column("anticipo_inicial_pct", sa.Integer(), nullable=False),
        sa.Column("segundo_anticipo_pct", sa.Integer(), nullable=False),
        sa.Column("saldo_final_pct", sa.Integer(), nullable=False),
        sa.Column("fecha_estimada_entrega", sa.Date(), nullable=False),
        sa.Column("pdf_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("lead_id", "version", name="uq_quotation_version"),
    )


def downgrade() -> None:
    op.drop_table("quotations")
    tipo_pago_enum.drop(op.get_bind(), checkfirst=True)
