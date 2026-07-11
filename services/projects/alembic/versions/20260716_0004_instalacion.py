"""E5-H1: instalación programada y reprogramaciones (módulo Técnico)

Revision ID: 0004_instalacion
Revises: 0003_checklist_importacion
Create Date: 2026-07-16

"""
from alembic import op
import sqlalchemy as sa

revision = "0004_instalacion"
down_revision = "0003_checklist_importacion"
branch_labels = None
depends_on = None

estado_instalacion_enum = sa.Enum("PROGRAMADO", "COMPLETADO", name="estado_instalacion")


def upgrade() -> None:
    op.create_table(
        "installations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("project_id", sa.String(length=36), sa.ForeignKey("projects.id"), nullable=False, unique=True),
        sa.Column("fecha_instalacion", sa.Date(), nullable=False),
        sa.Column("tecnico_id", sa.String(length=36), nullable=False),
        sa.Column("tecnico_nombre", sa.String(length=255), nullable=False),
        sa.Column("ciudad", sa.String(length=255), nullable=False),
        sa.Column("estado", estado_instalacion_enum, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "installation_reprogrammings",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("installation_id", sa.String(length=36), sa.ForeignKey("installations.id"), nullable=False),
        sa.Column("fecha_anterior", sa.Date(), nullable=False),
        sa.Column("fecha_nueva", sa.Date(), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column("usuario_id", sa.String(length=36), nullable=False),
        sa.Column("usuario_nombre", sa.String(length=255), nullable=False),
        sa.Column("fecha_cambio", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("installation_reprogrammings")
    op.drop_table("installations")
    estado_instalacion_enum.drop(op.get_bind(), checkfirst=True)
