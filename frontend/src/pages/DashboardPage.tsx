import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ApiError, projectsApiFetch } from "../api/client";
import AppShell from "../components/AppShell";
import { useAuth } from "../context/AuthContext";
import { ESTADO_ETAPA_LABELS, MODULE_LABELS, ROLE_LABELS, moduleRoute, type EstadoEtapa } from "../domain";

type SemaforoConteo = { color: "VERDE" | "AMARILLO" | "ROJO"; cantidad: number };
type EtapaConteo = { etapa: EstadoEtapa; cantidad: number };
type ProyectoResumen = {
  id: string;
  crp_code: string;
  cliente: string;
  ciudad: string;
  etapa_actual: EstadoEtapa;
  semaforo_color: "VERDE" | "AMARILLO" | "ROJO";
};

type Dashboard = {
  total_activos: number;
  total_entregados: number;
  por_semaforo: SemaforoConteo[];
  por_etapa: EtapaConteo[];
  proyectos: ProyectoResumen[];
};

type RentabilidadProyecto = {
  crp_code: string;
  cliente: string;
  valor_contrato: number;
  costo_fabricacion: number;
  gastos_logisticos_cop: number;
  margen_bruto: number;
  margen_pct: number;
};

type Rentabilidad = {
  proyectos: RentabilidadProyecto[];
  margen_bruto_total: number;
  valor_contrato_total: number;
};

type KpisOperativos = {
  proyectos_gm_con_checklist_incompleto: number;
  instalaciones_programadas: number;
  instalaciones_completadas: number;
  notificaciones_asignacion_pendientes: number;
  notificaciones_inactividad_pendientes: number;
};

type KpisFinancieros = {
  total_cobrado_cop: number;
  total_por_cobrar_cop: number;
  total_gastos_logisticos_pendientes_cop: number;
  total_gastos_logisticos_pagados_cop: number;
  margen_bruto_total: number;
  valor_contrato_total: number;
};

const SEMAFORO_COLORS: Record<SemaforoConteo["color"], string> = {
  VERDE: "var(--mactral-green)",
  AMARILLO: "var(--mactral-yellow-dark)",
  ROJO: "var(--mactral-red)",
};

export default function DashboardPage() {
  const { user, token, accessibleModules } = useAuth();
  const [searchParams] = useSearchParams();
  const denied = searchParams.get("denied") === "1";

  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [dashboardError, setDashboardError] = useState<string | null>(null);

  const [rentabilidad, setRentabilidad] = useState<Rentabilidad | null>(null);
  const [kpisOperativos, setKpisOperativos] = useState<KpisOperativos | null>(null);
  const [kpisFinancieros, setKpisFinancieros] = useState<KpisFinancieros | null>(null);

  useEffect(() => {
    projectsApiFetch<Dashboard>("/reportes/dashboard", { token })
      .then(setDashboard)
      .catch((err) => setDashboardError(err instanceof ApiError ? err.message : "No se pudo cargar el dashboard"));

    if (user?.role === "GERENCIA") {
      projectsApiFetch<Rentabilidad>("/reportes/rentabilidad", { token })
        .then(setRentabilidad)
        .catch(() => null);
      projectsApiFetch<KpisOperativos>("/reportes/kpis-operativos", { token })
        .then(setKpisOperativos)
        .catch(() => null);
      projectsApiFetch<KpisFinancieros>("/reportes/kpis-financieros", { token })
        .then(setKpisFinancieros)
        .catch(() => null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <AppShell>
      <h1 className="page-title">Dashboard</h1>
      <p className="page-subtitle">
        {user && `${ROLE_LABELS[user.role]} · Módulos disponibles para tu rol`}
      </p>

      {denied && (
        // Escenario 3 (E1-H2): acceso a módulo no autorizado.
        <div className="alert alert-error">No tiene permisos para acceder a este módulo.</div>
      )}

      <div className="card">
        <h2 className="card-title">Módulos</h2>
        <div className="module-grid">
          {accessibleModules.map((m) => (
            <Link key={m} className="module-card" to={moduleRoute(m)}>
              {MODULE_LABELS[m]}
            </Link>
          ))}
        </div>
      </div>

      <div className="card">
        <h2 className="card-title">Proyectos activos</h2>
        {dashboardError && <div className="alert alert-error">{dashboardError}</div>}
        {dashboard && (
          <>
            <div className="form-grid" style={{ marginBottom: 16 }}>
              <div>
                <div style={{ fontSize: 12, color: "var(--mactral-text-muted)" }}>Activos</div>
                <div style={{ fontSize: 22, fontWeight: 700 }}>{dashboard.total_activos}</div>
              </div>
              <div>
                <div style={{ fontSize: 12, color: "var(--mactral-text-muted)" }}>Entregados</div>
                <div style={{ fontSize: 22, fontWeight: 700 }}>{dashboard.total_entregados}</div>
              </div>
              {dashboard.por_semaforo.map((s) => (
                <div key={s.color}>
                  <div style={{ fontSize: 12, color: "var(--mactral-text-muted)" }}>
                    Semáforo{" "}
                    <span style={{ color: SEMAFORO_COLORS[s.color], fontWeight: 700 }}>
                      {s.color === "VERDE" ? "Verde" : s.color === "AMARILLO" ? "Amarillo" : "Rojo"}
                    </span>
                  </div>
                  <div style={{ fontSize: 22, fontWeight: 700 }}>{s.cantidad}</div>
                </div>
              ))}
            </div>

            <table>
              <thead>
                <tr>
                  <th>Código CRP</th>
                  <th>Cliente</th>
                  <th>Ciudad</th>
                  <th>Etapa</th>
                  <th>Semáforo</th>
                </tr>
              </thead>
              <tbody>
                {dashboard.proyectos.map((p) => (
                  <tr key={p.id}>
                    <td>
                      <Link to="/reg-maestro">{p.crp_code}</Link>
                    </td>
                    <td>{p.cliente}</td>
                    <td>{p.ciudad}</td>
                    <td>{ESTADO_ETAPA_LABELS[p.etapa_actual]}</td>
                    <td>
                      <span style={{ color: SEMAFORO_COLORS[p.semaforo_color], fontWeight: 700 }}>
                        {p.semaforo_color === "VERDE" ? "Verde" : p.semaforo_color === "AMARILLO" ? "Amarillo" : "Rojo"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </div>

      {user?.role === "GERENCIA" && rentabilidad && (
        <div className="card">
          <h2 className="card-title">Rentabilidad por proyecto</h2>
          <div className="form-grid" style={{ marginBottom: 16 }}>
            <div>
              <div style={{ fontSize: 12, color: "var(--mactral-text-muted)" }}>Valor contrato total</div>
              <div style={{ fontSize: 22, fontWeight: 700 }}>
                ${rentabilidad.valor_contrato_total.toLocaleString("es-CO")}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 12, color: "var(--mactral-text-muted)" }}>Margen bruto total</div>
              <div style={{ fontSize: 22, fontWeight: 700 }}>
                ${rentabilidad.margen_bruto_total.toLocaleString("es-CO")}
              </div>
            </div>
          </div>
          {rentabilidad.proyectos.length === 0 ? (
            <p style={{ color: "var(--mactral-text-muted)", fontSize: 13 }}>
              Ningún proyecto tiene el esquema de pagos configurado todavía.
            </p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Código CRP</th>
                  <th>Cliente</th>
                  <th>Contrato</th>
                  <th>Fabricación</th>
                  <th>Logística</th>
                  <th>Margen bruto</th>
                  <th>Margen %</th>
                </tr>
              </thead>
              <tbody>
                {rentabilidad.proyectos.map((p) => (
                  <tr key={p.crp_code}>
                    <td>{p.crp_code}</td>
                    <td>{p.cliente}</td>
                    <td>${p.valor_contrato.toLocaleString("es-CO")}</td>
                    <td>${p.costo_fabricacion.toLocaleString("es-CO")}</td>
                    <td>${p.gastos_logisticos_cop.toLocaleString("es-CO")}</td>
                    <td>${p.margen_bruto.toLocaleString("es-CO")}</td>
                    <td>{p.margen_pct.toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {user?.role === "GERENCIA" && (kpisOperativos || kpisFinancieros) && (
        <div className="card">
          <h2 className="card-title">KPIs</h2>
          {kpisOperativos && (
            <>
              <h3 style={{ fontSize: 13, color: "var(--mactral-text-muted)", marginTop: 0 }}>Operativos</h3>
              <div className="form-grid" style={{ marginBottom: 20 }}>
                <div>
                  <div style={{ fontSize: 12, color: "var(--mactral-text-muted)" }}>GM con checklist incompleto</div>
                  <div style={{ fontSize: 22, fontWeight: 700 }}>
                    {kpisOperativos.proyectos_gm_con_checklist_incompleto}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 12, color: "var(--mactral-text-muted)" }}>Instalaciones programadas</div>
                  <div style={{ fontSize: 22, fontWeight: 700 }}>{kpisOperativos.instalaciones_programadas}</div>
                </div>
                <div>
                  <div style={{ fontSize: 12, color: "var(--mactral-text-muted)" }}>Instalaciones completadas</div>
                  <div style={{ fontSize: 22, fontWeight: 700 }}>{kpisOperativos.instalaciones_completadas}</div>
                </div>
                <div>
                  <div style={{ fontSize: 12, color: "var(--mactral-text-muted)" }}>Notificaciones de asignación</div>
                  <div style={{ fontSize: 22, fontWeight: 700 }}>
                    {kpisOperativos.notificaciones_asignacion_pendientes}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 12, color: "var(--mactral-text-muted)" }}>Alertas de inactividad</div>
                  <div style={{ fontSize: 22, fontWeight: 700 }}>
                    {kpisOperativos.notificaciones_inactividad_pendientes}
                  </div>
                </div>
              </div>
            </>
          )}

          {kpisFinancieros && (
            <>
              <h3 style={{ fontSize: 13, color: "var(--mactral-text-muted)" }}>Financieros</h3>
              <div className="form-grid">
                <div>
                  <div style={{ fontSize: 12, color: "var(--mactral-text-muted)" }}>Total cobrado</div>
                  <div style={{ fontSize: 22, fontWeight: 700 }}>
                    ${kpisFinancieros.total_cobrado_cop.toLocaleString("es-CO")}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 12, color: "var(--mactral-text-muted)" }}>Total por cobrar</div>
                  <div style={{ fontSize: 22, fontWeight: 700 }}>
                    ${kpisFinancieros.total_por_cobrar_cop.toLocaleString("es-CO")}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 12, color: "var(--mactral-text-muted)" }}>Gastos logísticos pendientes</div>
                  <div style={{ fontSize: 22, fontWeight: 700 }}>
                    ${kpisFinancieros.total_gastos_logisticos_pendientes_cop.toLocaleString("es-CO")}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 12, color: "var(--mactral-text-muted)" }}>Gastos logísticos pagados</div>
                  <div style={{ fontSize: 22, fontWeight: 700 }}>
                    ${kpisFinancieros.total_gastos_logisticos_pagados_cop.toLocaleString("es-CO")}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 12, color: "var(--mactral-text-muted)" }}>Margen bruto total</div>
                  <div style={{ fontSize: 22, fontWeight: 700 }}>
                    ${kpisFinancieros.margen_bruto_total.toLocaleString("es-CO")}
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </AppShell>
  );
}
