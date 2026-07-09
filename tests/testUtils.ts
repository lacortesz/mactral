import type { User } from "@prisma/client";
import { vi } from "vitest";
import type { UserRepository } from "@/lib/userService";
import type { AuthUserRepository } from "@/lib/authService";

let idCounter = 0;

export function makeInMemoryUserRepo(seed: Partial<User>[] = []) {
  const users: User[] = seed.map((u) => toUser(u));

  function toUser(partial: Partial<User>): User {
    idCounter += 1;
    return {
      id: partial.id ?? `user-${idCounter}`,
      name: partial.name ?? "Sin nombre",
      email: partial.email ?? `user${idCounter}@grupomactral.com`,
      passwordHash: partial.passwordHash ?? null,
      role: partial.role ?? "COMERCIAL",
      lineaNegocio: partial.lineaNegocio ?? "MOBILITY",
      status: partial.status ?? "ACTIVO",
      activationToken: partial.activationToken ?? null,
      activationTokenExpiresAt: partial.activationTokenExpiresAt ?? null,
      lastAccessAt: partial.lastAccessAt ?? null,
      createdAt: partial.createdAt ?? new Date(),
      updatedAt: partial.updatedAt ?? new Date(),
    } as User;
  }

  const repo = {
    users,
    findUnique: vi.fn(async ({ where }: { where: Partial<User> }) => {
      const key = Object.keys(where)[0] as keyof User;
      const value = (where as any)[key];
      return users.find((u) => u[key] === value) ?? null;
    }),
    create: vi.fn(async ({ data }: { data: Partial<User> }) => {
      const user = toUser(data);
      users.push(user);
      return user;
    }),
    update: vi.fn(async ({ where, data }: { where: { id: string }; data: Partial<User> }) => {
      const index = users.findIndex((u) => u.id === where.id);
      if (index === -1) throw new Error("not found");
      users[index] = { ...users[index], ...data };
      return users[index];
    }),
    findMany: vi.fn(async () => [...users].sort(
      (a, b) => b.createdAt.getTime() - a.createdAt.getTime()
    )),
  };

  // El doble de prueba modela la forma real del repositorio en runtime, pero
  // no replica los tipos generados por Prisma (overloads de UserWhereUniqueInput,
  // etc.), así que se expone como UserRepository/AuthUserRepository vía cast.
  return repo as typeof repo & UserRepository & AuthUserRepository;
}
