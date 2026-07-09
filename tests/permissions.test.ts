import { describe, expect, it } from "vitest";
import { canManageUsers } from "@/lib/permissions";

describe("canManageUsers", () => {
  it("permite gestionar usuarios solo al rol GERENCIA", () => {
    expect(canManageUsers("GERENCIA")).toBe(true);
  });

  it.each([
    "COMERCIAL",
    "IMPORTACIONES",
    "TECNICO",
    "ADMINISTRATIVO",
  ] as const)("niega la gestión de usuarios al rol %s", (role) => {
    expect(canManageUsers(role)).toBe(false);
  });
});
