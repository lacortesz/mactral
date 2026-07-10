"""init: projects, estado por modulo y linea de tiempo

Revision ID: 0001_init
Revises:
Create Date: 2026-07-10

"""
from alembic import op
import sqlalchemy as sa

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None

# Sin create_type=False ni .create() manual: op.create_table ya emite el
# CREATE TYPE una sola vez al crear las columnas Enum (lección de la
# migración de services/auth: llamarlo a mano duplica la creación y falla
# con "type already exists").
estado_etapa_enum = sa.Enum(
    "PENDIENTE", "EN_CURSO", "CERRADO", "BLOQUEADO", name="estado_etapa"
)
semaforo_color_enum = sa.Enum("VERDE", "AMARILLO", "ROJO", name="semaforo_color")
estado_etapa_modulo_enum = sa.Enum(
    "PENDIENTE", "EN_CURSO", "CERRADO", "BLOQUEADO", name="estado_etapa_modulo"
)
modulo_enum = sa.Enum("comercial", "reg-maestro", "importaciones", "tecnico", name="modulo")


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("crp_code", sa.String(length=32), nullable=False),
        sa.Column("tipo", sa.String(length=255), nullable=False),
        sa.Column("cliente", sa.String(length=255), nullable=False),
        sa.Column("ciudad", sa.String(length=255), nullable=False),
        sa.Column("producto", sa.String(length=255), nullable=False),
        sa.Column("marca", sa.String(length=255), nullable=False),
        sa.Column("etapa_actual", estado_etapa_enum, nullable=False),
        sa.Column("semaforo_color", semaforo_color_enum, nullable=False),
        sa.Column("semaforo_detalle", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_projects_crp_code", "projects", ["crp_code"], unique=True)

    op.create_table(
        "project_module_status",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("project_id", sa.String(length=36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("modulo", modulo_enum, nullable=False),
        sa.Column("estado", estado_etapa_modulo_enum, nullable=False),
        sa.UniqueConstraint("project_id", "modulo", name="uq_project_modulo"),
    )

    op.create_table(
        "project_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("project_id", sa.String(length=36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("fecha", sa.DateTime(), nullable=False),
        sa.Column("origen", sa.String(length=64), nullable=False),
        sa.Column("mensaje", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("project_events")
    op.drop_table("project_module_status")
    op.drop_table("projects")
    estado_etapa_enum.drop(op.get_bind(), checkfirst=True)
    semaforo_color_enum.drop(op.get_bind(), checkfirst=True)
    estado_etapa_modulo_enum.drop(op.get_bind(), checkfirst=True)
    modulo_enum.drop(op.get_bind(), checkfirst=True)
