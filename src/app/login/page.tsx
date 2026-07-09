import LoginForm from "./LoginForm";

export default function LoginPage() {
  return (
    <div className="login-wrap">
      <div className="login-card">
        <div className="login-header">
          <div
            className="sidebar-brand-badge"
            style={{ margin: "0 auto 12px" }}
          >
            GM
          </div>
          <h1 style={{ fontSize: 18, margin: 0 }}>Grupo Mactral</h1>
          <p style={{ fontSize: 13, color: "var(--mactral-text-muted)", margin: "4px 0 0" }}>
            Plataforma de Gestión de Proyectos
          </p>
        </div>
        <LoginForm />
      </div>
    </div>
  );
}
