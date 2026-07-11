"""E9-H2: bandeja de notificaciones por módulo (asignación e inactividad)

Revision ID: 0008_notificaciones
Revises: 0007_anticipo1_confirmacion
Create Date: 2026-07-20

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008_notificaciones"
down_revision = "0007_anticipo1_confirmacion"
branch_labels = None
depends_on = None

modulo_notificacion_enum = sa.Enum(
    "comercial", "reg-maestro", "importaciones", "tecnico", name="modulo_notificacion"
)


def upgrade() -> None:
    modulo_notificacion_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "notificaciones",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("project_id", sa.String(length=36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column(
            "modulo",
            postgresql.ENUM(
                "comercial", "reg-maestro", "importaciones", "tecnico",
                name="modulo_notificacion", create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("tipo", sa.String(length=32), nullable=False),
        sa.Column("mensaje", sa.Text(), nullable=False),
        sa.Column("fecha", sa.DateTime(), nullable=False),
        sa.Column("leida", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("notificaciones", "leida", server_default=None)


def downgrade() -> None:
    op.drop_table("notificaciones")
    modulo_notificacion_enum.drop(op.get_bind(), checkfirst=True)
