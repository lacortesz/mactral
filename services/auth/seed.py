"""Crea el usuario Gerencia/Administrador inicial si no existe.

Uso: python seed.py
"""
import os

from sqlalchemy import select

from app.database import SessionLocal
from app.domain import EstadoUsuario, LineaNegocio, Rol
from app.models import User
from app.security import hash_password


def main() -> None:
    email = os.environ.get("SEED_ADMIN_EMAIL", "maya@grupomactral.com")
    password = os.environ.get("SEED_ADMIN_PASSWORD", "Mactral2026!")

    db = SessionLocal()
    try:
        existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if existing:
            print(f"El usuario administrador {email} ya existe, no se crea de nuevo.")
            return

        user = User(
            name="Maya Lozada",
            email=email,
            password_hash=hash_password(password),
            role=Rol.GERENCIA,
            linea_negocio=LineaNegocio.AMBAS,
            status=EstadoUsuario.ACTIVO,
        )
        db.add(user)
        db.commit()
        print(f"Usuario administrador creado: {email} / {password}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
