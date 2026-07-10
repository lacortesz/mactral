import { Link, useSearchParams } from "react-router-dom";
import AppShell from "../components/AppShell";
import { useAuth } from "../context/AuthContext";
import { MODULE_LABELS, ROLE_LABELS, moduleRoute } from "../domain";

export default function DashboardPage() {
  const { user, accessibleModules } = useAuth();
  const [searchParams] = useSearchParams();
  const denied = searchParams.get("denied") === "1";

  return (
    <AppShell>
      <h1 className="page-title">Dashboard</h1>
      <p className="page-subtitle">
        {user && `${ROLE_LABELS[user.role]} · Módulos disponibles para tu rol`}
      </p>

      {denied && (
        // Escenario 3 (E1-H2): acceso a módulo no autorizado.
        <div className="alert alert-error">No tiene permisos para acceder a este módulo.</div>
      )}

      <div className="card">
        <h2 className="card-title">Módulos</h2>
        <div className="module-grid">
          {accessibleModules.map((m) => (
            <Link key={m} className="module-card" to={moduleRoute(m)}>
              {MODULE_LABELS[m]}
            </Link>
          ))}
        </div>
      </div>
    </AppShell>
  );
}
