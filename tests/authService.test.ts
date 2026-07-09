import { describe, expect, it } from "vitest";
import { makeInMemoryUserRepo } from "./testUtils";
import { hashPassword } from "@/lib/password";
import {
  InactiveAccountError,
  InvalidActivationTokenError,
  InvalidCredentialsError,
  loginUser,
  setPasswordWithToken,
} from "@/lib/authService";

describe("loginUser", () => {
  it("autentica con credenciales correctas y actualiza el último acceso", async () => {
    const passwordHash = await hashPassword("Mactral2026!");
    const repo = makeInMemoryUserRepo([
      { id: "u1", email: "maya@grupomactral.com", passwordHash, status: "ACTIVO" },
    ]);

    const user = await loginUser(repo, {
      email: "maya@grupomactral.com",
      password: "Mactral2026!",
    });

    expect(user.id).toBe("u1");
    expect(repo.update).toHaveBeenCalledWith(
      expect.objectContaining({ where: { id: "u1" } })
    );
  });

  it("rechaza contraseña incorrecta", async () => {
    const passwordHash = await hashPassword("Mactral2026!");
    const repo = makeInMemoryUserRepo([
      { id: "u1", email: "maya@grupomactral.com", passwordHash, status: "ACTIVO" },
    ]);

    await expect(
      loginUser(repo, { email: "maya@grupomactral.com", password: "incorrecta" })
    ).rejects.toThrow(InvalidCredentialsError);
  });

  it("rechaza un correo que no existe", async () => {
    const repo = makeInMemoryUserRepo();

    await expect(
      loginUser(repo, { email: "nadie@grupomactral.com", password: "x" })
    ).rejects.toThrow(InvalidCredentialsError);
  });

  it("rechaza el acceso de una cuenta inactiva", async () => {
    const passwordHash = await hashPassword("Mactral2026!");
    const repo = makeInMemoryUserRepo([
      { id: "u1", email: "luis@grupomactral.com", passwordHash, status: "INACTIVO" },
    ]);

    await expect(
      loginUser(repo, { email: "luis@grupomactral.com", password: "Mactral2026!" })
    ).rejects.toThrow(InactiveAccountError);
  });
});

describe("setPasswordWithToken", () => {
  it("establece la contraseña y consume el token de activación", async () => {
    const future = new Date(Date.now() + 60 * 60 * 1000);
    const repo = makeInMemoryUserRepo([
      {
        id: "u1",
        email: "andres@grupomactral.com",
        activationToken: "token-valido",
        activationTokenExpiresAt: future,
      },
    ]);

    const user = await setPasswordWithToken(repo, {
      token: "token-valido",
      password: "Mactral2026!",
    });

    expect(user.passwordHash).toBeTruthy();
    expect(user.activationToken).toBeNull();
  });

  it("rechaza un token expirado", async () => {
    const past = new Date(Date.now() - 60 * 60 * 1000);
    const repo = makeInMemoryUserRepo([
      {
        id: "u1",
        email: "andres@grupomactral.com",
        activationToken: "token-expirado",
        activationTokenExpiresAt: past,
      },
    ]);

    await expect(
      setPasswordWithToken(repo, { token: "token-expirado", password: "Mactral2026!" })
    ).rejects.toThrow(InvalidActivationTokenError);
  });

  it("rechaza un token inexistente", async () => {
    const repo = makeInMemoryUserRepo();

    await expect(
      setPasswordWithToken(repo, { token: "no-existe", password: "Mactral2026!" })
    ).rejects.toThrow(InvalidActivationTokenError);
  });
});
