import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, projectsApiFetch } from "../api/client";
import AppShell from "../components/AppShell";
import { useAuth } from "../context/AuthContext";

type SearchResult = {
  id: string;
  crp_code: string;
  cliente: string;
  ciudad: string;
};

type Cuota = {
  numero: number;
  etiqueta: string;
  monto: number;
  porcentaje: number;
  fecha_vencimiento: string;
  estado: "PENDIENTE" | "PAGADO";
  fecha_pago: string | null;
  monto_pagado: number | null;
  referencia_bancaria: string | null;
};

type ProjectDetail = {
  crp_code: string;
  cliente: string;
};

type TasaCambio = { moneda: string; tasa_cop: number };

type Tablero = {
  valor_contrato: number | null;
  costo_fabricacion: number;
  total_cobrado: number;
  total_por_cobrar: number;
  total_gastos_logisticos_cop: number;
  margen_bruto: number | null;
  semaforo_pago: "VERDE" | "AMARILLO" | "ROJO";
  tasas_cambio: TasaCambio[];
};

const SEMAFORO_LABELS: Record<Tablero["semaforo_pago"], string> = {
  VERDE: "Al día",
  AMARILLO: "Por vencer",
  ROJO: "Vencida",
};

const SEMAFORO_CLASSES: Record<Tablero["semaforo_pago"], string> = {
  VERDE: "badge-status-activo",
  AMARILLO: "badge-role",
  ROJO: "badge-status-inactivo",
};

type CuentaPorPagar = {
  id: string;
  crp_code: string;
  tipo: string;
  proveedor: string;
  concepto: string;
  monto: number;
  moneda: string;
  monto_cop: number;
  fecha_vencimiento: string;
  estado: "PENDIENTE" | "PAGADA";
  autorizado_gg: boolean;
};

type CxpConsolidado = {
  items: CuentaPorPagar[];
  total_pendiente_cop: number;
  total_pagado_cop: number;
};

const EMPTY_CUOTA = { etiqueta: "", monto: "", porcentaje: "", fecha_vencimiento: "" };

export default function FinancieroPage() {
  const { token, accessibleModules } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!accessibleModules.includes("financiero")) {
      navigate("/dashboard?denied=1", { replace: true });
    }
  }, [accessibleModules, navigate]);

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [selected, setSelected] = useState<ProjectDetail | null>(null);
  const [cuotas, setCuotas] = useState<Cuota[] | null>(null);
  const [tablero, setTablero] = useState<Tablero | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [valorContrato, setValorContrato] = useState("");
  const [costoFabricacion, setCostoFabricacion] = useState("");
  const [numCuotas, setNumCuotas] = useState(3);
  const [filasCuota, setFilasCuota] = useState([EMPTY_CUOTA, EMPTY_CUOTA, EMPTY_CUOTA]);
  const [configError, setConfigError] = useState<string | null>(null);
  const [configSaving, setConfigSaving] = useState(false);

  const [pagoForms, setPagoForms] = useState<Record<number, { fecha_pago: string; monto_pagado: string; referencia_bancaria: string }>>({});
  const [pagoError, setPagoError] = useState<string | null>(null);
  const [pagoSaving, setPagoSaving] = useState<number | null>(null);

  const [cxp, setCxp] = useState<CxpConsolidado | null>(null);
  const [cxpError, setCxpError] = useState<string | null>(null);
  const [filtroProveedor, setFiltroProveedor] = useState("");
  const [filtroMoneda, setFiltroMoneda] = useState("");
  const [filtroEstado, setFiltroEstado] = useState("");

  async function loadCxp() {
    setCxpError(null);
    try {
      const params = new URLSearchParams();
      if (filtroProveedor) params.set("proveedor", filtroProveedor);
      if (filtroMoneda) params.set("moneda", filtroMoneda);
      if (filtroEstado) params.set("estado", filtroEstado);
      const found = await projectsApiFetch<CxpConsolidado>(`/cuentas-por-pagar?${params.toString()}`, {
        token,
        method: "GET",
      });
      setCxp(found);
    } catch (err) {
      setCxpError(err instanceof ApiError ? err.message : "No se pudo cargar el consolidado de cuentas por pagar");
    }
  }

  useEffect(() => {
    loadCxp();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSearch(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSelected(null);
    setCuotas(null);
    setTablero(null);
    try {
      const found = await projectsApiFetch<SearchResult[]>(
        `/projects/search?q=${encodeURIComponent(query)}`,
        { token }
      );
      setResults(found);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo buscar el proyecto");
    }
  }

  async function openProject(crpCode: string, cliente: string) {
    setError(null);
    setSelected({ crp_code: crpCode, cliente });
    try {
      const found = await projectsApiFetch<Cuota[]>(`/projects/${encodeURIComponent(crpCode)}/cuotas`, {
        token,
        method: "GET",
      }).catch(() => null);
      setCuotas(found);
      const tableroFound = await projectsApiFetch<Tablero>(
        `/projects/${encodeURIComponent(crpCode)}/tablero-financiero`,
        { token, method: "GET" }
      ).catch(() => null);
      setTablero(tableroFound);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar el tablero financiero");
    }
  }

  async function handleConfigurarCuotas(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    setConfigError(null);
    setConfigSaving(true);
    try {
      const cuotasPayload = filasCuota.slice(0, numCuotas).map((f, idx) => ({
        numero: idx + 1,
        etiqueta: f.etiqueta,
        monto: Number(f.monto),
        porcentaje: Number(f.porcentaje),
        fecha_vencimiento: f.fecha_vencimiento,
      }));
      const created = await projectsApiFetch<Cuota[]>(`/projects/${encodeURIComponent(selected.crp_code)}/cuotas`, {
        method: "POST",
        token,
        body: {
          valor_contrato: Number(valorContrato),
          costo_fabricacion: Number(costoFabricacion) || 0,
          cuotas: cuotasPayload,
        },
      });
      setCuotas(created);
      const tableroFound = await projectsApiFetch<Tablero>(
        `/projects/${encodeURIComponent(selected.crp_code)}/tablero-financiero`,
        { token }
      ).catch(() => null);
      setTablero(tableroFound);
    } catch (err) {
      setConfigError(err instanceof ApiError ? err.message : "No se pudo configurar el esquema de pagos");
    } finally {
      setConfigSaving(false);
    }
  }

  async function handleRegistrarPago(numero: number) {
    if (!selected) return;
    const form = pagoForms[numero];
    setPagoError(null);
    setPagoSaving(numero);
    try {
      await projectsApiFetch(`/projects/${encodeURIComponent(selected.crp_code)}/cuotas/${numero}/pago`, {
        method: "PATCH",
        token,
        body: {
          fecha_pago: form.fecha_pago,
          monto_pagado: Number(form.monto_pagado),
          referencia_bancaria: form.referencia_bancaria || undefined,
        },
      });
      const found = await projectsApiFetch<Cuota[]>(`/projects/${encodeURIComponent(selected.crp_code)}/cuotas`, {
        token,
      });
      setCuotas(found);
      const tableroFound = await projectsApiFetch<Tablero>(
        `/projects/${encodeURIComponent(selected.crp_code)}/tablero-financiero`,
        { token }
      ).catch(() => null);
      setTablero(tableroFound);
    } catch (err) {
      setPagoError(err instanceof ApiError ? err.message : "No se pudo registrar el pago");
    } finally {
      setPagoSaving(null);
    }
  }

  const totalCobrado = cuotas ? cuotas.filter((c) => c.estado === "PAGADO").reduce((s, c) => s + (c.monto_pagado ?? c.monto), 0) : 0;
  const totalPendiente = cuotas ? cuotas.filter((c) => c.estado === "PENDIENTE").reduce((s, c) => s + c.monto, 0) : 0;

  return (
    <AppShell>
      <h1 className="page-title">Financiero</h1>
      <p className="page-subtitle">Cuotas, anticipos y registro de pagos por proyecto</p>

      <div className="card">
        <h2 className="card-title">Buscar proyecto</h2>
        <form onSubmit={handleSearch} style={{ display: "flex", gap: 10 }}>
          <input
            style={{ flex: 1, border: "1px solid var(--mactral-border)", borderRadius: 6, padding: "9px 10px" }}
            placeholder="Código CRP o nombre de cliente..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button type="submit" className="btn-primary">
            Buscar
          </button>
        </form>
        {error && <div className="alert alert-error" style={{ marginTop: 14 }}>{error}</div>}
        {results && results.length > 0 && (
          <table style={{ marginTop: 14 }}>
            <thead>
              <tr>
                <th>Código CRP</th>
                <th>Cliente</th>
                <th>Ciudad</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {results.map((r) => (
                <tr key={r.id}>
                  <td>{r.crp_code}</td>
                  <td>{r.cliente}</td>
                  <td>{r.ciudad}</td>
                  <td>
                    <button className="btn-link" onClick={() => openProject(r.crp_code, r.cliente)}>
                      Ver financiero
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {selected && (
        <div className="card">
          <h2 className="card-title">
            {selected.crp_code} · {selected.cliente}
          </h2>

          {!cuotas || cuotas.length === 0 ? (
            <>
              <p style={{ color: "var(--mactral-text-muted)", fontSize: 13 }}>
                Este proyecto no tiene un esquema de pagos configurado.
              </p>
              {configError && <div className="alert alert-error">{configError}</div>}
              <form onSubmit={handleConfigurarCuotas}>
                <div className="form-grid">
                  <div className="form-field">
                    <label htmlFor="valor_contrato">Valor del contrato (COP)</label>
                    <input
                      id="valor_contrato"
                      type="number"
                      value={valorContrato}
                      onChange={(e) => setValorContrato(e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label htmlFor="costo_fabricacion">Costo de fabricación (COP)</label>
                    <input
                      id="costo_fabricacion"
                      type="number"
                      value={costoFabricacion}
                      onChange={(e) => setCostoFabricacion(e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label htmlFor="num_cuotas">Número de cuotas</label>
                    <select id="num_cuotas" value={numCuotas} onChange={(e) => setNumCuotas(Number(e.target.value))}>
                      <option value={1}>1</option>
                      <option value={2}>2</option>
                      <option value={3}>3</option>
                    </select>
                  </div>
                </div>

                {Array.from({ length: numCuotas }).map((_, idx) => (
                  <div className="form-grid" key={idx} style={{ marginTop: 12 }}>
                    <div className="form-field">
                      <label>Etiqueta cuota {idx + 1}</label>
                      <input
                        value={filasCuota[idx].etiqueta}
                        onChange={(e) => {
                          const next = [...filasCuota];
                          next[idx] = { ...next[idx], etiqueta: e.target.value };
                          setFilasCuota(next);
                        }}
                      />
                    </div>
                    <div className="form-field">
                      <label>Monto</label>
                      <input
                        type="number"
                        value={filasCuota[idx].monto}
                        onChange={(e) => {
                          const next = [...filasCuota];
                          next[idx] = { ...next[idx], monto: e.target.value };
                          setFilasCuota(next);
                        }}
                      />
                    </div>
                    <div className="form-field">
                      <label>Porcentaje</label>
                      <input
                        type="number"
                        value={filasCuota[idx].porcentaje}
                        onChange={(e) => {
                          const next = [...filasCuota];
                          next[idx] = { ...next[idx], porcentaje: e.target.value };
                          setFilasCuota(next);
                        }}
                      />
                    </div>
                    <div className="form-field">
                      <label>Vencimiento</label>
                      <input
                        type="date"
                        value={filasCuota[idx].fecha_vencimiento}
                        onChange={(e) => {
                          const next = [...filasCuota];
                          next[idx] = { ...next[idx], fecha_vencimiento: e.target.value };
                          setFilasCuota(next);
                        }}
                      />
                    </div>
                  </div>
                ))}

                <button type="submit" className="btn-primary" style={{ marginTop: 16 }} disabled={configSaving}>
                  {configSaving ? "Guardando..." : "Guardar esquema de pagos"}
                </button>
              </form>
            </>
          ) : (
            <>
              <div className="form-grid" style={{ marginBottom: 16 }}>
                <div>
                  <div style={{ fontSize: 12, color: "var(--mactral-text-muted)" }}>Total cobrado</div>
                  <div style={{ fontSize: 22, fontWeight: 700 }}>${totalCobrado.toLocaleString("es-CO")}</div>
                </div>
                <div>
                  <div style={{ fontSize: 12, color: "var(--mactral-text-muted)" }}>Por cobrar</div>
                  <div style={{ fontSize: 22, fontWeight: 700 }}>${totalPendiente.toLocaleString("es-CO")}</div>
                </div>
                {tablero && (
                  <>
                    <div>
                      <div style={{ fontSize: 12, color: "var(--mactral-text-muted)" }}>Gastos logísticos (COP)</div>
                      <div style={{ fontSize: 22, fontWeight: 700 }}>
                        ${tablero.total_gastos_logisticos_cop.toLocaleString("es-CO")}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: 12, color: "var(--mactral-text-muted)" }}>Margen bruto</div>
                      <div style={{ fontSize: 22, fontWeight: 700 }}>
                        {tablero.margen_bruto !== null ? `$${tablero.margen_bruto.toLocaleString("es-CO")}` : "—"}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: 12, color: "var(--mactral-text-muted)" }}>Semáforo de pago</div>
                      <span className={`badge ${SEMAFORO_CLASSES[tablero.semaforo_pago]}`}>
                        {SEMAFORO_LABELS[tablero.semaforo_pago]}
                      </span>
                    </div>
                  </>
                )}
              </div>

              {tablero && (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 12, color: "var(--mactral-text-muted)", marginBottom: 6 }}>
                    Tasas de cambio de referencia (a COP)
                  </div>
                  <div style={{ display: "flex", gap: 16 }}>
                    {tablero.tasas_cambio.map((t) => (
                      <div key={t.moneda} style={{ fontSize: 13 }}>
                        <strong>{t.moneda}</strong> ${t.tasa_cop.toLocaleString("es-CO")}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {pagoError && <div className="alert alert-error">{pagoError}</div>}

              <table>
                <thead>
                  <tr>
                    <th>Cuota</th>
                    <th>Monto</th>
                    <th>Vencimiento</th>
                    <th>Estado</th>
                    <th>Registrar pago</th>
                  </tr>
                </thead>
                <tbody>
                  {cuotas.map((c) => (
                    <tr key={c.numero}>
                      <td>
                        {c.etiqueta} ({c.porcentaje}%)
                      </td>
                      <td>${c.monto.toLocaleString("es-CO")}</td>
                      <td>{new Date(c.fecha_vencimiento + "T00:00:00").toLocaleDateString("es-CO")}</td>
                      <td>
                        <span className={`badge ${c.estado === "PAGADO" ? "badge-status-activo" : "badge-role"}`}>
                          {c.estado === "PAGADO" ? "Pagado" : "Pendiente"}
                        </span>
                      </td>
                      <td>
                        {c.estado === "PENDIENTE" && (
                          <div style={{ display: "flex", gap: 6 }}>
                            <input
                              type="date"
                              style={{ width: 130 }}
                              onChange={(e) =>
                                setPagoForms({
                                  ...pagoForms,
                                  [c.numero]: {
                                    ...(pagoForms[c.numero] ?? { fecha_pago: "", monto_pagado: String(c.monto), referencia_bancaria: "" }),
                                    fecha_pago: e.target.value,
                                  },
                                })
                              }
                            />
                            <input
                              type="number"
                              placeholder="Monto"
                              style={{ width: 100 }}
                              defaultValue={c.monto}
                              onChange={(e) =>
                                setPagoForms({
                                  ...pagoForms,
                                  [c.numero]: {
                                    ...(pagoForms[c.numero] ?? { fecha_pago: "", monto_pagado: String(c.monto), referencia_bancaria: "" }),
                                    monto_pagado: e.target.value,
                                  },
                                })
                              }
                            />
                            <input
                              placeholder="Referencia"
                              style={{ width: 100 }}
                              onChange={(e) =>
                                setPagoForms({
                                  ...pagoForms,
                                  [c.numero]: {
                                    ...(pagoForms[c.numero] ?? { fecha_pago: "", monto_pagado: String(c.monto), referencia_bancaria: "" }),
                                    referencia_bancaria: e.target.value,
                                  },
                                })
                              }
                            />
                            <button
                              className="btn-primary"
                              disabled={pagoSaving === c.numero}
                              onClick={() => handleRegistrarPago(c.numero)}
                            >
                              {pagoSaving === c.numero ? "..." : "Registrar"}
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </div>
      )}

      <div className="card">
        <h2 className="card-title">Cuentas por pagar (consolidado)</h2>
        <p className="page-subtitle">Gastos logísticos y obligaciones con proveedores de todos los proyectos</p>

        <div style={{ display: "flex", gap: 10, marginBottom: 14 }}>
          <input
            placeholder="Proveedor..."
            value={filtroProveedor}
            onChange={(e) => setFiltroProveedor(e.target.value)}
            style={{ border: "1px solid var(--mactral-border)", borderRadius: 6, padding: "9px 10px" }}
          />
          <select value={filtroMoneda} onChange={(e) => setFiltroMoneda(e.target.value)}>
            <option value="">Moneda (todas)</option>
            <option value="COP">COP</option>
            <option value="USD">USD</option>
            <option value="EUR">EUR</option>
            <option value="GBP">GBP</option>
            <option value="CNY">CNY</option>
          </select>
          <select value={filtroEstado} onChange={(e) => setFiltroEstado(e.target.value)}>
            <option value="">Estado (todos)</option>
            <option value="PENDIENTE">Pendiente</option>
            <option value="PAGADA">Pagada</option>
          </select>
          <button className="btn-primary" onClick={loadCxp}>
            Filtrar
          </button>
        </div>

        {cxpError && <div className="alert alert-error">{cxpError}</div>}

        {cxp && (
          <>
            <div className="form-grid" style={{ marginBottom: 14 }}>
              <div>
                <div style={{ fontSize: 12, color: "var(--mactral-text-muted)" }}>Total pendiente (COP)</div>
                <div style={{ fontSize: 22, fontWeight: 700 }}>${cxp.total_pendiente_cop.toLocaleString("es-CO")}</div>
              </div>
              <div>
                <div style={{ fontSize: 12, color: "var(--mactral-text-muted)" }}>Total pagado (COP)</div>
                <div style={{ fontSize: 22, fontWeight: 700 }}>${cxp.total_pagado_cop.toLocaleString("es-CO")}</div>
              </div>
            </div>

            {cxp.items.length === 0 ? (
              <p style={{ color: "var(--mactral-text-muted)", fontSize: 13 }}>No hay cuentas por pagar registradas.</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Proyecto</th>
                    <th>Tipo</th>
                    <th>Proveedor</th>
                    <th>Concepto</th>
                    <th>Monto</th>
                    <th>Monto (COP)</th>
                    <th>Vencimiento</th>
                    <th>Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {cxp.items.map((i) => (
                    <tr key={i.id}>
                      <td>{i.crp_code}</td>
                      <td>{i.tipo}</td>
                      <td>{i.proveedor}</td>
                      <td>{i.concepto}</td>
                      <td>
                        {i.moneda} {i.monto.toLocaleString("es-CO")}
                      </td>
                      <td>${i.monto_cop.toLocaleString("es-CO")}</td>
                      <td>{new Date(i.fecha_vencimiento + "T00:00:00").toLocaleDateString("es-CO")}</td>
                      <td>
                        <span className={`badge ${i.estado === "PAGADA" ? "badge-status-activo" : "badge-role"}`}>
                          {i.estado === "PAGADA" ? "Pagada" : "Pendiente"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}
