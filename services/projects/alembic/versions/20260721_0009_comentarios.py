"""E9-H3: comentarios por proyecto con menciones @usuario

Revision ID: 0009_comentarios
Revises: 0008_notificaciones
Create Date: 2026-07-21

"""
from alembic import op
import sqlalchemy as sa

revision = "0009_comentarios"
down_revision = "0008_notificaciones"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "comentarios",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("project_id", sa.String(length=36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("autor_id", sa.String(length=36), nullable=False),
        sa.Column("autor_nombre", sa.String(length=255), nullable=False),
        sa.Column("mensaje", sa.Text(), nullable=False),
        sa.Column("fecha", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("comentarios")
