import type { SessionPayload } from "@/lib/session";
import LogoutButton from "@/components/LogoutButton";

const NAV_ITEMS = [
  { label: "Dashboard", href: "/usuarios" },
  { label: "Comercial", href: "#" },
  { label: "Reg. maestro", href: "#" },
  { label: "Importaciones", href: "#" },
  { label: "Técnico", href: "#" },
  { label: "Stock", href: "#" },
  { label: "Financiero", href: "#" },
];

export default function AppShell({
  session,
  children,
}: {
  session: SessionPayload;
  children: React.ReactNode;
}) {
  return (
    <div className="app-shell">
      <aside className="sidebar" style={{ display: "flex", flexDirection: "column" }}>
        <div className="sidebar-brand">
          <span className="sidebar-brand-badge">GM</span>
          Grupo Mactral
        </div>
        <nav className="sidebar-nav">
          {NAV_ITEMS.map((item) => (
            <a key={item.label} href={item.href} className="sidebar-link">
              {item.label}
            </a>
          ))}
          <a href="/usuarios" className="sidebar-link active">
            Administración
          </a>
        </nav>
        <div className="sidebar-user">
          <div style={{ fontWeight: 700 }}>{session.name}</div>
          <div style={{ opacity: 0.7 }}>{session.role}</div>
        </div>
      </aside>
      <div className="main-content">
        <div className="topbar">
          <span style={{ color: "var(--mactral-text-muted)", fontSize: 13 }}>
            » Buscar por código CRP o cliente...
          </span>
          <LogoutButton />
        </div>
        <div className="content">{children}</div>
      </div>
    </div>
  );
}
