"""E4-H1: checklist documental de importación + campos de ingreso a bodega

Revision ID: 0003_checklist_importacion
Revises: 0002_project_counters
Create Date: 2026-07-15

"""
from alembic import op
import sqlalchemy as sa

revision = "0003_checklist_importacion"
down_revision = "0002_project_counters"
branch_labels = None
depends_on = None

tipo_item_checklist_enum = sa.Enum("REQUERIDO", "OPCIONAL", name="tipo_item_checklist")
estado_item_checklist_enum = sa.Enum("PENDIENTE", "ARCHIVADO", "NO_APLICA", name="estado_item_checklist")


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("notificado_anticipo2", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("projects", "notificado_anticipo2", server_default=None)
    op.add_column("projects", sa.Column("ingreso_bodega_fecha", sa.DateTime(), nullable=True))
    op.add_column("projects", sa.Column("ingreso_bodega_nota", sa.Text(), nullable=True))

    op.create_table(
        "import_checklist_items",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("project_id", sa.String(length=36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("numero", sa.String(length=8), nullable=False),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column("tipo", tipo_item_checklist_enum, nullable=False),
        sa.Column("estado", estado_item_checklist_enum, nullable=False),
        sa.Column("fecha", sa.DateTime(), nullable=True),
        sa.Column("nota", sa.Text(), nullable=True),
        sa.Column("adjunto_bytes", sa.LargeBinary(), nullable=True),
        sa.Column("adjunto_nombre", sa.String(length=255), nullable=True),
        sa.UniqueConstraint("project_id", "numero", name="uq_checklist_item"),
    )


def downgrade() -> None:
    op.drop_table("import_checklist_items")
    op.drop_column("projects", "ingreso_bodega_nota")
    op.drop_column("projects", "ingreso_bodega_fecha")
    op.drop_column("projects", "notificado_anticipo2")
    tipo_item_checklist_enum.drop(op.get_bind(), checkfirst=True)
    estado_item_checklist_enum.drop(op.get_bind(), checkfirst=True)
