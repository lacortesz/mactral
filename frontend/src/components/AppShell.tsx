import type { ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { MODULE_LABELS, type ModuleKey } from "../domain";

const NAV_ORDER: ModuleKey[] = [
  "comercial",
  "reg-maestro",
  "importaciones",
  "tecnico",
  "stock",
  "financiero",
  "administracion",
];

export default function AppShell({ children }: { children: ReactNode }) {
  const { user, accessibleModules, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span className="sidebar-brand-badge">GM</span>
          Grupo Mactral
        </div>
        <nav className="sidebar-nav">
          <NavLink to="/dashboard" className="sidebar-link" end>
            Dashboard
          </NavLink>
          {/* E1-H2 escenario 1: solo son visibles los módulos permitidos para el rol. */}
          {NAV_ORDER.filter((m) => accessibleModules.includes(m)).map((m) => (
            <NavLink
              key={m}
              to={m === "administracion" ? "/usuarios" : `/modulos/${m}`}
              className={({ isActive }) => `sidebar-link${isActive ? " active" : ""}`}
            >
              {MODULE_LABELS[m]}
            </NavLink>
          ))}
        </nav>
        {user && (
          <div className="sidebar-user">
            <div style={{ fontWeight: 700 }}>{user.name}</div>
            <div style={{ opacity: 0.7 }}>{user.role}</div>
          </div>
        )}
      </aside>
      <div className="main-content">
        <div className="topbar">
          <span style={{ color: "var(--mactral-text-muted)", fontSize: 13 }}>
            » Buscar por código CRP o cliente...
          </span>
          <button className="btn-link" onClick={handleLogout}>
            Cerrar sesión
          </button>
        </div>
        <div className="content">{children}</div>
      </div>
    </div>
  );
}
