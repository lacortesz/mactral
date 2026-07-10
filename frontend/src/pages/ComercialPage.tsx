import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, comercialApiFetch } from "../api/client";
import AppShell from "../components/AppShell";
import { useAuth } from "../context/AuthContext";
import {
  CANAL_ENTRADA_OPTIONS,
  ESTADO_LEAD_LABELS,
  LINE_LABELS,
  type EstadoLead,
  type LineaNegocio,
} from "../domain";

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

type LeadDetail = LeadListItem & {
  telefono: string | null;
  correo: string | null;
  canal_entrada: string;
  marca: string;
  vendedor_id: string;
  interacciones: Interaction[];
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
        <div className="card">
          <h2 className="card-title">
            {selected.codigo} · {selected.nombre}
          </h2>
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
        </div>
      )}
    </AppShell>
  );
}
