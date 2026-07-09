import { useState, type FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { ApiError, apiFetch } from "../api/client";

export default function SetPasswordPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await apiFetch("/auth/set-password", { method: "POST", body: { token, password } });
      setSuccess(true);
      setTimeout(() => navigate("/login"), 1500);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo establecer la contraseña");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-wrap">
      <div className="login-card">
        <div className="login-header">
          <h1 style={{ fontSize: 18, margin: 0 }}>Establecer contraseña</h1>
          <p style={{ fontSize: 13, color: "var(--mactral-text-muted)", margin: "4px 0 0" }}>
            Grupo Mactral — activación / recuperación de cuenta
          </p>
        </div>

        {success ? (
          <div className="alert alert-success">
            Contraseña establecida correctamente. Redirigiendo al inicio de sesión...
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            {error && <div className="alert alert-error">{error}</div>}
            <div className="form-field" style={{ marginBottom: 18 }}>
              <label htmlFor="password">Nueva contraseña</label>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <span style={{ fontSize: 12, color: "var(--mactral-text-muted)" }}>
                Mínimo 8 caracteres, una mayúscula, un número y un carácter especial.
              </span>
            </div>
            <button
              type="submit"
              className="btn-primary"
              style={{ width: "100%" }}
              disabled={loading || !token}
            >
              {loading ? "Guardando..." : "Guardar contraseña"}
            </button>
            {!token && (
              <p style={{ fontSize: 12, color: "var(--mactral-red)", marginTop: 10 }}>
                Enlace inválido: falta el token de activación.
              </p>
            )}
          </form>
        )}
      </div>
    </div>
  );
}
