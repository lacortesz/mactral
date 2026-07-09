import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, apiFetch } from "../api/client";
import AppShell from "../components/AppShell";
import { useAuth } from "../context/AuthContext";
import {
  LINE_LABELS,
  ROLE_LABELS,
  type EstadoUsuario,
  type LineaNegocio,
  type Rol,
} from "../domain";

type UserRow = {
  id: string;
  name: string;
  email: string;
  role: Rol;
  linea_negocio: LineaNegocio;
  status: EstadoUsuario;
  last_access_at: string | null;
};

const EMPTY_FORM = {
  name: "",
  email: "",
  role: "COMERCIAL" as Rol,
  linea_negocio: "MOBILITY" as LineaNegocio,
};

export default function UsuariosPage() {
  const { token, user, accessibleModules } = useAuth();
  const navigate = useNavigate();
  const [users, setUsers] = useState<UserRow[]>([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState<string | null>(null);
  const [successLink, setSuccessLink] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    // Escenario 3 (E1-H2): acceso directo por URL a un módulo no autorizado
    // ("administracion" solo está en la lista de Gerencia).
    if (!accessibleModules.includes("administracion")) {
      navigate("/dashboard?denied=1", { replace: true });
    }
  }, [accessibleModules, navigate]);

  useEffect(() => {
    if (!token) return;
    apiFetch<UserRow[]>("/users", { token })
      .then(setUsers)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) {
          navigate("/dashboard?denied=1", { replace: true });
        }
      });
  }, [token, navigate]);

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSuccessLink(null);
    setSubmitting(true);
    try {
      const created = await apiFetch<UserRow & { activation_link: string }>("/users", {
        method: "POST",
        token,
        body: form,
      });
      setUsers((prev) => [created, ...prev]);
      setSuccessLink(created.activation_link);
      setForm(EMPTY_FORM);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el usuario");
    } finally {
      setSubmitting(false);
    }
  }

  async function toggleStatus(row: UserRow) {
    const nextStatus: EstadoUsuario = row.status === "ACTIVO" ? "INACTIVO" : "ACTIVO";
    const confirmed = window.confirm(
      nextStatus === "INACTIVO"
        ? `¿Desactivar la cuenta de ${row.name}? No podrá iniciar sesión.`
        : `¿Reactivar la cuenta de ${row.name}?`
    );
    if (!confirmed) return;

    try {
      const updated = await apiFetch<UserRow>(`/users/${row.id}`, {
        method: "PATCH",
        token,
        body: { status: nextStatus },
      });
      setUsers((prev) => prev.map((u) => (u.id === row.id ? { ...u, status: updated.status } : u)));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo actualizar el usuario");
    }
  }

  return (
    <AppShell>
      <h1 className="page-title">Gestión de usuarios</h1>
      <p className="page-subtitle">
        {user && `${ROLE_LABELS[user.role]} · Control de acceso por módulo y rol`}
      </p>

      <div className="card">
        <h2 className="card-title">Nuevo usuario</h2>
        {error && <div className="alert alert-error">{error}</div>}
        {successLink && (
          <div className="alert alert-success">
            Usuario creado. Enlace de activación (simulado, revisar logs del backend):{" "}
            <a href={successLink}>{successLink}</a>
          </div>
        )}
        <form onSubmit={handleCreate}>
          <div className="form-grid">
            <div className="form-field full">
              <label htmlFor="name">Nombre completo</label>
              <input
                id="name"
                required
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </div>
            <div className="form-field full">
              <label htmlFor="email">Correo electrónico</label>
              <input
                id="email"
                type="email"
                required
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
              />
            </div>
            <div className="form-field">
              <label htmlFor="role">Rol</label>
              <select
                id="role"
                value={form.role}
                onChange={(e) => setForm({ ...form, role: e.target.value as Rol })}
              >
                {Object.entries(ROLE_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
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
                {Object.entries(LINE_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <button
            type="submit"
            className="btn-primary"
            style={{ width: "100%", marginTop: 16 }}
            disabled={submitting}
          >
            {submitting ? "Creando..." : "Crear usuario"}
          </button>
        </form>
      </div>

      <div className="card">
        <h2 className="card-title">Usuarios</h2>
        <table>
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Correo</th>
              <th>Rol</th>
              <th>Línea</th>
              <th>Estado</th>
              <th>Último acceso</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {users.map((row) => (
              <tr key={row.id}>
                <td>{row.name}</td>
                <td>{row.email}</td>
                <td>
                  <span className="badge badge-role">{ROLE_LABELS[row.role]}</span>
                </td>
                <td>
                  <span className="badge badge-line">{LINE_LABELS[row.linea_negocio]}</span>
                </td>
                <td>
                  <span
                    className={`badge ${
                      row.status === "ACTIVO" ? "badge-status-activo" : "badge-status-inactivo"
                    }`}
                  >
                    {row.status === "ACTIVO" ? "Activo" : "Inactivo"}
                  </span>
                </td>
                <td>
                  {row.last_access_at
                    ? new Date(row.last_access_at).toLocaleDateString("es-CO")
                    : "—"}
                </td>
                <td>
                  <button className="btn-link" onClick={() => toggleStatus(row)}>
                    {row.status === "ACTIVO" ? "Desactivar" : "Activar"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </AppShell>
  );
}
