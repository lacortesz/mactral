import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, comercialApiFetch } from "../api/client";
import AppShell from "../components/AppShell";
import { useAuth } from "../context/AuthContext";
import { LINE_LABELS, type LineaNegocio } from "../domain";

type StockMovement = {
  tipo: "ENTRADA" | "SALIDA";
  cantidad: number;
  fecha: string;
  usuario_nombre: string;
  referencia_crp: string | null;
};

type StockItem = {
  id: string;
  linea_negocio: LineaNegocio;
  tipo_producto: string;
  nombre: string | null;
  descripcion: string | null;
  color: string | null;
  unidad: string;
  cantidad_total: number;
  cantidad_disponible: number;
  ultimo_movimiento: StockMovement | null;
};

const EMPTY_ENTRY_FORM = {
  linea_negocio: "MOBILITY" as LineaNegocio,
  tipo_producto: "",
  cantidad: "",
  nombre: "",
  descripcion: "",
  color: "",
  unidad: "unidad",
};

export default function StockPage() {
  const { token, accessibleModules } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!accessibleModules.includes("stock")) {
      navigate("/dashboard?denied=1", { replace: true });
    }
  }, [accessibleModules, navigate]);

  const [items, setItems] = useState<StockItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY_ENTRY_FORM);
  const [saving, setSaving] = useState(false);

  async function loadStock() {
    try {
      const found = await comercialApiFetch<StockItem[]>("/stock", { token });
      setItems(found);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar el inventario");
    }
  }

  useEffect(() => {
    if (!token) return;
    loadStock();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSaving(true);
    try {
      await comercialApiFetch("/stock/entrada", {
        method: "POST",
        token,
        body: {
          linea_negocio: form.linea_negocio,
          tipo_producto: form.tipo_producto,
          cantidad: Number(form.cantidad),
          nombre: form.nombre || undefined,
          descripcion: form.descripcion || undefined,
          color: form.color || undefined,
          unidad: form.unidad || "unidad",
        },
      });
      setForm(EMPTY_ENTRY_FORM);
      setShowForm(false);
      await loadStock();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo registrar la entrada");
    } finally {
      setSaving(false);
    }
  }

  const porLinea: Record<LineaNegocio, StockItem[]> = { MOBILITY: [], INDUSTRY: [], AMBAS: [] };
  for (const item of items) porLinea[item.linea_negocio].push(item);

  return (
    <AppShell>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <div>
          <h1 className="page-title">Stock</h1>
          <p className="page-subtitle">Mobility + Industry · Control de entradas y disponibilidad</p>
        </div>
        <button className="btn-primary" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancelar" : "+ Registrar entrada"}
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {showForm && (
        <div className="card">
          <h2 className="card-title">Registrar entrada</h2>
          <form onSubmit={handleSubmit}>
            <div className="form-grid">
              <div className="form-field">
                <label htmlFor="linea_negocio">Línea de negocio</label>
                <select
                  id="linea_negocio"
                  value={form.linea_negocio}
                  onChange={(e) => setForm({ ...form, linea_negocio: e.target.value as LineaNegocio })}
                >
                  <option value="MOBILITY">{LINE_LABELS.MOBILITY}</option>
                  <option value="INDUSTRY">{LINE_LABELS.INDUSTRY}</option>
                </select>
              </div>
              <div className="form-field">
                <label htmlFor="tipo_producto">Referencia</label>
                <input
                  id="tipo_producto"
                  placeholder="Ej. SSE Recta"
                  value={form.tipo_producto}
                  onChange={(e) => setForm({ ...form, tipo_producto: e.target.value })}
                />
              </div>
              <div className="form-field">
                <label htmlFor="cantidad">Cantidad</label>
                <input
                  id="cantidad"
                  type="number"
                  min={1}
                  value={form.cantidad}
                  onChange={(e) => setForm({ ...form, cantidad: e.target.value })}
                />
              </div>
              <div className="form-field">
                <label htmlFor="nombre">Nombre (si es referencia nueva)</label>
                <input
                  id="nombre"
                  value={form.nombre}
                  onChange={(e) => setForm({ ...form, nombre: e.target.value })}
                />
              </div>
              <div className="form-field">
                <label htmlFor="color">Color</label>
                <input id="color" value={form.color} onChange={(e) => setForm({ ...form, color: e.target.value })} />
              </div>
              <div className="form-field">
                <label htmlFor="unidad">Unidad</label>
                <input
                  id="unidad"
                  value={form.unidad}
                  onChange={(e) => setForm({ ...form, unidad: e.target.value })}
                />
              </div>
            </div>
            <button type="submit" className="btn-primary" style={{ marginTop: 16 }} disabled={saving}>
              {saving ? "Guardando..." : "Registrar entrada"}
            </button>
          </form>
        </div>
      )}

      {(["MOBILITY", "INDUSTRY"] as LineaNegocio[]).map((linea) => (
        <div className="card" key={linea}>
          <h2 className="card-title">{LINE_LABELS[linea]}</h2>
          {porLinea[linea].length === 0 ? (
            <p style={{ color: "var(--mactral-text-muted)", fontSize: 13 }}>Sin referencias registradas.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Referencia</th>
                  <th>Color</th>
                  <th>Disponible</th>
                  <th>Total</th>
                  <th>Último movimiento</th>
                </tr>
              </thead>
              <tbody>
                {porLinea[linea].map((item) => (
                  <tr key={item.id}>
                    <td>{item.nombre ?? item.tipo_producto}</td>
                    <td>{item.color ?? "—"}</td>
                    <td>
                      {item.cantidad_disponible} {item.unidad}
                      {item.cantidad_disponible === 0 && (
                        <span className="badge badge-status-inactivo" style={{ marginLeft: 8 }}>
                          Agotado
                        </span>
                      )}
                    </td>
                    <td>{item.cantidad_total}</td>
                    <td>
                      {item.ultimo_movimiento
                        ? `${new Date(item.ultimo_movimiento.fecha).toLocaleDateString("es-CO")} — ${
                            item.ultimo_movimiento.tipo === "ENTRADA" ? "entrada" : "venta"
                          }${item.ultimo_movimiento.referencia_crp ? ` ${item.ultimo_movimiento.referencia_crp}` : ""}`
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      ))}
    </AppShell>
  );
}
