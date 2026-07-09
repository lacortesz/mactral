// Copia mínima del mapa de roles/módulos de app/domain.py (services/auth).
// La autorización real se aplica en el backend; esta copia solo controla
// qué se muestra en la navegación (E1-H2 escenario 1: "solo son visibles
// los módulos permitidos para ese rol").

export type Rol = "COMERCIAL" | "IMPORTACIONES" | "TECNICO" | "ADMINISTRATIVO" | "GERENCIA";

export type LineaNegocio = "MOBILITY" | "INDUSTRY" | "AMBAS";

export type EstadoUsuario = "ACTIVO" | "INACTIVO";

export type ModuleKey =
  | "comercial"
  | "reg-maestro"
  | "importaciones"
  | "tecnico"
  | "stock"
  | "financiero"
  | "administracion";

export const MODULE_LABELS: Record<ModuleKey, string> = {
  comercial: "Comercial",
  "reg-maestro": "Reg. maestro",
  importaciones: "Importaciones",
  tecnico: "Técnico",
  stock: "Stock",
  financiero: "Financiero",
  administracion: "Administración",
};

export const ROLE_LABELS: Record<Rol, string> = {
  COMERCIAL: "Comercial",
  IMPORTACIONES: "Importaciones",
  TECNICO: "Técnico",
  ADMINISTRATIVO: "Administrativo",
  GERENCIA: "Gerencia",
};

export const LINE_LABELS: Record<LineaNegocio, string> = {
  MOBILITY: "Mobility",
  INDUSTRY: "Industry",
  AMBAS: "Ambas",
};
