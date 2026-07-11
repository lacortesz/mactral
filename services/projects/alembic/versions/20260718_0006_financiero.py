"""E7-H1/E7-H3/E8-H1: cuotas, cuentas por pagar y campos financieros del proyecto

Revision ID: 0006_financiero
Revises: 0005_acta_entrega
Create Date: 2026-07-18

"""
from alembic import op
import sqlalchemy as sa

revision = "0006_financiero"
down_revision = "0005_acta_entrega"
branch_labels = None
depends_on = None

estado_cuota_enum = sa.Enum("PENDIENTE", "PAGADO", name="estado_cuota")
tipo_gasto_logistico_enum = sa.Enum(
    "VUELO", "HOSPEDAJE", "TRANSPORTE", "VIATICOS", "OTRO", name="tipo_gasto_logistico"
)
estado_cxp_enum = sa.Enum("PENDIENTE", "PAGADA", name="estado_cuenta_por_pagar")


def upgrade() -> None:
    op.add_column("projects", sa.Column("valor_contrato", sa.Integer(), nullable=True))
    op.add_column(
        "projects", sa.Column("costo_fabricacion", sa.Integer(), nullable=False, server_default="0")
    )
    op.alter_column("projects", "costo_fabricacion", server_default=None)
    op.add_column("projects", sa.Column("planos_aprobados_fecha", sa.DateTime(), nullable=True))

    op.create_table(
        "cuotas",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("project_id", sa.String(length=36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("etiqueta", sa.String(length=64), nullable=False),
        sa.Column("monto", sa.Integer(), nullable=False),
        sa.Column("porcentaje", sa.Integer(), nullable=False),
        sa.Column("fecha_vencimiento", sa.Date(), nullable=False),
        sa.Column("estado", estado_cuota_enum, nullable=False),
        sa.Column("fecha_pago", sa.Date(), nullable=True),
        sa.Column("monto_pagado", sa.Integer(), nullable=True),
        sa.Column("referencia_bancaria", sa.String(length=255), nullable=True),
        sa.Column("comprobante_bytes", sa.LargeBinary(), nullable=True),
        sa.Column("comprobante_nombre", sa.String(length=255), nullable=True),
        sa.Column("alertada_proxima", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("alertada_vencida", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("project_id", "numero", name="uq_cuota_numero"),
    )
    op.alter_column("cuotas", "alertada_proxima", server_default=None)
    op.alter_column("cuotas", "alertada_vencida", server_default=None)

    op.create_table(
        "cuentas_por_pagar",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("project_id", sa.String(length=36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("tipo", tipo_gasto_logistico_enum, nullable=False),
        sa.Column("proveedor", sa.String(length=255), nullable=False),
        sa.Column("concepto", sa.String(length=255), nullable=False),
        sa.Column("monto", sa.Integer(), nullable=False),
        sa.Column("moneda", sa.String(length=8), nullable=False, server_default="COP"),
        sa.Column("tasa_cop", sa.Float(), nullable=True),
        sa.Column("fecha_vencimiento", sa.Date(), nullable=False),
        sa.Column("estado", estado_cxp_enum, nullable=False),
        sa.Column("fecha_pago", sa.Date(), nullable=True),
        sa.Column("soporte_bytes", sa.LargeBinary(), nullable=True),
        sa.Column("soporte_nombre", sa.String(length=255), nullable=True),
        sa.Column("autorizado_gg", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.alter_column("cuentas_por_pagar", "moneda", server_default=None)
    op.alter_column("cuentas_por_pagar", "autorizado_gg", server_default=None)


def downgrade() -> None:
    op.drop_table("cuentas_por_pagar")
    op.drop_table("cuotas")
    op.drop_column("projects", "planos_aprobados_fecha")
    op.drop_column("projects", "costo_fabricacion")
    op.drop_column("projects", "valor_contrato")
    estado_cxp_enum.drop(op.get_bind(), checkfirst=True)
    tipo_gasto_logistico_enum.drop(op.get_bind(), checkfirst=True)
    estado_cuota_enum.drop(op.get_bind(), checkfirst=True)
