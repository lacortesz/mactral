import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ApiError, retryAfterSeconds } from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (user) {
    const from = (location.state as { from?: string } | null)?.from ?? "/dashboard";
    navigate(from, { replace: true });
    return null;
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      const from = (location.state as { from?: string } | null)?.from ?? "/dashboard";
      navigate(from, { replace: true });
    } catch (err) {
      if (err instanceof ApiError && err.status === 423) {
        const seconds = retryAfterSeconds(err);
        const minutes = seconds ? Math.ceil(seconds / 60) : 15;
        setError(
          `Cuenta bloqueada temporalmente por demasiados intentos fallidos. Intenta de nuevo en ${minutes} minuto(s).`
        );
      } else if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("No se pudo iniciar sesión");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-wrap">
      <div className="login-card">
        <div className="login-header">
          <div className="sidebar-brand-badge" style={{ margin: "0 auto 12px" }}>
            GM
          </div>
          <h1 style={{ fontSize: 18, margin: 0 }}>Grupo Mactral</h1>
          <p style={{ fontSize: 13, color: "var(--mactral-text-muted)", margin: "4px 0 0" }}>
            Plataforma de Gestión de Proyectos
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          {error && <div className="alert alert-error">{error}</div>}

          <div className="form-field" style={{ marginBottom: 14 }}>
            <label htmlFor="email">Correo electrónico</label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="maya@grupomactral.com"
            />
          </div>

          <div className="form-field" style={{ marginBottom: 10 }}>
            <label htmlFor="password">Contraseña</label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          <div style={{ textAlign: "right", marginBottom: 18 }}>
            <Link to="/forgot-password" style={{ fontSize: 12 }}>
              ¿Olvidaste tu contraseña?
            </Link>
          </div>

          <button type="submit" className="btn-primary" style={{ width: "100%" }} disabled={loading}>
            {loading ? "Ingresando..." : "Ingresar"}
          </button>
        </form>
      </div>
    </div>
  );
}
