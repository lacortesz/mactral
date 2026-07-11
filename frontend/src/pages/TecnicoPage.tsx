import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, projectsApiFetch, projectsApiFetchMultipart, projectsFetchBlob } from "../api/client";
import AppShell from "../components/AppShell";
import { useAuth } from "../context/AuthContext";
import { ESTADO_INSTALACION_LABELS, type EstadoInstalacion } from "../domain";

type SearchResult = {
  id: string;
  crp_code: string;
  cliente: string;
  ciudad: string;
};

type Reprogramming = {
  fecha_anterior: string;
  fecha_nueva: string;
  motivo: string;
  usuario_nombre: string;
  fecha_cambio: string;
};

type Installation = {
  fecha_instalacion: string;
  tecnico_nombre: string;
  ciudad: string;
  estado: EstadoInstalacion;
  historial: Reprogramming[];
  fecha_real_entrega: string | null;
  tiene_acta: boolean;
  observaciones: string | null;
};

type ModuleStatus = {
  modulo: string;
  estado: "PENDIENTE" | "EN_CURSO" | "CERRADO" | "BLOQUEADO";
};

type ProjectDetail = {
  crp_code: string;
  cliente: string;
  ciudad: string;
  modulos: ModuleStatus[];
  instalacion: Installation | null;
};

const EMPTY_PROGRAM_FORM = { fecha_instalacion: "", tecnico_id: "", tecnico_nombre: "", ciudad: "" };

export default function TecnicoPage() {
  const { token, user, accessibleModules } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!accessibleModules.includes("tecnico")) {
      navigate("/dashboard?denied=1", { replace: true });
    }
  }, [accessibleModules, navigate]);

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [selected, setSelected] = useState<ProjectDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [programForm, setProgramForm] = useState(EMPTY_PROGRAM_FORM);
  const [programError, setProgramError] = useState<string | null>(null);
  const [programSaving, setProgramSaving] = useState(false);

  const [reprogramFecha, setReprogramFecha] = useState("");
  const [reprogramMotivo, setReprogramMotivo] = useState("");
  const [reprogramError, setReprogramError] = useState<string | null>(null);
  const [reprogramSaving, setReprogramSaving] = useState(false);

  const [actaFecha, setActaFecha] = useState("");
  const [actaObservaciones, setActaObservaciones] = useState("");
  const [actaFile, setActaFile] = useState<File | null>(null);
  const [actaError, setActaError] = useState<string | null>(null);
  const [actaSaving, setActaSaving] = useState(false);

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
      setProgramForm({ ...EMPTY_PROGRAM_FORM, tecnico_id: user?.id ?? "", tecnico_nombre: user?.name ?? "" });
      setProgramError(null);
      setReprogramError(null);
      setReprogramFecha(detail.instalacion?.fecha_instalacion ?? "");
      setReprogramMotivo("");
      setActaFecha("");
      setActaObservaciones("");
      setActaFile(null);
      setActaError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo abrir el proyecto");
    }
  }

  async function handleProgramar(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    setProgramError(null);
    setProgramSaving(true);
    try {
      await projectsApiFetch(`/projects/${encodeURIComponent(selected.crp_code)}/instalacion`, {
        method: "POST",
        token,
        body: programForm,
      });
      await openProject(selected.crp_code);
    } catch (err) {
      setProgramError(err instanceof ApiError ? err.message : "No se pudo programar la instalación");
    } finally {
      setProgramSaving(false);
    }
  }

  async function handleReprogramar(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    setReprogramError(null);
    setReprogramSaving(true);
    try {
      await projectsApiFetch(`/projects/${encodeURIComponent(selected.crp_code)}/instalacion`, {
        method: "PATCH",
        token,
        body: { fecha_instalacion: reprogramFecha, motivo: reprogramMotivo },
      });
      setReprogramMotivo("");
      await openProject(selected.crp_code);
    } catch (err) {
      setReprogramError(err instanceof ApiError ? err.message : "No se pudo reprogramar la instalación");
    } finally {
      setReprogramSaving(false);
    }
  }

  async function handleRegistrarActa(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    setActaError(null);
    setActaSaving(true);
    try {
      const formData = new FormData();
      formData.append("fecha_real_entrega", actaFecha);
      if (actaObservaciones) formData.append("observaciones", actaObservaciones);
      if (actaFile) formData.append("acta", actaFile);

      await projectsApiFetchMultipart(
        `/projects/${encodeURIComponent(selected.crp_code)}/instalacion/acta`,
        formData,
        token
      );
      // Escenario 2 (E5-H2): no adjuntar el acta no bloquea el registro; el
      // recordatorio persistente se ve más abajo (selected.instalacion.tiene_acta).
      await openProject(selected.crp_code);
    } catch (err) {
      setActaError(err instanceof ApiError ? err.message : "No se pudo registrar el acta de entrega");
    } finally {
      setActaSaving(false);
    }
  }

  async function handleViewActa() {
    if (!selected) return;
    const tab = window.open("", "_blank");
    try {
      const blob = await projectsFetchBlob(
        `/projects/${encodeURIComponent(selected.crp_code)}/instalacion/acta`,
        token
      );
      const url = URL.createObjectURL(blob);
      if (tab) tab.location.href = url;
    } catch (err) {
      tab?.close();
      setActaError(err instanceof ApiError ? err.message : "No se pudo abrir el acta");
    }
  }

  return (
    <AppShell>
      <h1 className="page-title">Técnico</h1>
      <p className="page-subtitle">Programación de instalación y entrega</p>

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
                      Ver instalación
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

          {!selected.instalacion ? (
            <>
              {programError && <div className="alert alert-error">{programError}</div>}
              <form onSubmit={handleProgramar}>
                <div className="form-grid">
                  <div className="form-field">
                    <label htmlFor="fecha_instalacion">Fecha de instalación</label>
                    <input
                      id="fecha_instalacion"
                      type="date"
                      value={programForm.fecha_instalacion}
                      onChange={(e) => setProgramForm({ ...programForm, fecha_instalacion: e.target.value })}
                    />
                  </div>
                  <div className="form-field">
                    <label htmlFor="tecnico_nombre">Técnico asignado</label>
                    <input
                      id="tecnico_nombre"
                      value={programForm.tecnico_nombre}
                      onChange={(e) => setProgramForm({ ...programForm, tecnico_nombre: e.target.value })}
                    />
                  </div>
                  <div className="form-field">
                    <label htmlFor="ciudad_instalacion">Ciudad</label>
                    <input
                      id="ciudad_instalacion"
                      value={programForm.ciudad}
                      onChange={(e) => setProgramForm({ ...programForm, ciudad: e.target.value })}
                    />
                  </div>
                </div>
                <button type="submit" className="btn-primary" style={{ marginTop: 16 }} disabled={programSaving}>
                  {programSaving ? "Guardando..." : "Programar instalación"}
                </button>
              </form>
            </>
          ) : (
            <>
              <p>
                <strong>Estado:</strong> {ESTADO_INSTALACION_LABELS[selected.instalacion.estado]} ·{" "}
                <strong>Fecha:</strong>{" "}
                {new Date(selected.instalacion.fecha_instalacion + "T00:00:00").toLocaleDateString("es-CO")} ·{" "}
                <strong>Técnico:</strong> {selected.instalacion.tecnico_nombre} ·{" "}
                <strong>Ciudad:</strong> {selected.instalacion.ciudad}
              </p>

              {selected.instalacion.historial.length > 0 && (
                <>
                  <h3 className="card-title">Historial de reprogramaciones</h3>
                  <ul style={{ listStyle: "none", margin: "0 0 16px", padding: 0, fontSize: 13 }}>
                    {selected.instalacion.historial.map((h, idx) => (
                      <li key={idx} style={{ padding: "8px 0", borderBottom: "1px solid var(--mactral-border)" }}>
                        {new Date(h.fecha_cambio).toLocaleString("es-CO")} —{" "}
                        {new Date(h.fecha_anterior + "T00:00:00").toLocaleDateString("es-CO")} →{" "}
                        {new Date(h.fecha_nueva + "T00:00:00").toLocaleDateString("es-CO")}: {h.motivo} (
                        {h.usuario_nombre})
                      </li>
                    ))}
                  </ul>
                </>
              )}

              {selected.instalacion.estado === "PROGRAMADO" && (
                <>
                  {reprogramError && <div className="alert alert-error">{reprogramError}</div>}
                  <form onSubmit={handleReprogramar}>
                    <h3 className="card-title">Reprogramar</h3>
                    <div className="form-grid">
                      <div className="form-field">
                        <label htmlFor="reprogram_fecha">Nueva fecha</label>
                        <input
                          id="reprogram_fecha"
                          type="date"
                          value={reprogramFecha}
                          onChange={(e) => setReprogramFecha(e.target.value)}
                        />
                      </div>
                      <div className="form-field full">
                        <label htmlFor="reprogram_motivo">Motivo</label>
                        <input
                          id="reprogram_motivo"
                          placeholder="Motivo del aplazamiento..."
                          value={reprogramMotivo}
                          onChange={(e) => setReprogramMotivo(e.target.value)}
                        />
                      </div>
                    </div>
                    <button
                      type="submit"
                      className="btn-primary"
                      style={{ marginTop: 16 }}
                      disabled={reprogramSaving}
                    >
                      {reprogramSaving ? "Guardando..." : "Reprogramar"}
                    </button>
                  </form>

                  <h3 className="card-title" style={{ marginTop: 20 }}>
                    Registro del acta de entrega
                  </h3>
                  {actaError && <div className="alert alert-error">{actaError}</div>}
                  <form onSubmit={handleRegistrarActa}>
                    <div className="form-grid">
                      <div className="form-field">
                        <label htmlFor="acta_fecha">Fecha real de firma del acta</label>
                        <input
                          id="acta_fecha"
                          type="date"
                          value={actaFecha}
                          onChange={(e) => setActaFecha(e.target.value)}
                        />
                      </div>
                      <div className="form-field full">
                        <label htmlFor="acta_observaciones">Observaciones técnicas</label>
                        <input
                          id="acta_observaciones"
                          placeholder="Observaciones (opcional)..."
                          value={actaObservaciones}
                          onChange={(e) => setActaObservaciones(e.target.value)}
                        />
                      </div>
                      <div className="form-field full">
                        <label htmlFor="acta_archivo">Acta de entrega firmada (PDF/JPG)</label>
                        <input
                          id="acta_archivo"
                          type="file"
                          onChange={(e) => setActaFile(e.target.files?.[0] ?? null)}
                        />
                      </div>
                    </div>
                    <button type="submit" className="btn-primary" style={{ marginTop: 16 }} disabled={actaSaving}>
                      {actaSaving ? "Registrando..." : "Registrar acta y cerrar proyecto técnico"}
                    </button>
                  </form>
                </>
              )}

              {selected.instalacion.estado === "COMPLETADO" && (
                <div style={{ marginTop: 16 }}>
                  {!selected.instalacion.tiene_acta && (
                    <div className="alert alert-error">El acta no fue adjuntada. Recuerda subirla.</div>
                  )}
                  <p>
                    <strong>Fecha real de entrega:</strong>{" "}
                    {selected.instalacion.fecha_real_entrega &&
                      new Date(selected.instalacion.fecha_real_entrega + "T00:00:00").toLocaleDateString("es-CO")}
                    {selected.instalacion.observaciones && (
                      <>
                        {" "}
                        · <strong>Observaciones:</strong> {selected.instalacion.observaciones}
                      </>
                    )}
                  </p>
                  {selected.instalacion.tiene_acta && (
                    <button className="btn-link" onClick={handleViewActa}>
                      Ver acta de entrega
                    </button>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </AppShell>
  );
}
