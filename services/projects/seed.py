"""Crea proyectos de ejemplo (el CRP del mockup e1h3_e3h2_crp, entre otros)
si todavía no existen.

Uso: python seed.py
"""
from datetime import datetime

from sqlalchemy import select

from app.database import SessionLocal
from app.domain import EstadoEtapa, Modulo, SemaforoColor
from app.models import Project, ProjectEvent, ProjectModuleStatus


def _create_if_missing(db, crp_code, **kwargs) -> bool:
    existing = db.execute(select(Project).where(Project.crp_code == crp_code)).scalar_one_or_none()
    if existing:
        print(f"El proyecto {crp_code} ya existe, no se crea de nuevo.")
        return False

    project = Project(crp_code=crp_code, **kwargs)
    db.add(project)
    db.flush()
    return True


def main() -> None:
    db = SessionLocal()
    try:
        if _create_if_missing(
            db,
            "GM26-03",
            tipo="GM - Importación",
            cliente="Clínica San Pedro",
            ciudad="Medellín",
            producto="Silla SSE Curva",
            marca="Stannah",
            etapa_actual=EstadoEtapa.EN_CURSO,
            semaforo_color=SemaforoColor.AMARILLO,
            semaforo_detalle="En fecha",
        ):
            project = db.execute(
                select(Project).where(Project.crp_code == "GM26-03")
            ).scalar_one()

            db.add_all(
                [
                    ProjectModuleStatus(project_id=project.id, modulo=Modulo.COMERCIAL, estado=EstadoEtapa.CERRADO),
                    ProjectModuleStatus(project_id=project.id, modulo=Modulo.REG_MAESTRO, estado=EstadoEtapa.CERRADO),
                    ProjectModuleStatus(project_id=project.id, modulo=Modulo.IMPORTACIONES, estado=EstadoEtapa.EN_CURSO),
                    ProjectModuleStatus(project_id=project.id, modulo=Modulo.TECNICO, estado=EstadoEtapa.PENDIENTE),
                ]
            )
            db.add_all(
                [
                    ProjectEvent(
                        project_id=project.id,
                        fecha=datetime(2026, 6, 25, 9, 0),
                        origen="Comercial",
                        mensaje="Venta cerrada · lead MOB26-017 · $45M",
                    ),
                    ProjectEvent(
                        project_id=project.id,
                        fecha=datetime(2026, 6, 25, 9, 5),
                        origen="Sistema",
                        mensaje="Código GM26-03 generado automáticamente",
                    ),
                    ProjectEvent(
                        project_id=project.id,
                        fecha=datetime(2026, 7, 1, 10, 0),
                        origen="Financiero",
                        mensaje="Anticipo 1 recibido · $22.5M",
                    ),
                    ProjectEvent(
                        project_id=project.id,
                        fecha=datetime(2026, 7, 5, 11, 0),
                        origen="Importaciones",
                        mensaje="BL archivado → Anticipo 2 solicitado",
                    ),
                    ProjectEvent(
                        project_id=project.id,
                        fecha=datetime(2026, 7, 7, 15, 0),
                        origen="Financiero",
                        mensaje="Anticipo 2 confirmado · $13.5M",
                    ),
                ]
            )

        if _create_if_missing(
            db,
            "GM26-04",
            tipo="GM - Nacional",
            cliente="Constructora Bolívar",
            ciudad="Bogotá",
            producto="Plataforma Vertical",
            marca="Savaria",
            etapa_actual=EstadoEtapa.PENDIENTE,
            semaforo_color=SemaforoColor.VERDE,
            semaforo_detalle="En fecha",
        ):
            project = db.execute(
                select(Project).where(Project.crp_code == "GM26-04")
            ).scalar_one()
            db.add_all(
                [
                    ProjectModuleStatus(project_id=project.id, modulo=Modulo.COMERCIAL, estado=EstadoEtapa.CERRADO),
                    ProjectModuleStatus(project_id=project.id, modulo=Modulo.REG_MAESTRO, estado=EstadoEtapa.EN_CURSO),
                    ProjectModuleStatus(project_id=project.id, modulo=Modulo.IMPORTACIONES, estado=EstadoEtapa.PENDIENTE),
                    ProjectModuleStatus(project_id=project.id, modulo=Modulo.TECNICO, estado=EstadoEtapa.PENDIENTE),
                ]
            )
            db.add_all(
                [
                    ProjectEvent(
                        project_id=project.id,
                        fecha=datetime(2026, 7, 2, 9, 0),
                        origen="Comercial",
                        mensaje="Venta cerrada · lead MOB26-021 · $80M",
                    ),
                    ProjectEvent(
                        project_id=project.id,
                        fecha=datetime(2026, 7, 2, 9, 5),
                        origen="Sistema",
                        mensaje="Código GM26-04 generado automáticamente",
                    ),
                ]
            )

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
