import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, comercialApiFetch, comercialFetchBlob } from "../api/client";
import AppShell from "../components/AppShell";
import { useAuth } from "../context/AuthContext";
import {
  CANAL_ENTRADA_OPTIONS,
  ESTADO_LEAD_LABELS,
  LINE_LABELS,
  TIPO_CLASIFICACION_LABELS,
  TIPO_PAGO_LABELS,
  type EstadoLead,
  type LineaNegocio,
  type TipoClasificacion,
  type TipoPago,
} from "../domain";

const ESTADO_SIGUIENTE: Partial<Record<EstadoLead, EstadoLead>> = {
  COTIZAR: "ENVIADA",
  ENVIADA: "VENDIDO",
};

type LeadListItem = {
  id: string;
  codigo: string;
  nombre: string;
  ciudad: string;
  tipo_producto: string;
  linea_negocio: LineaNegocio;
  vendedor_nombre: string;
  estado: EstadoLead;
  created_at: string;
};

type Interaction = {
  fecha: string;
  canal: string;
  resumen: string;
  usuario_nombre: string;
};

type Quotation = {
  version: number;
  numero_cotizacion: string;
  valor_equipo: number;
  tipo_pago: TipoPago;
  anticipo_inicial_pct: number;
  segundo_anticipo_pct: number;
  saldo_final_pct: number;
  fecha_estimada_entrega: string;
  created_at: string;
};

type EstadoHistorialItem = {
  estado_anterior: EstadoLead;
  estado_nuevo: EstadoLead;
  usuario_nombre: string;
  fecha: string;
};

type LeadDetail = LeadListItem & {
  telefono: string | null;
  correo: string | null;
  canal_entrada: string;
  marca: string;
  vendedor_id: string;
  clasificacion: TipoClasificacion | null;
  interacciones: Interaction[];
  cotizaciones: Quotation[];
  historial_estados: EstadoHistorialItem[];
};

const EMPTY_QUOTATION_FORM = {
  valor_equipo: "",
  tipo_pago: "CONTADO" as TipoPago,
  anticipo_inicial_pct: "50",
  segundo_anticipo_pct: "30",
  saldo_final_pct: "20",
  fecha_estimada_entrega: "",
};

const EMPTY_FORM = {
  nombre: "",
  telefono: "",
  correo: "",
  ciudad: "",
  canal_entrada: CANAL_ENTRADA_OPTIONS[0] as string,
  linea_negocio: "MOBILITY" as LineaNegocio,
  tipo_producto: "",
  marca: "",
};

export default function ComercialPage() {
  const { token, accessibleModules } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    // Escenario 3 (E1-H2): acceso directo por URL a un módulo no autorizado.
    if (!accessibleModules.includes("comercial")) {
      navigate("/dashboard?denied=1", { replace: true });
    }
  }, [accessibleModules, navigate]);

  const [leads, setLeads] = useState<LeadListItem[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [selected, setSelected] = useState<LeadDetail | null>(null);
  const [interactionForm, setInteractionForm] = useState({
    canal: CANAL_ENTRADA_OPTIONS[0] as string,
    resumen: "",
  });
  const [interactionError, setInteractionError] = useState<string | null>(null);

  const [quotationForm, setQuotationForm] = useState(EMPTY_QUOTATION_FORM);
  const [quotationError, setQuotationError] = useState<string | null>(null);
  const [generatingQuotation, setGeneratingQuotation] = useState(false);

  const [estadoError, setEstadoError] = useState<string | null>(null);
  const [changingEstado, setChangingEstado] = useState(false);
  const [showClasificacionModal, setShowClasificacionModal] = useState(false);
  const [clasificacion, setClasificacion] = useState<TipoClasificacion>("GM");

  useEffect(() => {
    if (!token) return;
    comercialApiFetch<LeadListItem[]>("/leads", { token }).then(setLeads).catch(() => {});
  }, [token]);

  const kpis = {
    COTIZAR: leads.filter((l) => l.estado === "COTIZAR").length,
    ENVIADA: leads.filter((l) => l.estado === "ENVIADA").length,
    VENDIDO: leads.filter((l) => l.estado === "VENDIDO").length,
  };

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const created = await comercialApiFetch<LeadDetail>("/leads", {
        method: "POST",
        token,
        body: form,
      });
      setLeads((prev) => [created, ...prev]);
      setForm(EMPTY_FORM);
      setShowForm(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar el lead");
    } finally {
      setSubmitting(false);
    }
  }

  async function openLead(id: string) {
    setInteractionError(null);
    try {
      const detail = await comercialApiFetch<LeadDetail>(`/leads/${id}`, { token });
      setSelected(detail);
    } catch (err) {
      setInteractionError(err instanceof ApiError ? err.message : "No se pudo abrir el lead");
    }
  }

  async function handleAddInteraction(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    setInteractionError(null);
    try {
      await comercialApiFetch(`/leads/${selected.id}/interactions`, {
        method: "POST",
        token,
        body: interactionForm,
      });
      const refreshed = await comercialApiFetch<LeadDetail>(`/leads/${selected.id}`, { token });
      setSelected(refreshed);
      setInteractionForm({ canal: CANAL_ENTRADA_OPTIONS[0], resumen: "" });
    } catch (err) {
      setInteractionError(err instanceof ApiError ? err.message : "No se pudo agregar la nota");
    }
  }

  async function handleGenerateQuotation(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    setQuotationError(null);
    setGeneratingQuotation(true);
    try {
      await comercialApiFetch(`/leads/${selected.id}/quotations`, {
        method: "POST",
        token,
        body: {
          valor_equipo: Number(quotationForm.valor_equipo),
          tipo_pago: quotationForm.tipo_pago,
          anticipo_inicial_pct: Number(quotationForm.anticipo_inicial_pct),
          segundo_anticipo_pct: Number(quotationForm.segundo_anticipo_pct),
          saldo_final_pct: Number(quotationForm.saldo_final_pct),
          fecha_estimada_entrega: quotationForm.fecha_estimada_entrega,
        },
      });
      const refreshed = await comercialApiFetch<LeadDetail>(`/leads/${selected.id}`, { token });
      setSelected(refreshed);
      setLeads((prev) => prev.map((l) => (l.id === refreshed.id ? { ...l, estado: refreshed.estado } : l)));
    } catch (err) {
      setQuotationError(err instanceof ApiError ? err.message : "No se pudo generar la cotización");
    } finally {
      setGeneratingQuotation(false);
    }
  }

  async function advanceEstado(target: EstadoLead, clasificacionElegida?: TipoClasificacion) {
    if (!selected) return;
    setEstadoError(null);
    setChangingEstado(true);
    try {
      const refreshed = await comercialApiFetch<LeadDetail>(`/leads/${selected.id}/estado`, {
        method: "PATCH",
        token,
        body: clasificacionElegida ? { estado: target, clasificacion: clasificacionElegida } : { estado: target },
      });
      setSelected(refreshed);
      setLeads((prev) => prev.map((l) => (l.id === refreshed.id ? { ...l, estado: refreshed.estado } : l)));
      setShowClasificacionModal(false);
    } catch (err) {
      setEstadoError(err instanceof ApiError ? err.message : "No se pudo cambiar el estado");
    } finally {
      setChangingEstado(false);
    }
  }

  function handleAvanzarClick() {
    if (!selected) return;
    const siguiente = ESTADO_SIGUIENTE[selected.estado];
    if (!siguiente) return;
    if (siguiente === "VENDIDO") {
      setEstadoError(null);
      setShowClasificacionModal(true);
      return;
    }
    advanceEstado(siguiente);
  }

  async function viewQuotationPdf(leadId: string, version: number) {
    // La pestaña debe abrirse de forma síncrona con el clic: si se abre
    // después del await, Chromium pierde el "user gesture" y bloquea el popup.
    const tab = window.open("", "_blank");
    try {
      const blob = await comercialFetchBlob(`/leads/${leadId}/quotations/${version}/pdf`, token);
      const url = URL.createObjectURL(blob);
      if (tab) tab.location.href = url;
    } catch (err) {
      tab?.close();
      setQuotationError(err instanceof ApiError ? err.message : "No se pudo abrir el PDF");
    }
  }

  return (
    <AppShell>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <div>
          <h1 className="page-title">Módulo comercial — Leads</h1>
          <p className="page-subtitle">CRM · Mobility + Industry · {leads.length} leads activos</p>
        </div>
        <button className="btn-primary" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancelar" : "+ Nuevo lead"}
        </button>
      </div>

      <div className="form-grid" style={{ marginBottom: 20 }}>
        <div className="card" style={{ margin: 0 }}>
          <h2 className="card-title">Cotizar</h2>
          <div style={{ fontSize: 28, fontWeight: 700 }}>{kpis.COTIZAR}</div>
        </div>
        <div className="card" style={{ margin: 0 }}>
          <h2 className="card-title">Enviada</h2>
          <div style={{ fontSize: 28, fontWeight: 700 }}>{kpis.ENVIADA}</div>
        </div>
        <div className="card" style={{ margin: 0 }}>
          <h2 className="card-title">Vendido</h2>
          <div style={{ fontSize: 28, fontWeight: 700 }}>{kpis.VENDIDO}</div>
        </div>
      </div>

      {showForm && (
        <div className="card">
          <h2 className="card-title">Nuevo lead</h2>
          {error && <div className="alert alert-error">{error}</div>}
          <form onSubmit={handleCreate}>
            <div className="form-grid">
              <div className="form-field full">
                <label htmlFor="nombre">Nombre</label>
                <input
                  id="nombre"
                  value={form.nombre}
                  onChange={(e) => setForm({ ...form, nombre: e.target.value })}
                />
              </div>
              <div className="form-field">
                <label htmlFor="telefono">Teléfono</label>
                <input
                  id="telefono"
                  value={form.telefono}
                  onChange={(e) => setForm({ ...form, telefono: e.target.value })}
                />
              </div>
              <div className="form-field">
                <label htmlFor="correo">Correo</label>
                <input
                  id="correo"
                  type="email"
                  value={form.correo}
                  onChange={(e) => setForm({ ...form, correo: e.target.value })}
                />
              </div>
              <div className="form-field">
                <label htmlFor="ciudad">Ciudad</label>
                <input
                  id="ciudad"
                  value={form.ciudad}
                  onChange={(e) => setForm({ ...form, ciudad: e.target.value })}
                />
              </div>
              <div className="form-field">
                <label htmlFor="canal_entrada">Canal de entrada</label>
                <select
                  id="canal_entrada"
                  value={form.canal_entrada}
                  onChange={(e) => setForm({ ...form, canal_entrada: e.target.value })}
                >
                  {CANAL_ENTRADA_OPTIONS.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-field">
                <label htmlFor="linea_negocio">Línea de negocio</label>
                <select
                  id="linea_negocio"
                  value={form.linea_negocio}
                  onChange={(e) =>
                    setForm({ ...form, linea_negocio: e.target.value as LineaNegocio })
                  }
                >
                  <option value="MOBILITY">{LINE_LABELS.MOBILITY}</option>
                  <option value="INDUSTRY">{LINE_LABELS.INDUSTRY}</option>
                </select>
              </div>
              <div className="form-field">
                <label htmlFor="tipo_producto">Tipo de producto</label>
                <input
                  id="tipo_producto"
                  value={form.tipo_producto}
                  onChange={(e) => setForm({ ...form, tipo_producto: e.target.value })}
                />
              </div>
              <div className="form-field">
                <label htmlFor="marca">Marca</label>
                <input
                  id="marca"
                  value={form.marca}
                  onChange={(e) => setForm({ ...form, marca: e.target.value })}
                />
              </div>
            </div>
            <button type="submit" className="btn-primary" style={{ marginTop: 16 }} disabled={submitting}>
              {submitting ? "Guardando..." : "Guardar lead"}
            </button>
          </form>
        </div>
      )}

      <div className="card">
        <h2 className="card-title">Leads activos</h2>
        <table>
          <thead>
            <tr>
              <th>Código</th>
              <th>Cliente</th>
              <th>Ciudad</th>
              <th>Producto</th>
              <th>Línea</th>
              <th>Vendedor</th>
              <th>Estado</th>
              <th>Fecha</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {leads.map((l) => (
              <tr key={l.id}>
                <td>{l.codigo}</td>
                <td>{l.nombre}</td>
                <td>{l.ciudad}</td>
                <td>{l.tipo_producto}</td>
                <td>
                  <span className="badge badge-line">{LINE_LABELS[l.linea_negocio]}</span>
                </td>
                <td>{l.vendedor_nombre}</td>
                <td>
                  <span className="badge badge-role">{ESTADO_LEAD_LABELS[l.estado]}</span>
                </td>
                <td>{new Date(l.created_at).toLocaleDateString("es-CO")}</td>
                <td>
                  <button className="btn-link" onClick={() => openLead(l.id)}>
                    Ver
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selected && (
        <>
          <div className="card">
            <h2 className="card-title">
              {selected.codigo} · {selected.nombre}{" "}
              <span className="badge badge-role">{ESTADO_LEAD_LABELS[selected.estado]}</span>
            </h2>
            {estadoError && <div className="alert alert-error">{estadoError}</div>}

            {selected.clasificacion && (
              <p style={{ fontSize: 13, color: "var(--mactral-text-muted)" }}>
                Clasificación: <strong>{TIPO_CLASIFICACION_LABELS[selected.clasificacion]}</strong>
              </p>
            )}

            {ESTADO_SIGUIENTE[selected.estado] && (
              <button className="btn-primary" onClick={handleAvanzarClick} disabled={changingEstado}>
                {changingEstado
                  ? "Cambiando..."
                  : ESTADO_SIGUIENTE[selected.estado] === "VENDIDO"
                    ? "Marcar como Vendido"
                    : `Avanzar a ${ESTADO_LEAD_LABELS[ESTADO_SIGUIENTE[selected.estado] as EstadoLead]}`}
              </button>
            )}

            {selected.historial_estados.length > 0 && (
              <ul style={{ listStyle: "none", margin: "16px 0 0", padding: 0, fontSize: 13 }}>
                {selected.historial_estados.map((h, idx) => (
                  <li key={idx} style={{ padding: "4px 0", color: "var(--mactral-text-muted)" }}>
                    {new Date(h.fecha).toLocaleString("es-CO")} — {ESTADO_LEAD_LABELS[h.estado_anterior]} →{" "}
                    {ESTADO_LEAD_LABELS[h.estado_nuevo]} ({h.usuario_nombre})
                  </li>
                ))}
              </ul>
            )}
          </div>

          {showClasificacionModal && (
            <div
              style={{
                position: "fixed",
                inset: 0,
                background: "rgba(0,0,0,0.4)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                zIndex: 100,
              }}
            >
              <div className="card" style={{ maxWidth: 420, margin: 0 }}>
                <h2 className="card-title">Clasificación de la venta</h2>
                <p style={{ fontSize: 13, color: "var(--mactral-text-muted)" }}>
                  Elige la clasificación para activar el flujo correspondiente. Una vez confirmada
                  no se puede modificar sin aprobación de Gerencia.
                </p>
                <div className="form-field">
                  <label htmlFor="clasificacion">Clasificación</label>
                  <select
                    id="clasificacion"
                    value={clasificacion}
                    onChange={(e) => setClasificacion(e.target.value as TipoClasificacion)}
                  >
                    <option value="GM">{TIPO_CLASIFICACION_LABELS.GM}</option>
                    <option value="STOCK_MOBILITY">{TIPO_CLASIFICACION_LABELS.STOCK_MOBILITY}</option>
                    <option value="STOCK_INDUSTRY">{TIPO_CLASIFICACION_LABELS.STOCK_INDUSTRY}</option>
                  </select>
                </div>
                <div style={{ display: "flex", gap: 10, marginTop: 16 }}>
                  <button
                    className="btn-primary"
                    disabled={changingEstado}
                    onClick={() => advanceEstado("VENDIDO", clasificacion)}
                  >
                    {changingEstado ? "Confirmando..." : "Confirmar"}
                  </button>
                  <button
                    type="button"
                    className="btn-link"
                    onClick={() => setShowClasificacionModal(false)}
                    disabled={changingEstado}
                  >
                    Cancelar
                  </button>
                </div>
              </div>
            </div>
          )}

          <div className="card">
            <h2 className="card-title">Interacciones</h2>
            {interactionError && <div className="alert alert-error">{interactionError}</div>}

            <ul style={{ listStyle: "none", margin: "0 0 16px", padding: 0, fontSize: 13 }}>
              {selected.interacciones.length === 0 && (
                <li style={{ color: "var(--mactral-text-muted)" }}>Sin interacciones registradas.</li>
              )}
              {selected.interacciones.map((i, idx) => (
                <li key={idx} style={{ padding: "8px 0", borderBottom: "1px solid var(--mactral-border)" }}>
                  <strong>{new Date(i.fecha).toLocaleString("es-CO")}</strong>{" "}
                  <span className="badge badge-role">{i.canal}</span> — {i.resumen}{" "}
                  <span style={{ color: "var(--mactral-text-muted)" }}>({i.usuario_nombre})</span>
                </li>
              ))}
            </ul>

            {selected.estado === "VENDIDO" ? (
              <p style={{ fontSize: 13, color: "var(--mactral-text-muted)" }}>
                Este lead ya fue vendido: las etapas anteriores quedaron en solo lectura.
              </p>
            ) : (
              <form onSubmit={handleAddInteraction} style={{ display: "flex", gap: 10 }}>
                <select
                  value={interactionForm.canal}
                  onChange={(e) => setInteractionForm({ ...interactionForm, canal: e.target.value })}
                >
                  {CANAL_ENTRADA_OPTIONS.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
                <input
                  style={{ flex: 1, border: "1px solid var(--mactral-border)", borderRadius: 6, padding: "9px 10px" }}
                  placeholder="Resumen de la interacción..."
                  value={interactionForm.resumen}
                  onChange={(e) => setInteractionForm({ ...interactionForm, resumen: e.target.value })}
                />
                <button type="submit" className="btn-primary">
                  Agregar nota
                </button>
              </form>
            )}
          </div>

          <div className="card">
            <h2 className="card-title">Cotización</h2>
            {quotationError && <div className="alert alert-error">{quotationError}</div>}

            {selected.cotizaciones.length > 0 && (
              <table style={{ marginBottom: 16 }}>
                <thead>
                  <tr>
                    <th>N° cotización</th>
                    <th>Valor equipo</th>
                    <th>Tipo de pago</th>
                    <th>Entrega estimada</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {selected.cotizaciones.map((q) => (
                    <tr key={q.version}>
                      <td>{q.numero_cotizacion}</td>
                      <td>${q.valor_equipo.toLocaleString("es-CO")}</td>
                      <td>{TIPO_PAGO_LABELS[q.tipo_pago]}</td>
                      <td>{new Date(q.fecha_estimada_entrega).toLocaleDateString("es-CO")}</td>
                      <td>
                        <button className="btn-link" onClick={() => viewQuotationPdf(selected.id, q.version)}>
                          Vista previa
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            {selected.estado === "VENDIDO" ? (
              <p style={{ fontSize: 13, color: "var(--mactral-text-muted)" }}>
                Este lead ya fue vendido: la cotización quedó en solo lectura.
              </p>
            ) : (
            <form onSubmit={handleGenerateQuotation}>
              <div className="form-grid">
                <div className="form-field">
                  <label htmlFor="valor_equipo">Valor del equipo (COP)</label>
                  <input
                    id="valor_equipo"
                    type="number"
                    min={1}
                    value={quotationForm.valor_equipo}
                    onChange={(e) => setQuotationForm({ ...quotationForm, valor_equipo: e.target.value })}
                  />
                </div>
                <div className="form-field">
                  <label htmlFor="tipo_pago">Tipo de pago</label>
                  <select
                    id="tipo_pago"
                    value={quotationForm.tipo_pago}
                    onChange={(e) =>
                      setQuotationForm({ ...quotationForm, tipo_pago: e.target.value as TipoPago })
                    }
                  >
                    <option value="CONTADO">{TIPO_PAGO_LABELS.CONTADO}</option>
                    <option value="CREDITO">{TIPO_PAGO_LABELS.CREDITO}</option>
                  </select>
                </div>
                <div className="form-field">
                  <label htmlFor="fecha_estimada_entrega">Fecha estimada de entrega</label>
                  <input
                    id="fecha_estimada_entrega"
                    type="date"
                    value={quotationForm.fecha_estimada_entrega}
                    onChange={(e) =>
                      setQuotationForm({ ...quotationForm, fecha_estimada_entrega: e.target.value })
                    }
                  />
                </div>
                <div className="form-field">
                  <label htmlFor="anticipo_inicial_pct">Anticipo inicial (%)</label>
                  <input
                    id="anticipo_inicial_pct"
                    type="number"
                    min={0}
                    max={100}
                    value={quotationForm.anticipo_inicial_pct}
                    onChange={(e) =>
                      setQuotationForm({ ...quotationForm, anticipo_inicial_pct: e.target.value })
                    }
                  />
                </div>
                <div className="form-field">
                  <label htmlFor="segundo_anticipo_pct">2do anticipo (%)</label>
                  <input
                    id="segundo_anticipo_pct"
                    type="number"
                    min={0}
                    max={100}
                    value={quotationForm.segundo_anticipo_pct}
                    onChange={(e) =>
                      setQuotationForm({ ...quotationForm, segundo_anticipo_pct: e.target.value })
                    }
                  />
                </div>
                <div className="form-field">
                  <label htmlFor="saldo_final_pct">Saldo final (%)</label>
                  <input
                    id="saldo_final_pct"
                    type="number"
                    min={0}
                    max={100}
                    value={quotationForm.saldo_final_pct}
                    onChange={(e) => setQuotationForm({ ...quotationForm, saldo_final_pct: e.target.value })}
                  />
                </div>
              </div>

              {(() => {
                const valor = Number(quotationForm.valor_equipo) || 0;
                const pct1 = Number(quotationForm.anticipo_inicial_pct) || 0;
                const pct2 = Number(quotationForm.segundo_anticipo_pct) || 0;
                const pct3 = Number(quotationForm.saldo_final_pct) || 0;
                const total = pct1 + pct2 + pct3;
                return (
                  <div style={{ marginTop: 16, fontSize: 13 }}>
                    <div>
                      Anticipo 1 ({pct1}%): ${Math.round((valor * pct1) / 100).toLocaleString("es-CO")}
                    </div>
                    <div>
                      Anticipo 2 ({pct2}%): ${Math.round((valor * pct2) / 100).toLocaleString("es-CO")}
                    </div>
                    <div>
                      Saldo final ({pct3}%): ${Math.round((valor * pct3) / 100).toLocaleString("es-CO")}
                    </div>
                    <div style={{ fontWeight: 700 }}>Total contrato: ${valor.toLocaleString("es-CO")}</div>
                    {total !== 100 && (
                      <div style={{ color: "var(--mactral-red)", marginTop: 4 }}>
                        Los porcentajes suman {total}%, deben sumar 100%.
                      </div>
                    )}
                  </div>
                );
              })()}

              <button type="submit" className="btn-primary" style={{ marginTop: 16 }} disabled={generatingQuotation}>
                {generatingQuotation
                  ? "Generando..."
                  : selected.cotizaciones.length > 0
                    ? "Regenerar cotización"
                    : "Generar cotización PDF"}
              </button>
            </form>
            )}
          </div>
        </>
      )}
    </AppShell>
  );
}
