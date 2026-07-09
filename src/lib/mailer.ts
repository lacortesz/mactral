/**
 * Stub de envío de correo. En este entorno de desarrollo no hay proveedor
 * SMTP configurado, así que el enlace de activación se registra en consola.
 * Sustituir por una integración real (Resend, SES, etc.) en producción.
 */
export async function sendActivationEmail(
  email: string,
  activationLink: string
): Promise<void> {
  console.log(
    `[mailer] Enlace para establecer contraseña enviado a ${email}: ${activationLink}`
  );
}

export function buildActivationLink(token: string): string {
  const baseUrl = process.env.APP_BASE_URL ?? "http://localhost:3000";
  return `${baseUrl}/activar-cuenta?token=${token}`;
}
