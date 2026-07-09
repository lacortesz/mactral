import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { buildActivationLink, sendActivationEmail } from "@/lib/mailer";

describe("buildActivationLink", () => {
  const originalBaseUrl = process.env.APP_BASE_URL;

  afterEach(() => {
    process.env.APP_BASE_URL = originalBaseUrl;
  });

  it("usa el valor por defecto cuando no hay APP_BASE_URL configurado", () => {
    delete process.env.APP_BASE_URL;
    expect(buildActivationLink("abc123")).toBe(
      "http://localhost:3000/activar-cuenta?token=abc123"
    );
  });

  it("respeta APP_BASE_URL cuando está configurado", () => {
    process.env.APP_BASE_URL = "https://mactral.example.com";
    expect(buildActivationLink("abc123")).toBe(
      "https://mactral.example.com/activar-cuenta?token=abc123"
    );
  });
});

describe("sendActivationEmail", () => {
  beforeEach(() => {
    vi.spyOn(console, "log").mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("registra en consola el enlace de activación enviado", async () => {
    await sendActivationEmail("andres@grupomactral.com", "http://localhost:3000/x");

    expect(console.log).toHaveBeenCalledWith(
      expect.stringContaining("andres@grupomactral.com")
    );
  });
});
