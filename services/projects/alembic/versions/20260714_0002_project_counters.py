"""E2-H4: consecutivo del Registro Maestro (GM/STMB/STIN)

Revision ID: 0002_project_counters
Revises: 0001_init
Create Date: 2026-07-14

"""
from alembic import op
import sqlalchemy as sa

revision = "0002_project_counters"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_counters",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("prefijo", sa.String(length=16), nullable=False),
        sa.Column("anio", sa.Integer(), nullable=False),
        sa.Column("ultimo_valor", sa.Integer(), nullable=False),
        sa.UniqueConstraint("prefijo", "anio", name="uq_project_counter"),
    )


def downgrade() -> None:
    op.drop_table("project_counters")
