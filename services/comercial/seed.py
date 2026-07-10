"""Crea leads de ejemplo (los del mockup e2h1_e2h3_leads) si no existen.

Uso: python seed.py
"""
from datetime import datetime

from sqlalchemy import select

from app.database import SessionLocal
from app.domain import EstadoLead, LineaNegocio
from app.models import Lead, LeadCounter


SEED_LEADS = [
    dict(
        codigo="MOB26-018",
        nombre="Residencias El Pinar",
        telefono="3001234567",
        ciudad="Pereira",
        canal_entrada="Sitio web",
        linea_negocio=LineaNegocio.MOBILITY,
        tipo_producto="SSE Recta",
        marca="Stannah",
        estado=EstadoLead.COTIZAR,
        vendedor_id="seed-carlos",
        vendedor_nombre="Carlos Martínez",
        created_at=datetime(2026, 7, 3, 10, 0),
    ),
    dict(
        codigo="MOB26-017",
        nombre="Gustavo Ramírez",
        correo="gustavo.ramirez@example.com",
        ciudad="Bogotá",
        canal_entrada="Referido",
        linea_negocio=LineaNegocio.MOBILITY,
        tipo_producto="SSE Curva",
        marca="Stannah",
        estado=EstadoLead.ENVIADA,
        vendedor_id="seed-maria",
        vendedor_nombre="María Angulo",
        created_at=datetime(2026, 7, 1, 9, 0),
    ),
    dict(
        codigo="IND26-006",
        nombre="Almacenes Éxito",
        telefono="6042345678",
        ciudad="Medellín",
        canal_entrada="Feria comercial",
        linea_negocio=LineaNegocio.INDUSTRY,
        tipo_producto="Montacargas",
        marca="Savaria",
        estado=EstadoLead.VENDIDO,
        vendedor_id="seed-carla",
        vendedor_nombre="Carla Andrade",
        created_at=datetime(2026, 6, 28, 11, 0),
    ),
    dict(
        codigo="MOB26-016",
        nombre="Hospital San Ignacio",
        correo="compras@hospitalsi.example.com",
        ciudad="Bogotá",
        canal_entrada="Sitio web",
        linea_negocio=LineaNegocio.MOBILITY,
        tipo_producto="Plataforma",
        marca="Savaria",
        estado=EstadoLead.ENVIADA,
        vendedor_id="seed-carlos",
        vendedor_nombre="Carlos Martínez",
        created_at=datetime(2026, 6, 25, 14, 0),
    ),
    dict(
        codigo="IND26-005",
        nombre="Coltejer S.A.",
        telefono="6043456789",
        ciudad="Itagüí",
        canal_entrada="Referido",
        linea_negocio=LineaNegocio.INDUSTRY,
        tipo_producto="Carretilla",
        marca="Stannah",
        estado=EstadoLead.COTIZAR,
        vendedor_id="seed-carla",
        vendedor_nombre="Carla Andrade",
        created_at=datetime(2026, 6, 20, 8, 30),
    ),
]


def main() -> None:
    db = SessionLocal()
    try:
        for data in SEED_LEADS:
            existing = db.execute(select(Lead).where(Lead.codigo == data["codigo"])).scalar_one_or_none()
            if existing:
                print(f"El lead {data['codigo']} ya existe, no se crea de nuevo.")
                continue
            db.add(Lead(**data))
            print(f"Lead creado: {data['codigo']} — {data['nombre']}")

        # Sincronizar los contadores para que el próximo alta no choque con
        # los códigos de ejemplo ya sembrados manualmente.
        for linea, seeded_max in [(LineaNegocio.MOBILITY, 18), (LineaNegocio.INDUSTRY, 6)]:
            counter = db.execute(
                select(LeadCounter).where(LeadCounter.linea_negocio == linea, LeadCounter.anio == 2026)
            ).scalar_one_or_none()
            if counter is None:
                db.add(LeadCounter(linea_negocio=linea, anio=2026, ultimo_valor=seeded_max))
            elif counter.ultimo_valor < seeded_max:
                counter.ultimo_valor = seeded_max

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
