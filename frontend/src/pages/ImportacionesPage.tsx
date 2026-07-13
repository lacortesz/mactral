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
import {
  ESTADO_ITEM_CHECKLIST_LABELS,
  type EstadoItemChecklist,
  type TipoItemChecklist,
} from "../domain";

type SearchResult = {
  id: string;
  crp_code: string;
  cliente: string;
  ciudad: string;
};

type ChecklistItem = {
  numero: string;
  nombre: string;
  tipo: TipoItemChecklist;
  estado: EstadoItemChecklist;
  fecha: string | null;
  nota: string | null;
  tiene_adjunto: boolean;
};

type ModuleStatus = {
  modulo: string;
  estado: "PENDIENTE" | "EN_CURSO" | "CERRADO" | "BLOQUEADO";
};

type ProjectDetail = {
  crp_code: string;
  cliente: string;
  ciudad: string;
  checklist: ChecklistItem[];
  modulos: ModuleStatus[];
};

type ItemFormState = { estado: EstadoItemChecklist; nota: string };

export default function ImportacionesPage() {
  const { token, accessibleModules } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!accessibleModules.includes("importaciones")) {
      navigate("/dashboard?denied=1", { replace: true });
    }
  }, [accessibleModules, navigate]);

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [selected, setSelected] = useState<ProjectDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [itemForms, setItemForms] = useState<Record<string, ItemFormState>>({});
  const [itemFiles, setItemFiles] = useState<Record<string, File | null>>({});
  const [saving, setSaving] = useState<string | null>(null);
  const [itemErrors, setItemErrors] = useState<Record<string, string>>({});
  const [ingresoBodegaNota, setIngresoBodegaNota] = useState("");
  const [transicionError, setTransicionError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function handleSearch(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSelected(null);
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

  async function openProject(crpCode: string) {
    setError(null);
    try {
      const detail = await projectsApiFetch<ProjectDetail>(`/projects/${encodeURIComponent(crpCode)}`, {
        token,
      });
      setSelected(detail);
      const forms: Record<string, ItemFormState> = {};
      for (const item of detail.checklist) {
        forms[item.numero] = { estado: item.estado, nota: item.nota ?? "" };
      }
      setItemForms(forms);
      setItemFiles({});
      setItemErrors({});
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo abrir el proyecto");
    }
  }

  async function handleSaveItem(numero: string) {
    if (!selected) return;
    const form = itemForms[numero];
    setSaving(numero);
    setItemErrors((prev) => ({ ...prev, [numero]: "" }));
    try {
      const formData = new FormData();
      formData.append("estado", form.estado);
      if (form.nota) formData.append("nota", form.nota);
      const file = itemFiles[numero];
      if (file) formData.append("archivo", file);

      await projectsApiFetchMultipart(
        `/projects/${encodeURIComponent(selected.crp_code)}/checklist/${numero}`,
        formData,
        token
      );
      await openProject(selected.crp_code);
    } catch (err) {
      setItemErrors((prev) => ({
        ...prev,
        [numero]: err instanceof ApiError ? err.message : "No se pudo actualizar el ítem",
      }));
    } finally {
      setSaving(null);
    }
  }

  async function handleEnviarTecnico(nota?: string) {
    if (!selected) return;
    setEnviando(true);
    setTransicionError(null);
    try {
      await projectsApiFetch(`/projects/${encodeURIComponent(selected.crp_code)}/enviar-tecnico`, {
        method: "POST",
        token,
        body: nota ? { ingreso_bodega_nota: nota } : {},
      });
      await openProject(selected.crp_code);
      setIngresoBodegaNota("");
    } catch (err) {
      setTransicionError(err instanceof ApiError ? err.message : "No se pudo enviar el proyecto a Técnico");
    } finally {
      setEnviando(false);
    }
  }

  async function handleViewAttachment(numero: string) {
    if (!selected) return;
    const tab = window.open("", "_blank");
    try {
      const blob = await projectsFetchBlob(
        `/projects/${encodeURIComponent(selected.crp_code)}/checklist/${numero}/adjunto`,
        token
      );
      const url = URL.createObjectURL(blob);
      if (tab) tab.location.href = url;
    } catch (err) {
      tab?.close();
      setError(err instanceof ApiError ? err.message : "No se pudo abrir el adjunto");
    }
  }

  const requeridosPendientes = selected
    ? selected.checklist.filter((i) => i.tipo === "REQUERIDO" && i.estado === "PENDIENTE")
    : [];
  const completados = selected
    ? selected.checklist.filter((i) => i.estado !== "PENDIENTE").length
    : 0;

  return (
    <AppShell>
      <h1 className="page-title">Importaciones</h1>
      <p className="page-subtitle">Checklist documental de importación (proyectos GM)</p>

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

        {error && (
          <div className="alert alert-error" style={{ marginTop: 14 }}>
            {error}
          </div>
        )}

        {results && results.length === 0 && !error && (
          <div className="alert alert-error" style={{ marginTop: 14 }}>
            No se encontraron proyectos con ese criterio
          </div>
        )}

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
                    <button className="btn-link" onClick={() => openProject(r.crp_code)}>
                      Ver checklist
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
            {selected.crp_code} · {selected.cliente} — {completados}/{selected.checklist.length} docs
          </h2>

          {selected.checklist.length === 0 ? (
            <p style={{ color: "var(--mactral-text-muted)", fontSize: 13 }}>
              Este proyecto no tiene checklist de importación (solo aplica a proyectos GM).
            </p>
          ) : (
            <>
              {requeridosPendientes.length > 0 && (
                <div className="alert alert-error" style={{ marginBottom: 14 }}>
                  {requeridosPendientes.length} documento(s) requerido(s) pendiente(s):{" "}
                  {requeridosPendientes.map((i) => i.nombre).join(", ")}
                </div>
              )}

              <table>
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Documento</th>
                    <th>Tipo</th>
                    <th>Estado</th>
                    <th>Nota</th>
                    <th>Adjunto</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {selected.checklist.map((item) => {
                    const form = itemForms[item.numero] ?? { estado: item.estado, nota: item.nota ?? "" };
                    const requiereNota = form.estado === "NO_APLICA";
                    return (
                      <tr
                        key={item.numero}
                        style={
                          item.tipo === "REQUERIDO" && item.estado === "PENDIENTE"
                            ? { background: "var(--mactral-red-bg)" }
                            : undefined
                        }
                      >
                        <td>{item.numero}</td>
                        <td>{item.nombre}</td>
                        <td>{item.tipo === "REQUERIDO" ? "Requerido" : "Opcional"}</td>
                        <td>
                          <select
                            value={form.estado}
                            onChange={(e) =>
                              setItemForms((prev) => ({
                                ...prev,
                                [item.numero]: { ...form, estado: e.target.value as EstadoItemChecklist },
                              }))
                            }
                          >
                            <option value="PENDIENTE">{ESTADO_ITEM_CHECKLIST_LABELS.PENDIENTE}</option>
                            <option value="ARCHIVADO">{ESTADO_ITEM_CHECKLIST_LABELS.ARCHIVADO}</option>
                            <option value="NO_APLICA">{ESTADO_ITEM_CHECKLIST_LABELS.NO_APLICA}</option>
                          </select>
                        </td>
                        <td>
                          <input
                            style={{ width: 160 }}
                            placeholder={requiereNota ? "Justificación (obligatoria)" : "Nota (opcional)"}
                            value={form.nota}
                            onChange={(e) =>
                              setItemForms((prev) => ({
                                ...prev,
                                [item.numero]: { ...form, nota: e.target.value },
                              }))
                            }
                          />
                        </td>
                        <td>
                          {item.tiene_adjunto ? (
                            <button className="btn-link" onClick={() => handleViewAttachment(item.numero)}>
                              Ver adjunto
                            </button>
                          ) : (
                            <input
                              type="file"
                              onChange={(e) =>
                                setItemFiles((prev) => ({
                                  ...prev,
                                  [item.numero]: e.target.files?.[0] ?? null,
                                }))
                              }
                            />
                          )}
                        </td>
                        <td>
                          <button
                            className="btn-primary"
                            disabled={saving === item.numero}
                            onClick={() => handleSaveItem(item.numero)}
                          >
                            {saving === item.numero ? "Guardando..." : "Guardar"}
                          </button>
                          {itemErrors[item.numero] && (
                            <div style={{ color: "var(--mactral-red)", fontSize: 12, marginTop: 4 }}>
                              {itemErrors[item.numero]}
                            </div>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>

              {(() => {
                const importaciones = selected.modulos.find((m) => m.modulo === "importaciones");
                if (importaciones?.estado === "CERRADO") {
                  return (
                    <div className="alert alert-success" style={{ marginTop: 16 }}>
                      ✓ Checklist cerrado — el proyecto ya avanzó al módulo Técnico.
                    </div>
                  );
                }
                return (
                  <div style={{ marginTop: 16 }}>
                    {transicionError && <div className="alert alert-error">{transicionError}</div>}
                    {requeridosPendientes.length === 0 ? (
                      <button className="btn-primary" disabled={enviando} onClick={() => handleEnviarTecnico()}>
                        {enviando ? "Enviando..." : "Enviar a módulo Técnico"}
                      </button>
                    ) : (
                      <div className="form-field">
                        <label htmlFor="ingreso_bodega_nota">
                          Excepción — ingreso a bodega (nota de justificación obligatoria)
                        </label>
                        <div style={{ display: "flex", gap: 10 }}>
                          <input
                            id="ingreso_bodega_nota"
                            style={{ flex: 1 }}
                            placeholder="Motivo del ingreso sin checklist completo..."
                            value={ingresoBodegaNota}
                            onChange={(e) => setIngresoBodegaNota(e.target.value)}
                          />
                          <button
                            className="btn-primary"
                            disabled={enviando || !ingresoBodegaNota.trim()}
                            title={
                              requeridosPendientes.length > 0
                                ? `Pendientes: ${requeridosPendientes.map((i) => i.nombre).join(", ")}`
                                : undefined
                            }
                            onClick={() => handleEnviarTecnico(ingresoBodegaNota)}
                          >
                            {enviando ? "Registrando..." : "Registrar ingreso a bodega exitoso"}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })()}
            </>
          )}
        </div>
      )}
    </AppShell>
  );
}
