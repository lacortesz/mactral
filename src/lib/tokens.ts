import { randomBytes } from "node:crypto";

export const ACTIVATION_TOKEN_TTL_HOURS = 48;

export function generateActivationToken(): string {
  return randomBytes(24).toString("hex");
}

export function activationTokenExpiry(from: Date = new Date()): Date {
  return new Date(from.getTime() + ACTIVATION_TOKEN_TTL_HOURS * 60 * 60 * 1000);
}
