import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import {
  ApiError,
  projectsApiFetch,
  projectsApiFetchMultipart,
  projectsFetchBlob,
} from "../api/client";
import AppShell from "../components/AppShell";
import { useAuth } from "../context/AuthContext";

type SearchResult = {
  id: string;
  crp_code: string;
  cliente: string;
  ciudad: string;
};

type ProjectDetail = {
  crp_code: string;
  cliente: string;
};

type GastoLogistico = {
  id: string;
  tipo: "VUELO" | "HOSPEDAJE" | "TRANSPORTE" | "VIATICOS" | "OTRO";
  proveedor: string;
  concepto: string;
  monto: number;
  moneda: string;
  monto_cop: number;
  fecha_vencimiento: string;
  estado: "PENDIENTE" | "PAGADA";
  autorizado_gg: boolean;
  tiene_soporte: boolean;
};

const TIPO_LABELS: Record<GastoLogistico["tipo"], string> = {
  VUELO: "Vuelo",
  HOSPEDAJE: "Hospedaje",
  TRANSPORTE: "Transporte",
  VIATICOS: "Viáticos",
  OTRO: "Otro",
};

const EMPTY_FORM = {
  tipo: "VUELO" as GastoLogistico["tipo"],
  proveedor: "",
  concepto: "",
  monto: "",
  moneda: "COP",
  fecha_vencimiento: "",
  autorizado_gg: false,
};

export default function LogisticaPage() {
  const { token, accessibleModules } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!accessibleModules.includes("logistica")) {
      navigate("/dashboard?denied=1", { replace: true });
    }
  }, [accessibleModules, navigate]);

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [selected, setSelected] = useState<ProjectDetail | null>(null);
  const [gastos, setGastos] = useState<GastoLogistico[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSearch(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSelected(null);
    setGastos(null);
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

  async function loadGastos(crpCode: string) {
    const found = await projectsApiFetch<GastoLogistico[]>(
      `/projects/${encodeURIComponent(crpCode)}/logistica`,
      { token, method: "GET" }
    );
    setGastos(found);
  }

  async function openProject(crpCode: string, cliente: string) {
    setError(null);
    setSelected({ crp_code: crpCode, cliente });
    setShowForm(false);
    setForm(EMPTY_FORM);
    try {
      await loadGastos(crpCode);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar la programación logística");
    }
  }

  async function handleRegistrarGasto(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    setFormError(null);
    setSaving(true);
    try {
      await projectsApiFetch(`/projects/${encodeURIComponent(selected.crp_code)}/logistica`, {
        method: "POST",
        token,
        body: {
          tipo: form.tipo,
          proveedor: form.proveedor,
          concepto: form.concepto,
          monto: Number(form.monto),
          moneda: form.moneda,
          fecha_vencimiento: form.fecha_vencimiento,
          autorizado_gg: form.autorizado_gg,
        },
      });
      await loadGastos(selected.crp_code);
      setForm(EMPTY_FORM);
      setShowForm(false);
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "No se pudo registrar el gasto logístico");
    } finally {
      setSaving(false);
    }
  }

  const [soporteFiles, setSoporteFiles] = useState<Record<string, File | null>>({});
  const [soporteSaving, setSoporteSaving] = useState<string | null>(null);
  const [soporteError, setSoporteError] = useState<string | null>(null);

  async function handleSubirSoporte(gastoId: string) {
    if (!selected) return;
    const file = soporteFiles[gastoId];
    if (!file) return;
    setSoporteError(null);
    setSoporteSaving(gastoId);
    try {
      const formData = new FormData();
      formData.append("soporte", file);
      await projectsApiFetchMultipart(
        `/projects/${encodeURIComponent(selected.crp_code)}/logistica/${gastoId}/soporte`,
        formData,
        token
      );
      await loadGastos(selected.crp_code);
    } catch (err) {
      setSoporteError(err instanceof ApiError ? err.message : "No se pudo adjuntar el soporte");
    } finally {
      setSoporteSaving(null);
    }
  }

  async function handleViewSoporte(gastoId: string) {
    if (!selected) return;
    const tab = window.open("", "_blank");
    try {
      const blob = await projectsFetchBlob(
        `/projects/${encodeURIComponent(selected.crp_code)}/logistica/${gastoId}/soporte`,
        token
      );
      const url = URL.createObjectURL(blob);
      if (tab) tab.location.href = url;
    } catch (err) {
      tab?.close();
      setSoporteError(err instanceof ApiError ? err.message : "No se pudo abrir el soporte");
    }
  }

  return (
    <AppShell>
      <h1 className="page-title">Logística</h1>
      <p className="page-subtitle">Programación de viajes: vuelos, hospedaje, transporte y viáticos</p>

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
                      Ver logística
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

          <button className="btn-primary" style={{ marginBottom: 14 }} onClick={() => setShowForm(!showForm)}>
            {showForm ? "Cancelar" : "+ Registrar gasto logístico"}
          </button>

          {showForm && (
            <form onSubmit={handleRegistrarGasto} style={{ marginBottom: 20 }}>
              {formError && <div className="alert alert-error">{formError}</div>}
              <div className="form-grid">
                <div className="form-field">
                  <label htmlFor="tipo">Tipo</label>
                  <select
                    id="tipo"
                    value={form.tipo}
                    onChange={(e) => setForm({ ...form, tipo: e.target.value as GastoLogistico["tipo"] })}
                  >
                    {Object.entries(TIPO_LABELS).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="form-field">
                  <label htmlFor="proveedor">Proveedor</label>
                  <input
                    id="proveedor"
                    value={form.proveedor}
                    onChange={(e) => setForm({ ...form, proveedor: e.target.value })}
                  />
                </div>
                <div className="form-field">
                  <label htmlFor="concepto">Concepto</label>
                  <input
                    id="concepto"
                    value={form.concepto}
                    onChange={(e) => setForm({ ...form, concepto: e.target.value })}
                  />
                </div>
                <div className="form-field">
                  <label htmlFor="monto">Monto</label>
                  <input
                    id="monto"
                    type="number"
                    value={form.monto}
                    onChange={(e) => setForm({ ...form, monto: e.target.value })}
                  />
                </div>
                <div className="form-field">
                  <label htmlFor="moneda">Moneda</label>
                  <select id="moneda" value={form.moneda} onChange={(e) => setForm({ ...form, moneda: e.target.value })}>
                    <option value="COP">COP</option>
                    <option value="USD">USD</option>
                    <option value="EUR">EUR</option>
                    <option value="GBP">GBP</option>
                    <option value="CNY">CNY</option>
                  </select>
                </div>
                <div className="form-field">
                  <label htmlFor="fecha_vencimiento">Fecha</label>
                  <input
                    id="fecha_vencimiento"
                    type="date"
                    value={form.fecha_vencimiento}
                    onChange={(e) => setForm({ ...form, fecha_vencimiento: e.target.value })}
                  />
                </div>
                {form.tipo === "VIATICOS" && (
                  <div className="form-field">
                    <label htmlFor="autorizado_gg">Autorizado por el Gerente General</label>
                    <input
                      id="autorizado_gg"
                      type="checkbox"
                      checked={form.autorizado_gg}
                      onChange={(e) => setForm({ ...form, autorizado_gg: e.target.checked })}
                    />
                  </div>
                )}
              </div>
              <button type="submit" className="btn-primary" style={{ marginTop: 16 }} disabled={saving}>
                {saving ? "Guardando..." : "Registrar gasto logístico"}
              </button>
            </form>
          )}

          {gastos && gastos.length === 0 ? (
            <p style={{ color: "var(--mactral-text-muted)", fontSize: 13 }}>
              Este proyecto no tiene gastos logísticos registrados.
            </p>
          ) : (
            gastos && (
              <>
                {soporteError && <div className="alert alert-error">{soporteError}</div>}
                <table>
                <thead>
                  <tr>
                    <th>Tipo</th>
                    <th>Proveedor</th>
                    <th>Concepto</th>
                    <th>Monto</th>
                    <th>Fecha</th>
                    <th>Estado</th>
                    <th>Soporte</th>
                  </tr>
                </thead>
                <tbody>
                  {gastos.map((g) => (
                    <tr key={g.id}>
                      <td>{TIPO_LABELS[g.tipo]}</td>
                      <td>{g.proveedor}</td>
                      <td>{g.concepto}</td>
                      <td>
                        {g.moneda} {g.monto.toLocaleString("es-CO")}
                      </td>
                      <td>{new Date(g.fecha_vencimiento + "T00:00:00").toLocaleDateString("es-CO")}</td>
                      <td>
                        <span className={`badge ${g.estado === "PAGADA" ? "badge-status-activo" : "badge-role"}`}>
                          {g.estado === "PAGADA" ? "Pagada" : "Pendiente"}
                        </span>
                      </td>
                      <td>
                        {g.tiene_soporte ? (
                          <button className="btn-link" onClick={() => handleViewSoporte(g.id)}>
                            Ver soporte
                          </button>
                        ) : (
                          <div style={{ display: "flex", gap: 6 }}>
                            <input
                              type="file"
                              onChange={(e) =>
                                setSoporteFiles((prev) => ({ ...prev, [g.id]: e.target.files?.[0] ?? null }))
                              }
                            />
                            <button
                              className="btn-primary"
                              disabled={soporteSaving === g.id || !soporteFiles[g.id]}
                              onClick={() => handleSubirSoporte(g.id)}
                            >
                              {soporteSaving === g.id ? "..." : "Subir"}
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
                </table>
              </>
            )
          )}
        </div>
      )}
    </AppShell>
  );
}
