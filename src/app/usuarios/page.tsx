import { redirect } from "next/navigation";
import { getCurrentSession } from "@/lib/currentUser";
import { prisma } from "@/lib/prisma";
import { listUsers } from "@/lib/userService";
import { canManageUsers } from "@/lib/permissions";
import AppShell from "@/components/AppShell";
import UsersClient, { type UserRow } from "./UsersClient";
import type { EstadoUsuario, LineaNegocio, Rol } from "@/lib/domain";

export default async function UsuariosPage() {
  const session = await getCurrentSession();
  if (!session) {
    redirect("/login");
  }

  const users = await listUsers(prisma.user);
  const rows: UserRow[] = users.map((u) => ({
    id: u.id,
    name: u.name,
    email: u.email,
    role: u.role as Rol,
    lineaNegocio: u.lineaNegocio as LineaNegocio,
    status: u.status as EstadoUsuario,
    lastAccessAt: u.lastAccessAt ? u.lastAccessAt.toISOString() : null,
  }));

  return (
    <AppShell session={session}>
      <h1 className="page-title">Gestión de usuarios</h1>
      <p className="page-subtitle">
        {session.role} · Control de acceso por módulo y rol
      </p>
      <UsersClient initialUsers={rows} canManage={canManageUsers(session.role)} />
    </AppShell>
  );
}
