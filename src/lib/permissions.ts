import type { Rol } from "@/lib/domain";

/**
 * Restricción de negocio E1-H1: solo Gerencia (rol administrador de la
 * plataforma) puede crear o modificar usuarios. El resto de roles solo
 * puede consultar en modo lectura.
 */
export function canManageUsers(role: Rol): boolean {
  return role === "GERENCIA";
}
