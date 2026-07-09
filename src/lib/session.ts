import { SignJWT, jwtVerify } from "jose";
import type { Rol } from "@/lib/domain";

export const SESSION_COOKIE_NAME = "mactral_session";
const SESSION_DURATION_SECONDS = 8 * 60 * 60; // 8 horas de inactividad (E1-H2)

export type SessionPayload = {
  sub: string;
  name: string;
  email: string;
  role: Rol;
};

function getSecretKey() {
  const secret = process.env.JWT_SECRET;
  if (!secret) {
    throw new Error("JWT_SECRET no está configurado");
  }
  return new TextEncoder().encode(secret);
}

export async function signSessionToken(payload: SessionPayload): Promise<string> {
  return new SignJWT({ ...payload })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime(`${SESSION_DURATION_SECONDS}s`)
    .sign(getSecretKey());
}

export async function verifySessionToken(
  token: string
): Promise<SessionPayload | null> {
  try {
    const { payload } = await jwtVerify(token, getSecretKey());
    return payload as unknown as SessionPayload;
  } catch {
    return null;
  }
}

export const SESSION_MAX_AGE = SESSION_DURATION_SECONDS;
