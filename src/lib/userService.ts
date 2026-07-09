import type { PrismaClient, User } from "@prisma/client";
import type { Rol } from "@/lib/domain";
import { canManageUsers } from "@/lib/permissions";
import { createUserSchema, type CreateUserInput } from "@/lib/validators";
import { generateActivationToken, activationTokenExpiry } from "@/lib/tokens";
import { buildActivationLink, sendActivationEmail } from "@/lib/mailer";

export class ForbiddenError extends Error {}
export class DuplicateEmailError extends Error {}
export class UserNotFoundError extends Error {}

type Actor = { role: Rol };

/**
 * Subconjunto de PrismaClient que necesita este servicio, para poder
 * inyectar un doble de prueba en los tests unitarios sin levantar SQLite.
 */
export type UserRepository = Pick<PrismaClient["user"], "findUnique" | "create" | "update" | "findMany">;

export async function listUsers(db: UserRepository): Promise<User[]> {
  return db.findMany({ orderBy: { createdAt: "desc" } });
}

// Escenario 1 (E1-H1): alta de usuario exitosa.
// Escenario 2 (E1-H1): correo duplicado.
export async function createUser(
  db: UserRepository,
  actor: Actor,
  input: CreateUserInput
): Promise<{ user: User; activationLink: string }> {
  if (!canManageUsers(actor.role)) {
    throw new ForbiddenError(
      "Solo el rol Gerencia/Administrador puede crear o modificar usuarios."
    );
  }

  const data = createUserSchema.parse(input);

  const existing = await db.findUnique({ where: { email: data.email } });
  if (existing) {
    throw new DuplicateEmailError("Ya existe un usuario con ese correo");
  }

  const activationToken = generateActivationToken();

  const user = await db.create({
    data: {
      name: data.name,
      email: data.email,
      role: data.role,
      lineaNegocio: data.lineaNegocio,
      status: "ACTIVO",
      activationToken,
      activationTokenExpiresAt: activationTokenExpiry(),
    },
  });

  const activationLink = buildActivationLink(activationToken);
  await sendActivationEmail(user.email, activationLink);

  return { user, activationLink };
}

async function setUserStatus(
  db: UserRepository,
  actor: Actor,
  userId: string,
  status: "ACTIVO" | "INACTIVO"
): Promise<User> {
  if (!canManageUsers(actor.role)) {
    throw new ForbiddenError(
      "Solo el rol Gerencia/Administrador puede crear o modificar usuarios."
    );
  }

  const existing = await db.findUnique({ where: { id: userId } });
  if (!existing) {
    throw new UserNotFoundError("Usuario no encontrado");
  }

  return db.update({ where: { id: userId }, data: { status } });
}

// Escenario 3 (E1-H1): desactivación de usuario. Los datos e historial
// permanecen intactos: solo cambia el campo `status`, nunca se borra el registro.
export function deactivateUser(db: UserRepository, actor: Actor, userId: string) {
  return setUserStatus(db, actor, userId, "INACTIVO");
}

export function activateUser(db: UserRepository, actor: Actor, userId: string) {
  return setUserStatus(db, actor, userId, "ACTIVO");
}
