import { beforeEach, describe, expect, it, vi } from "vitest";
import { makeInMemoryUserRepo } from "./testUtils";

vi.mock("@/lib/mailer", () => ({
  sendActivationEmail: vi.fn(async () => {}),
  buildActivationLink: vi.fn((token: string) => `http://localhost:3000/activar-cuenta?token=${token}`),
}));

import {
  activateUser,
  createUser,
  deactivateUser,
  DuplicateEmailError,
  ForbiddenError,
  listUsers,
  UserNotFoundError,
} from "@/lib/userService";
import { sendActivationEmail } from "@/lib/mailer";

const GERENCIA = { role: "GERENCIA" as const };
const TECNICO = { role: "TECNICO" as const };

const validInput = {
  name: "Andrés Pérez",
  email: "andres@grupomactral.com",
  role: "TECNICO" as const,
  lineaNegocio: "INDUSTRY" as const,
};

describe("createUser", () => {
  let repo: ReturnType<typeof makeInMemoryUserRepo>;

  beforeEach(() => {
    repo = makeInMemoryUserRepo();
    vi.clearAllMocks();
  });

  // Escenario 1: Alta de usuario exitosa
  it("crea el usuario con estado Activo y envía el enlace de activación", async () => {
    const { user, activationLink } = await createUser(repo, GERENCIA, validInput);

    expect(user.status).toBe("ACTIVO");
    expect(user.email).toBe("andres@grupomactral.com");
    expect(activationLink).toContain("/activar-cuenta?token=");
    expect(sendActivationEmail).toHaveBeenCalledWith(user.email, activationLink);
  });

  it("expone el nuevo usuario en el listado con su rol y línea", async () => {
    await createUser(repo, GERENCIA, validInput);
    const users = await listUsers(repo);

    expect(users).toHaveLength(1);
    expect(users[0]).toMatchObject({ role: "TECNICO", lineaNegocio: "INDUSTRY" });
  });

  // Escenario 2: Correo duplicado
  it("rechaza un correo ya registrado sin crear un registro duplicado", async () => {
    await createUser(repo, GERENCIA, validInput);

    await expect(createUser(repo, GERENCIA, validInput)).rejects.toThrow(
      DuplicateEmailError
    );

    const users = await listUsers(repo);
    expect(users).toHaveLength(1);
  });

  it("solo permite crear usuarios al rol Gerencia/Administrador", async () => {
    await expect(createUser(repo, TECNICO, validInput)).rejects.toThrow(ForbiddenError);
    expect(await listUsers(repo)).toHaveLength(0);
  });

  it("rechaza datos inválidos antes de tocar el repositorio", async () => {
    await expect(
      createUser(repo, GERENCIA, { ...validInput, email: "no-valido" })
    ).rejects.toThrow();
    expect(repo.create).not.toHaveBeenCalled();
  });
});

describe("deactivateUser / activateUser", () => {
  let repo: ReturnType<typeof makeInMemoryUserRepo>;

  beforeEach(() => {
    repo = makeInMemoryUserRepo([
      { id: "u1", name: "Luis García", email: "luis@grupomactral.com", status: "ACTIVO" },
    ]);
  });

  // Escenario 3: Desactivación de usuario
  it("desactiva un usuario activo conservando sus datos", async () => {
    const updated = await deactivateUser(repo, GERENCIA, "u1");

    expect(updated.status).toBe("INACTIVO");
    expect(updated.name).toBe("Luis García");
    expect(updated.email).toBe("luis@grupomactral.com");
  });

  it("reactiva un usuario inactivo", async () => {
    await deactivateUser(repo, GERENCIA, "u1");
    const reactivated = await activateUser(repo, GERENCIA, "u1");

    expect(reactivated.status).toBe("ACTIVO");
  });

  it("solo permite desactivar/activar al rol Gerencia/Administrador", async () => {
    await expect(deactivateUser(repo, TECNICO, "u1")).rejects.toThrow(ForbiddenError);
  });

  it("lanza error si el usuario no existe", async () => {
    await expect(deactivateUser(repo, GERENCIA, "no-existe")).rejects.toThrow(
      UserNotFoundError
    );
  });
});
