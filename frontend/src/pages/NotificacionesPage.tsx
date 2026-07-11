import { useEffect, useState } from "react";
import { ApiError, projectsApiFetch } from "../api/client";
import AppShell from "../components/AppShell";
import { useAuth } from "../context/AuthContext";
import { MODULE_LABELS, moduleRoute, type ModuleKey } from "../domain";

type Notificacion = {
  id: string;
  crp_code: string;
  modulo: ModuleKey;
  tipo: "ASIGNACION" | "INACTIVIDAD";
  mensaje: string;
  fecha: string;
  leida: boolean;
};

const TIPO_LABELS: Record<Notificacion["tipo"], string> = {
  ASIGNACION: "Asignación",
  INACTIVIDAD: "Inactividad",
};

export default function NotificacionesPage() {
  const { token } = useAuth();
  const [notificaciones, setNotificaciones] = useState<Notificacion[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [marcando, setMarcando] = useState<string | null>(null);

  async function load() {
    setError(null);
    try {
      const found = await projectsApiFetch<Notificacion[]>("/notificaciones", { token });
      setNotificaciones(found);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar las notificaciones");
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleMarcarLeida(id: string) {
    setMarcando(id);
    try {
      await projectsApiFetch(`/notificaciones/${id}/leer`, { method: "PATCH", token });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo marcar la notificación como leída");
    } finally {
      setMarcando(null);
    }
  }

  return (
    <AppShell>
      <h1 className="page-title">Notificaciones</h1>
      <p className="page-subtitle">Asignaciones de proyectos a módulo y alertas de inactividad</p>

      <div className="card">
        {error && <div className="alert alert-error">{error}</div>}
        {notificaciones && notificaciones.length === 0 && (
          <p style={{ color: "var(--mactral-text-muted)", fontSize: 13 }}>No tienes notificaciones pendientes.</p>
        )}
        {notificaciones && notificaciones.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Tipo</th>
                <th>Módulo</th>
                <th>Mensaje</th>
                <th>Fecha</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {notificaciones.map((n) => (
                <tr key={n.id} style={n.tipo === "INACTIVIDAD" ? { background: "var(--mactral-red-bg)" } : undefined}>
                  <td>{TIPO_LABELS[n.tipo]}</td>
                  <td>{MODULE_LABELS[n.modulo] ?? n.modulo}</td>
                  <td>
                    <a href={moduleRoute(n.modulo)}>{n.mensaje}</a>
                  </td>
                  <td>{new Date(n.fecha).toLocaleString("es-CO")}</td>
                  <td>
                    <button
                      className="btn-link"
                      disabled={marcando === n.id}
                      onClick={() => handleMarcarLeida(n.id)}
                    >
                      {marcando === n.id ? "..." : "Marcar leída"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </AppShell>
  );
}
