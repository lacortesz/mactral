import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { apiFetch } from "../api/client";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    try {
      await apiFetch("/auth/forgot-password", { method: "POST", body: { email } });
      // Mensaje genérico siempre: no revela si el correo existe.
      setSent(true);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-wrap">
      <div className="login-card">
        <div className="login-header">
          <h1 style={{ fontSize: 18, margin: 0 }}>Recuperar contraseña</h1>
          <p style={{ fontSize: 13, color: "var(--mactral-text-muted)", margin: "4px 0 0" }}>
            Grupo Mactral
          </p>
        </div>

        {sent ? (
          <div className="alert alert-success">
            Si el correo existe, recibirás un enlace para restablecer tu contraseña.
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            <div className="form-field" style={{ marginBottom: 18 }}>
              <label htmlFor="email">Correo electrónico</label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <button type="submit" className="btn-primary" style={{ width: "100%" }} disabled={loading}>
              {loading ? "Enviando..." : "Enviar enlace"}
            </button>
          </form>
        )}

        <p style={{ textAlign: "center", marginTop: 16, fontSize: 13 }}>
          <Link to="/login">Volver al inicio de sesión</Link>
        </p>
      </div>
    </div>
  );
}
