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

const DEDICATED_MODULE_ROUTES: Partial<Record<ModuleKey, string>> = {
  administracion: "/usuarios",
  "reg-maestro": "/reg-maestro",
  comercial: "/comercial",
};

export function moduleRoute(m: ModuleKey): string {
  return DEDICATED_MODULE_ROUTES[m] ?? `/modulos/${m}`;
}

// E1-H3: catálogos de la ficha central del proyecto (CRP).
export type EstadoEtapa = "PENDIENTE" | "EN_CURSO" | "CERRADO" | "BLOQUEADO";

export const ESTADO_ETAPA_LABELS: Record<EstadoEtapa, string> = {
  PENDIENTE: "Pendiente",
  EN_CURSO: "En curso",
  CERRADO: "Cerrado",
  BLOQUEADO: "Bloqueado",
};

export type SemaforoColor = "VERDE" | "AMARILLO" | "ROJO";

// E2-H1: catálogos del módulo Comercial (leads).
export type EstadoLead = "COTIZAR" | "ENVIADA" | "VENDIDO";

export const ESTADO_LEAD_LABELS: Record<EstadoLead, string> = {
  COTIZAR: "Cotizar",
  ENVIADA: "Enviada",
  VENDIDO: "Vendido",
};

export const CANAL_ENTRADA_OPTIONS = [
  "Sitio web",
  "Referido",
  "Feria comercial",
  "Redes sociales",
  "Llamada entrante",
] as const;
