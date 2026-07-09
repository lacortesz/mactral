import { beforeAll, describe, expect, it } from "vitest";
import { signSessionToken, verifySessionToken } from "@/lib/session";

beforeAll(() => {
  process.env.JWT_SECRET = "test-secret-para-pruebas";
});

describe("signSessionToken / verifySessionToken", () => {
  it("firma y verifica un token válido con los datos de sesión", async () => {
    const token = await signSessionToken({
      sub: "u1",
      name: "Maya Lozada",
      email: "maya@grupomactral.com",
      role: "GERENCIA",
    });

    const payload = await verifySessionToken(token);

    expect(payload).toMatchObject({
      sub: "u1",
      name: "Maya Lozada",
      email: "maya@grupomactral.com",
      role: "GERENCIA",
    });
  });

  it("devuelve null ante un token inválido o manipulado", async () => {
    const payload = await verifySessionToken("token-invalido");
    expect(payload).toBeNull();
  });

  it("devuelve null ante un token firmado con otro secreto", async () => {
    const token = await signSessionToken({
      sub: "u1",
      name: "Maya Lozada",
      email: "maya@grupomactral.com",
      role: "GERENCIA",
    });

    process.env.JWT_SECRET = "otro-secreto-distinto";
    const payload = await verifySessionToken(token);
    expect(payload).toBeNull();

    process.env.JWT_SECRET = "test-secret-para-pruebas";
  });
});
