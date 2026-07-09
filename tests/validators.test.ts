import { describe, expect, it } from "vitest";
import {
  createUserSchema,
  loginSchema,
  setPasswordSchema,
} from "@/lib/validators";

describe("createUserSchema", () => {
  const valid = {
    name: "Andrés Pérez",
    email: "Andres@GrupoMactral.com",
    role: "TECNICO",
    lineaNegocio: "INDUSTRY",
  };

  it("acepta datos válidos y normaliza el correo a minúsculas", () => {
    const result = createUserSchema.parse(valid);
    expect(result.email).toBe("andres@grupomactral.com");
  });

  it("rechaza nombre vacío", () => {
    expect(() => createUserSchema.parse({ ...valid, name: "  " })).toThrow();
  });

  it("rechaza correo inválido", () => {
    expect(() => createUserSchema.parse({ ...valid, email: "no-es-correo" })).toThrow();
  });

  it("rechaza un rol fuera del catálogo permitido", () => {
    expect(() => createUserSchema.parse({ ...valid, role: "SUPERADMIN" })).toThrow();
  });

  it("rechaza una línea de negocio fuera del catálogo permitido", () => {
    expect(() =>
      createUserSchema.parse({ ...valid, lineaNegocio: "OTRA" })
    ).toThrow();
  });
});

describe("loginSchema", () => {
  it("acepta correo y contraseña", () => {
    expect(() =>
      loginSchema.parse({ email: "maya@grupomactral.com", password: "x" })
    ).not.toThrow();
  });

  it("rechaza contraseña vacía", () => {
    expect(() =>
      loginSchema.parse({ email: "maya@grupomactral.com", password: "" })
    ).toThrow();
  });
});

describe("setPasswordSchema", () => {
  it("acepta una contraseña que cumple la política de seguridad", () => {
    expect(() =>
      setPasswordSchema.parse({ token: "abc", password: "Mactral2026!" })
    ).not.toThrow();
  });

  it.each([
    "sinespeciales1A",
    "sinnumeromayus!",
    "corta1!",
    "todaminuscula1!",
  ])("rechaza contraseñas que no cumplen la política: %s", (password) => {
    expect(() => setPasswordSchema.parse({ token: "abc", password })).toThrow();
  });
});
