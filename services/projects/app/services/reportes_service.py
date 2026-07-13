"""E10-H1/E10-H2: dashboard global de proyectos activos y vista gerencial
de rentabilidad por proyecto."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import EstadoCuentaPorPagar, EstadoCuota, EstadoEtapa, EstadoInstalacion, EstadoItemChecklist, SemaforoColor
from app.models import Installation, Notificacion, Project
from app.schemas import (
    DashboardOut,
    EtapaConteoOut,
    KpisFinancierosOut,
    KpisOperativosOut,
    ProjectSearchResult,
    RentabilidadOut,
    RentabilidadProyectoOut,
    SemaforoConteoOut,
)
from app.services.notificacion_service import TIPO_ASIGNACION, TIPO_INACTIVIDAD


def get_dashboard(db: Session) -> DashboardOut:
    proyectos = list(db.execute(select(Project).order_by(Project.crp_code)).scalars())

    total_entregados = sum(1 for p in proyectos if p.etapa_actual == EstadoEtapa.ENTREGADO)
    total_activos = len(proyectos) - total_entregados

    por_semaforo = {color: 0 for color in SemaforoColor}
    por_etapa = {etapa: 0 for etapa in EstadoEtapa}
    for p in proyectos:
        por_semaforo[p.semaforo_color] += 1
        por_etapa[p.etapa_actual] += 1

    return DashboardOut(
        total_activos=total_activos,
        total_entregados=total_entregados,
        por_semaforo=[SemaforoConteoOut(color=c, cantidad=n) for c, n in por_semaforo.items()],
        por_etapa=[EtapaConteoOut(etapa=e, cantidad=n) for e, n in por_etapa.items()],
        proyectos=[ProjectSearchResult.model_validate(p) for p in proyectos],
    )


def get_rentabilidad(db: Session) -> RentabilidadOut:
    proyectos = list(
        db.execute(select(Project).where(Project.valor_contrato.is_not(None)).order_by(Project.crp_code)).scalars()
    )

    filas = []
    for p in proyectos:
        gastos_logisticos_cop = sum(cxp.monto_cop for cxp in p.cuentas_por_pagar)
        margen_bruto = p.valor_contrato - p.costo_fabricacion - gastos_logisticos_cop
        margen_pct = (margen_bruto / p.valor_contrato * 100) if p.valor_contrato else 0.0
        filas.append(
            RentabilidadProyectoOut(
                crp_code=p.crp_code,
                cliente=p.cliente,
                valor_contrato=p.valor_contrato,
                costo_fabricacion=p.costo_fabricacion,
                gastos_logisticos_cop=gastos_logisticos_cop,
                margen_bruto=margen_bruto,
                margen_pct=margen_pct,
            )
        )

    return RentabilidadOut(
        proyectos=filas,
        margen_bruto_total=sum(f.margen_bruto for f in filas),
        valor_contrato_total=sum(f.valor_contrato for f in filas),
    )


def get_kpis_operativos(db: Session) -> KpisOperativosOut:
    proyectos = list(db.execute(select(Project)).scalars())
    checklist_incompleto = sum(
        1
        for p in proyectos
        if any(i.tipo.value == "REQUERIDO" and i.estado == EstadoItemChecklist.PENDIENTE for i in p.checklist_items)
    )

    instalaciones = list(db.execute(select(Installation)).scalars())
    instalaciones_programadas = sum(1 for i in instalaciones if i.estado == EstadoInstalacion.PROGRAMADO)
    instalaciones_completadas = sum(1 for i in instalaciones if i.estado == EstadoInstalacion.COMPLETADO)

    notificaciones = list(db.execute(select(Notificacion).where(Notificacion.leida.is_(False))).scalars())
    notif_asignacion = sum(1 for n in notificaciones if n.tipo == TIPO_ASIGNACION)
    notif_inactividad = sum(1 for n in notificaciones if n.tipo == TIPO_INACTIVIDAD)

    return KpisOperativosOut(
        proyectos_gm_con_checklist_incompleto=checklist_incompleto,
        instalaciones_programadas=instalaciones_programadas,
        instalaciones_completadas=instalaciones_completadas,
        notificaciones_asignacion_pendientes=notif_asignacion,
        notificaciones_inactividad_pendientes=notif_inactividad,
    )


def get_kpis_financieros(db: Session) -> KpisFinancierosOut:
    proyectos = list(db.execute(select(Project)).scalars())

    total_cobrado = 0
    total_por_cobrar = 0
    gastos_pendientes = 0.0
    gastos_pagados = 0.0
    margen_bruto_total = 0.0
    valor_contrato_total = 0

    for p in proyectos:
        for cuota in p.cuotas:
            if cuota.estado == EstadoCuota.PAGADO:
                total_cobrado += cuota.monto_pagado or 0
            else:
                total_por_cobrar += cuota.monto

        for cxp in p.cuentas_por_pagar:
            if cxp.estado == EstadoCuentaPorPagar.PAGADA:
                gastos_pagados += cxp.monto_cop
            else:
                gastos_pendientes += cxp.monto_cop

        if p.valor_contrato is not None:
            valor_contrato_total += p.valor_contrato
            gastos_logisticos_cop = sum(cxp.monto_cop for cxp in p.cuentas_por_pagar)
            margen_bruto_total += p.valor_contrato - p.costo_fabricacion - gastos_logisticos_cop

    return KpisFinancierosOut(
        total_cobrado_cop=total_cobrado,
        total_por_cobrar_cop=total_por_cobrar,
        total_gastos_logisticos_pendientes_cop=gastos_pendientes,
        total_gastos_logisticos_pagados_cop=gastos_pagados,
        margen_bruto_total=margen_bruto_total,
        valor_contrato_total=valor_contrato_total,
    )
