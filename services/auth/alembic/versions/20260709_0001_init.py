"""init: users table with roles, estado y bloqueo de sesion

Revision ID: 0001_init
Revises:
Create Date: 2026-07-09

"""
from alembic import op
import sqlalchemy as sa

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None

# Sin create_type=False ni .create() manual: op.create_table ya emite el
# CREATE TYPE una sola vez al crear las columnas Enum (la tabla es nueva,
# así que no hay riesgo de "type already exists" aquí).
rol_enum = sa.Enum(
    "COMERCIAL", "IMPORTACIONES", "TECNICO", "ADMINISTRATIVO", "GERENCIA", name="rol"
)
linea_negocio_enum = sa.Enum("MOBILITY", "INDUSTRY", "AMBAS", name="linea_negocio")
estado_usuario_enum = sa.Enum("ACTIVO", "INACTIVO", name="estado_usuario")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("role", rol_enum, nullable=False),
        sa.Column("linea_negocio", linea_negocio_enum, nullable=False),
        sa.Column("status", estado_usuario_enum, nullable=False, server_default="ACTIVO"),
        sa.Column("activation_token", sa.String(length=64), nullable=True),
        sa.Column("activation_token_expires_at", sa.DateTime(), nullable=True),
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(), nullable=True),
        sa.Column("last_access_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_unique_constraint("uq_users_activation_token", "users", ["activation_token"])


def downgrade() -> None:
    op.drop_table("users")
    rol_enum.drop(op.get_bind(), checkfirst=True)
    linea_negocio_enum.drop(op.get_bind(), checkfirst=True)
    estado_usuario_enum.drop(op.get_bind(), checkfirst=True)
