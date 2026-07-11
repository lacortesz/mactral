"""E7-H5: confirmación manual de la solicitud de Anticipo 1

Revision ID: 0007_anticipo1_confirmacion
Revises: 0006_financiero
Create Date: 2026-07-19

"""
from alembic import op
import sqlalchemy as sa

revision = "0007_anticipo1_confirmacion"
down_revision = "0006_financiero"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("anticipo1_solicitud_confirmada", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("projects", "anticipo1_solicitud_confirmada", server_default=None)


def downgrade() -> None:
    op.drop_column("projects", "anticipo1_solicitud_confirmada")
