import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, projectsApiFetch } from "../api/client";
import AppShell from "../components/AppShell";
import { useAuth } from "../context/AuthContext";
import { ESTADO_ETAPA_LABELS, MODULE_LABELS, type EstadoEtapa, type ModuleKey, type SemaforoColor } from "../domain";

type SearchResult = {
  id: string;
  crp_code: string;
  cliente: string;
  ciudad: string;
  etapa_actual: EstadoEtapa;
  semaforo_color: SemaforoColor;
};

type ModuleStatus = {
  modulo: ModuleKey;
  estado: EstadoEtapa;
  bloqueado_por_cierre: boolean;
  editable_por_mi_rol: boolean;
};

type TimelineEvent = {
  fecha: string;
  origen: string;
  mensaje: string;
};

type ProjectDetail = {
  id: string;
  crp_code: string;
  tipo: string;
  cliente: string;
  ciudad: string;
  producto: string;
  marca: string;
  etapa_actual: EstadoEtapa;
  semaforo_color: SemaforoColor;
  semaforo_detalle: string;
  modulos: ModuleStatus[];
  linea_de_tiempo: TimelineEvent[];
};

type Comentario = {
  id: string;
  autor_nombre: string;
  mensaje: string;
  fecha: string;
  menciones: string[];
};

function renderMensajeConMenciones(mensaje: string) {
  const partes = mensaje.split(/(@\w+)/g);
  return partes.map((parte, i) =>
    parte.startsWith("@") ? (
      <strong key={i} style={{ color: "var(--mactral-yellow-dark)" }}>
        {parte}
      </strong>
    ) : (
      <span key={i}>{parte}</span>
    )
  );
}

const SEMAFORO_COLORS: Record<SemaforoColor, string> = {
  VERDE: "var(--mactral-green)",
  AMARILLO: "var(--mactral-yellow-dark)",
  ROJO: "var(--mactral-red)",
};

export default function RegMaestroPage() {
  const { token, accessibleModules } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    // Defensa en profundidad: hoy todos los roles tienen "reg-maestro",
    // pero si eso cambia, este guard evita mostrar la página igualmente.
    if (!accessibleModules.includes("reg-maestro")) {
      navigate("/dashboard?denied=1", { replace: true });
    }
  }, [accessibleModules, navigate]);

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [selected, setSelected] = useState<ProjectDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const [comentarios, setComentarios] = useState<Comentario[] | null>(null);
  const [nuevoComentario, setNuevoComentario] = useState("");
  const [comentarioError, setComentarioError] = useState<string | null>(null);
  const [enviandoComentario, setEnviandoComentario] = useState(false);

  async function loadComentarios(crpCode: string) {
    const found = await projectsApiFetch<Comentario[]>(
      `/projects/${encodeURIComponent(crpCode)}/comentarios`,
      { token }
    );
    setComentarios(found);
  }

  async function handleAgregarComentario(event: FormEvent) {
    event.preventDefault();
    if (!selected || !nuevoComentario.trim()) return;
    setComentarioError(null);
    setEnviandoComentario(true);
    try {
      await projectsApiFetch(`/projects/${encodeURIComponent(selected.crp_code)}/comentarios`, {
        method: "POST",
        token,
        body: { mensaje: nuevoComentario },
      });
      setNuevoComentario("");
      await loadComentarios(selected.crp_code);
    } catch (err) {
      setComentarioError(err instanceof ApiError ? err.message : "No se pudo publicar el comentario");
    } finally {
      setEnviandoComentario(false);
    }
  }

  async function handleSearch(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSelected(null);
    setLoading(true);
    try {
      const found = await projectsApiFetch<SearchResult[]>(
        `/projects/search?q=${encodeURIComponent(query)}`,
        { token }
      );
      setResults(found);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo buscar el proyecto");
    } finally {
      setLoading(false);
    }
  }

  async function handleSelect(crpCode: string) {
    setError(null);
    try {
      const detail = await projectsApiFetch<ProjectDetail>(
        `/projects/${encodeURIComponent(crpCode)}`,
        { token }
      );
      setSelected(detail);
      await loadComentarios(crpCode);
    } catch (err) {
      // Escenario 2 (E1-H3): proyecto no encontrado.
      setError(err instanceof ApiError ? err.message : "No se pudo abrir el proyecto");
    }
  }

  return (
    <AppShell>
      <h1 className="page-title">Registro maestro</h1>
      <p className="page-subtitle">Ficha central del proyecto (CRP)</p>

      <div className="card">
        <h2 className="card-title">Buscar proyecto</h2>
        <form onSubmit={handleSearch} style={{ display: "flex", gap: 10 }}>
          <input
            style={{ flex: 1, border: "1px solid var(--mactral-border)", borderRadius: 6, padding: "9px 10px" }}
            placeholder="Código CRP o nombre de cliente..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? "Buscando..." : "Buscar"}
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
                <th>Estado</th>
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
                    {ESTADO_ETAPA_LABELS[r.etapa_actual]} ·{" "}
                    <span style={{ color: SEMAFORO_COLORS[r.semaforo_color], fontWeight: 700 }}>
                      {r.semaforo_color === "VERDE" ? "Verde" : r.semaforo_color === "AMARILLO" ? "Amarillo" : "Rojo"}
                    </span>
                  </td>
                  <td>
                    <button className="btn-link" onClick={() => handleSelect(r.crp_code)}>
                      Ver ficha
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {selected && (
        <>
          <div className="card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", flexWrap: "wrap", gap: 8 }}>
              <h2 style={{ margin: 0 }}>{selected.crp_code}</h2>
              <div style={{ fontSize: 13, color: "var(--mactral-text-muted)" }}>
                {selected.tipo} · {ESTADO_ETAPA_LABELS[selected.etapa_actual]} ·{" "}
                <span style={{ color: SEMAFORO_COLORS[selected.semaforo_color], fontWeight: 700 }}>
                  {selected.semaforo_color === "VERDE"
                    ? "Verde"
                    : selected.semaforo_color === "AMARILLO"
                      ? "Amarillo"
                      : "Rojo"}
                </span>{" "}
                — {selected.semaforo_detalle}
              </div>
            </div>

            <h3 className="card-title" style={{ marginTop: 20 }}>
              Datos del proyecto
            </h3>
            <div className="form-grid">
              <div className="form-field">
                <label>Código CRP</label>
                <div>{selected.crp_code}</div>
              </div>
              <div className="form-field">
                <label>Tipo</label>
                <div>{selected.tipo}</div>
              </div>
              <div className="form-field">
                <label>Cliente</label>
                <div>{selected.cliente}</div>
              </div>
              <div className="form-field">
                <label>Ciudad</label>
                <div>{selected.ciudad}</div>
              </div>
              <div className="form-field">
                <label>Producto</label>
                <div>{selected.producto}</div>
              </div>
              <div className="form-field">
                <label>Marca</label>
                <div>{selected.marca}</div>
              </div>
            </div>
          </div>

          <div className="card">
            <h2 className="card-title">Estado de módulos</h2>
            <table>
              <tbody>
                {selected.modulos.map((m) => (
                  <tr key={m.modulo}>
                    <td>{MODULE_LABELS[m.modulo]}</td>
                    <td>
                      <span
                        className={`badge ${
                          m.estado === "CERRADO"
                            ? "badge-status-activo"
                            : m.estado === "BLOQUEADO"
                              ? "badge-status-inactivo"
                              : "badge-role"
                        }`}
                      >
                        {/* Restricción E1-H3: etapas cerradas quedan bloqueadas con candado. */}
                        {m.bloqueado_por_cierre && "🔒 "}
                        {ESTADO_ETAPA_LABELS[m.estado]}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="card">
            <h2 className="card-title">Línea de tiempo</h2>
            {selected.linea_de_tiempo.length === 0 ? (
              <p style={{ color: "var(--mactral-text-muted)", fontSize: 13 }}>Sin eventos registrados.</p>
            ) : (
              <ul style={{ listStyle: "none", margin: 0, padding: 0, fontSize: 13 }}>
                {selected.linea_de_tiempo.map((e, i) => (
                  <li
                    key={i}
                    style={{ padding: "8px 0", borderBottom: "1px solid var(--mactral-border)" }}
                  >
                    <strong>{new Date(e.fecha).toLocaleDateString("es-CO")}</strong>{" "}
                    <span className="badge badge-role">{e.origen}</span> {e.mensaje}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="card">
            <h2 className="card-title">Comentarios</h2>
            {comentarioError && <div className="alert alert-error">{comentarioError}</div>}
            <form onSubmit={handleAgregarComentario} style={{ display: "flex", gap: 10, marginBottom: 16 }}>
              <input
                style={{ flex: 1, border: "1px solid var(--mactral-border)", borderRadius: 6, padding: "9px 10px" }}
                placeholder="Escribe un comentario... usa @usuario para mencionar"
                value={nuevoComentario}
                onChange={(e) => setNuevoComentario(e.target.value)}
              />
              <button type="submit" className="btn-primary" disabled={enviandoComentario || !nuevoComentario.trim()}>
                {enviandoComentario ? "Publicando..." : "Comentar"}
              </button>
            </form>

            {comentarios && comentarios.length === 0 ? (
              <p style={{ color: "var(--mactral-text-muted)", fontSize: 13 }}>Sin comentarios todavía.</p>
            ) : (
              <ul style={{ listStyle: "none", margin: 0, padding: 0, fontSize: 13 }}>
                {comentarios?.map((c) => (
                  <li key={c.id} style={{ padding: "8px 0", borderBottom: "1px solid var(--mactral-border)" }}>
                    <strong>{c.autor_nombre}</strong>{" "}
                    <span style={{ color: "var(--mactral-text-muted)" }}>
                      {new Date(c.fecha).toLocaleString("es-CO")}
                    </span>
                    <div>{renderMensajeConMenciones(c.mensaje)}</div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}
    </AppShell>
  );
}
