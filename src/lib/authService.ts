import type { PrismaClient, User } from "@prisma/client";
import { hashPassword, verifyPassword } from "@/lib/password";
import {
  loginSchema,
  setPasswordSchema,
  type LoginInput,
  type SetPasswordInput,
} from "@/lib/validators";

export class InvalidCredentialsError extends Error {}
export class InactiveAccountError extends Error {}
export class InvalidActivationTokenError extends Error {}

export type AuthUserRepository = Pick<
  PrismaClient["user"],
  "findUnique" | "update"
>;

/**
 * Login básico (soporte mínimo de E1-H2) usado para autenticar al
 * Administrador que ejecuta las acciones de E1-H1. No implementa el
 * bloqueo tras 5 intentos fallidos descrito en E1-H2; esa historia se
 * cubre por separado.
 */
export async function loginUser(
  db: AuthUserRepository,
  input: LoginInput
): Promise<User> {
  const { email, password } = loginSchema.parse(input);

  const user = await db.findUnique({ where: { email } });
  if (!user || !user.passwordHash) {
    throw new InvalidCredentialsError("Correo o contraseña incorrectos");
  }

  const isValid = await verifyPassword(password, user.passwordHash);
  if (!isValid) {
    throw new InvalidCredentialsError("Correo o contraseña incorrectos");
  }

  if (user.status !== "ACTIVO") {
    throw new InactiveAccountError("La cuenta está inactiva");
  }

  await db.update({ where: { id: user.id }, data: { lastAccessAt: new Date() } });

  return user;
}

/**
 * Completa el alta de usuario (E1-H1, escenario 1): el enlace enviado por
 * correo permite establecer la contraseña inicial usando el token de
 * activación generado al crear el usuario.
 */
export async function setPasswordWithToken(
  db: AuthUserRepository,
  input: SetPasswordInput
): Promise<User> {
  const { token, password } = setPasswordSchema.parse(input);

  const user = await db.findUnique({ where: { activationToken: token } });
  if (!user || !user.activationTokenExpiresAt || user.activationTokenExpiresAt < new Date()) {
    throw new InvalidActivationTokenError("El enlace de activación no es válido o expiró");
  }

  const passwordHash = await hashPassword(password);

  return db.update({
    where: { id: user.id },
    data: {
      passwordHash,
      activationToken: null,
      activationTokenExpiresAt: null,
    },
  });
}
