"use client";

import { useState } from "react";

export type Rol =
  | "COMERCIAL"
  | "IMPORTACIONES"
  | "TECNICO"
  | "ADMINISTRATIVO"
  | "GERENCIA";
export type LineaNegocio = "MOBILITY" | "INDUSTRY" | "AMBAS";
export type EstadoUsuario = "ACTIVO" | "INACTIVO";

export type UserRow = {
  id: string;
  name: string;
  email: string;
  role: Rol;
  lineaNegocio: LineaNegocio;
  status: EstadoUsuario;
  lastAccessAt: string | null;
};

const ROLE_LABELS: Record<Rol, string> = {
  COMERCIAL: "Comercial",
  IMPORTACIONES: "Importaciones",
  TECNICO: "Técnico",
  ADMINISTRATIVO: "Administrativo",
  GERENCIA: "Gerencia",
};

const LINE_LABELS: Record<LineaNegocio, string> = {
  MOBILITY: "Mobility",
  INDUSTRY: "Industry",
  AMBAS: "Ambas",
};

const EMPTY_FORM = {
  name: "",
  email: "",
  role: "COMERCIAL" as Rol,
  lineaNegocio: "MOBILITY" as LineaNegocio,
};

export default function UsersClient({
  initialUsers,
  canManage,
}: {
  initialUsers: UserRow[];
  canManage: boolean;
}) {
  const [users, setUsers] = useState(initialUsers);
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState<string | null>(null);
  const [successLink, setSuccessLink] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setSuccessLink(null);
    setSubmitting(true);

    try {
      const response = await fetch("/api/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      const data = await response.json();

      if (!response.ok) {
        setError(data.error ?? "No se pudo crear el usuario");
        return;
      }

      setUsers((prev) => [
        {
          id: data.id,
          name: data.name,
          email: data.email,
          role: data.role,
          lineaNegocio: data.lineaNegocio,
          status: data.status,
          lastAccessAt: null,
        },
        ...prev,
      ]);
      setSuccessLink(data.activationLink);
      setForm(EMPTY_FORM);
    } finally {
      setSubmitting(false);
    }
  }

  async function toggleStatus(user: UserRow) {
    const nextStatus: EstadoUsuario = user.status === "ACTIVO" ? "INACTIVO" : "ACTIVO";
    const confirmed = window.confirm(
      nextStatus === "INACTIVO"
        ? `¿Desactivar la cuenta de ${user.name}? No podrá iniciar sesión.`
        : `¿Reactivar la cuenta de ${user.name}?`
    );
    if (!confirmed) return;

    const response = await fetch(`/api/users/${user.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: nextStatus }),
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      setError(data.error ?? "No se pudo actualizar el usuario");
      return;
    }

    setUsers((prev) =>
      prev.map((u) => (u.id === user.id ? { ...u, status: nextStatus } : u))
    );
  }

  return (
    <>
      {canManage && (
        <div className="card">
          <h2 className="card-title">Nuevo usuario</h2>
          {error && <div className="alert alert-error">{error}</div>}
          {successLink && (
            <div className="alert alert-success">
              Usuario creado. Enlace de activación (simulado, revisar consola del
              servidor): <a href={successLink}>{successLink}</a>
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
                <label htmlFor="lineaNegocio">Línea de negocio</label>
                <select
                  id="lineaNegocio"
                  value={form.lineaNegocio}
                  onChange={(e) =>
                    setForm({ ...form, lineaNegocio: e.target.value as LineaNegocio })
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
      )}

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
              {canManage && <th />}
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id}>
                <td>{user.name}</td>
                <td>{user.email}</td>
                <td>
                  <span className="badge badge-role">{ROLE_LABELS[user.role]}</span>
                </td>
                <td>
                  <span className="badge badge-line">{LINE_LABELS[user.lineaNegocio]}</span>
                </td>
                <td>
                  <span
                    className={`badge ${
                      user.status === "ACTIVO"
                        ? "badge-status-activo"
                        : "badge-status-inactivo"
                    }`}
                  >
                    {user.status === "ACTIVO" ? "Activo" : "Inactivo"}
                  </span>
                </td>
                <td>
                  {user.lastAccessAt
                    ? new Date(user.lastAccessAt).toLocaleDateString("es-CO")
                    : "—"}
                </td>
                {canManage && (
                  <td>
                    <button className="btn-link" onClick={() => toggleStatus(user)}>
                      {user.status === "ACTIVO" ? "Desactivar" : "Activar"}
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
