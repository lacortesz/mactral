"""E7-H1: definición de cuotas/anticipos y registro de pagos por proyecto."""
from datetime import date, datetime, timedelta
from typing import Protocol

from sqlalchemy.orm import Session

from app.domain import (
    TASAS_CAMBIO_REFERENCIA,
    EstadoCuentaPorPagar,
    EstadoCuota,
    Rol,
    calcular_semaforo_pago,
    can_manage_financiero,
)
from app.models import CuentaPorPagar, Cuota, Project, ProjectEvent
from app.schemas import (
    CuentaPorPagarOut,
    CuentasPorPagarConsolidadoOut,
    CuotaPagoCreate,
    CuotasConfigCreate,
    TableroFinancieroOut,
    TasaCambioOut,
)
from app.services.project_service import ForbiddenError, get_project_by_code


class Actor(Protocol):
    id: str
    name: str
    role: Rol


class CuotaNotFoundError(Exception):
    pass


class CuotasYaConfiguradasError(Exception):
    pass


class PlanosNoAprobadosError(Exception):
    pass


class SolicitudYaConfirmadaError(Exception):
    pass


def evaluar_alertas_cuotas(db: Session, project: Project) -> None:
    """E7-H4: alerta de cuotas próximas a vencer (7 días) o ya vencidas.
    Se evalúa en cada lectura del proyecto (no hay job diario corriendo
    aparte, mismo patrón que el semáforo de entrega de E5-H3) y usa los
    flags alertada_proxima/alertada_vencida para no duplicar el evento."""
    hoy = date.today()
    cambios = False
    for cuota in project.cuotas:
        if cuota.estado != EstadoCuota.PENDIENTE:
            continue
        if cuota.fecha_vencimiento < hoy and not cuota.alertada_vencida:
            cuota.alertada_vencida = True
            db.add(
                ProjectEvent(
                    project_id=project.id,
                    fecha=datetime.utcnow(),
                    origen="Financiero",
                    mensaje=f"Alerta: {cuota.etiqueta} vencida (venció el {cuota.fecha_vencimiento.isoformat()})",
                )
            )
            cambios = True
        elif cuota.fecha_vencimiento <= hoy + timedelta(days=7) and not cuota.alertada_proxima:
            cuota.alertada_proxima = True
            db.add(
                ProjectEvent(
                    project_id=project.id,
                    fecha=datetime.utcnow(),
                    origen="Financiero",
                    mensaje=f"Alerta: {cuota.etiqueta} vence el {cuota.fecha_vencimiento.isoformat()}",
                )
            )
            cambios = True

    if cambios:
        db.commit()
        db.refresh(project)


def list_cuotas(db: Session, crp_code: str) -> list[Cuota]:
    project = get_project_by_code(db, crp_code)
    evaluar_alertas_cuotas(db, project)
    return project.cuotas


def configurar_cuotas(db: Session, actor: Actor, crp_code: str, data: CuotasConfigCreate) -> Project:
    if not can_manage_financiero(actor.role):
        raise ForbiddenError("Solo Administrativo (Financiero) o Gerencia pueden configurar las cuotas.")

    project = get_project_by_code(db, crp_code)
    if project.cuotas:
        raise CuotasYaConfiguradasError(
            "Este proyecto ya tiene cuotas configuradas; el valor del contrato requiere aprobación de "
            "Gerencia para modificarse."
        )

    project.valor_contrato = data.valor_contrato
    project.costo_fabricacion = data.costo_fabricacion

    for cuota_in in data.cuotas:
        db.add(
            Cuota(
                project_id=project.id,
                numero=cuota_in.numero,
                etiqueta=cuota_in.etiqueta,
                monto=cuota_in.monto,
                porcentaje=cuota_in.porcentaje,
                fecha_vencimiento=cuota_in.fecha_vencimiento,
                estado=EstadoCuota.PENDIENTE,
            )
        )

    db.add(
        ProjectEvent(
            project_id=project.id,
            fecha=datetime.utcnow(),
            origen="Financiero",
            mensaje=f"Esquema de pagos configurado · {len(data.cuotas)} cuota(s) · contrato ${data.valor_contrato:,.0f}".replace(
                ",", "."
            ),
        )
    )

    db.commit()
    db.refresh(project)
    return project


def registrar_pago(db: Session, actor: Actor, crp_code: str, numero: int, data: CuotaPagoCreate) -> Cuota:
    if not can_manage_financiero(actor.role):
        raise ForbiddenError("Solo Administrativo (Financiero) o Gerencia pueden registrar pagos.")

    project = get_project_by_code(db, crp_code)
    cuota = next((c for c in project.cuotas if c.numero == numero), None)
    if cuota is None:
        raise CuotaNotFoundError(f"La cuota {numero} no existe en este proyecto")

    cuota.estado = EstadoCuota.PAGADO
    cuota.fecha_pago = data.fecha_pago
    cuota.monto_pagado = data.monto_pagado
    cuota.referencia_bancaria = data.referencia_bancaria

    db.add(
        ProjectEvent(
            project_id=project.id,
            fecha=datetime.utcnow(),
            origen="Financiero",
            mensaje=f"{cuota.etiqueta} recibido · ${data.monto_pagado:,.0f}".replace(",", "."),
        )
    )

    db.commit()
    db.refresh(cuota)
    return cuota


def confirmar_solicitud_anticipo1(db: Session, actor: Actor, crp_code: str) -> Project:
    """E7-H5: confirmación manual del Administrador de que la solicitud de
    Anticipo 1 (disparada automáticamente al aprobarse los planos) ya fue
    enviada al cliente. Se registra en la línea de tiempo una sola vez."""
    if not can_manage_financiero(actor.role):
        raise ForbiddenError("Solo Administrativo (Financiero) o Gerencia pueden confirmar la solicitud.")

    project = get_project_by_code(db, crp_code)
    if project.planos_aprobados_fecha is None:
        raise PlanosNoAprobadosError("Los planos de este proyecto aún no han sido aprobados.")
    if project.anticipo1_solicitud_confirmada:
        raise SolicitudYaConfirmadaError("La solicitud de Anticipo 1 ya fue confirmada.")

    project.anticipo1_solicitud_confirmada = True
    db.add(
        ProjectEvent(
            project_id=project.id,
            fecha=datetime.utcnow(),
            origen="Financiero",
            mensaje=f"Anticipo 1 solicitado al cliente — confirmado por {actor.name}",
        )
    )
    db.commit()
    db.refresh(project)
    return project


def get_tablero(db: Session, crp_code: str) -> TableroFinancieroOut:
    """E7-H2: valor del contrato, desglose de cuotas, costos ya modelados
    (fabricación + gastos logísticos de E8-H1/E7-H3) y margen bruto."""
    project = get_project_by_code(db, crp_code)
    evaluar_alertas_cuotas(db, project)

    total_cobrado = sum(c.monto_pagado or 0 for c in project.cuotas if c.estado == EstadoCuota.PAGADO)
    total_por_cobrar = sum(c.monto for c in project.cuotas if c.estado == EstadoCuota.PENDIENTE)
    total_gastos_logisticos_cop = sum(cxp.monto_cop for cxp in project.cuentas_por_pagar)

    margen_bruto = None
    if project.valor_contrato is not None:
        margen_bruto = project.valor_contrato - project.costo_fabricacion - total_gastos_logisticos_cop

    return TableroFinancieroOut(
        crp_code=project.crp_code,
        valor_contrato=project.valor_contrato,
        costo_fabricacion=project.costo_fabricacion,
        total_cobrado=total_cobrado,
        total_por_cobrar=total_por_cobrar,
        total_gastos_logisticos_cop=total_gastos_logisticos_cop,
        margen_bruto=margen_bruto,
        semaforo_pago=calcular_semaforo_pago(project.cuotas),
        cuotas=project.cuotas,
        tasas_cambio=[TasaCambioOut(moneda=m, tasa_cop=t) for m, t in TASAS_CAMBIO_REFERENCIA.items()],
        planos_aprobados_fecha=project.planos_aprobados_fecha,
        anticipo1_solicitud_confirmada=project.anticipo1_solicitud_confirmada,
    )


def list_cuentas_por_pagar(
    db: Session,
    actor: Actor,
    proveedor: str | None = None,
    crp_code: str | None = None,
    moneda: str | None = None,
    estado: EstadoCuentaPorPagar | None = None,
) -> CuentasPorPagarConsolidadoOut:
    """E7-H3: tablero consolidado de CxP de todos los proyectos, con filtros
    de proveedor/proyecto/moneda/estado."""
    if not can_manage_financiero(actor.role):
        raise ForbiddenError("Solo Administrativo (Financiero) o Gerencia pueden ver el tablero de CxP.")

    query = db.query(CuentaPorPagar).join(Project, CuentaPorPagar.project_id == Project.id)
    if proveedor:
        query = query.filter(CuentaPorPagar.proveedor.ilike(f"%{proveedor}%"))
    if crp_code:
        query = query.filter(Project.crp_code == crp_code)
    if moneda:
        query = query.filter(CuentaPorPagar.moneda == moneda)
    if estado:
        query = query.filter(CuentaPorPagar.estado == estado)
    query = query.order_by(CuentaPorPagar.fecha_vencimiento)

    rows = query.all()
    items = [
        CuentaPorPagarOut(
            id=cxp.id,
            crp_code=cxp.project.crp_code,
            tipo=cxp.tipo,
            proveedor=cxp.proveedor,
            concepto=cxp.concepto,
            monto=cxp.monto,
            moneda=cxp.moneda,
            tasa_cop=cxp.tasa_cop,
            monto_cop=cxp.monto_cop,
            fecha_vencimiento=cxp.fecha_vencimiento,
            estado=cxp.estado,
            fecha_pago=cxp.fecha_pago,
            tiene_soporte=cxp.tiene_soporte,
            autorizado_gg=cxp.autorizado_gg,
        )
        for cxp in rows
    ]

    return CuentasPorPagarConsolidadoOut(
        items=items,
        total_pendiente_cop=sum(i.monto_cop for i in items if i.estado == EstadoCuentaPorPagar.PENDIENTE),
        total_pagado_cop=sum(i.monto_cop for i in items if i.estado == EstadoCuentaPorPagar.PAGADA),
    )
