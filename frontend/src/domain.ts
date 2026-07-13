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
  | "logistica"
  | "administracion";

export const MODULE_LABELS: Record<ModuleKey, string> = {
  comercial: "Comercial",
  "reg-maestro": "Reg. maestro",
  importaciones: "Importaciones",
  tecnico: "Técnico",
  stock: "Stock",
  financiero: "Financiero",
  logistica: "Logística",
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
  importaciones: "/importaciones",
  tecnico: "/tecnico",
  stock: "/stock",
  financiero: "/financiero",
  logistica: "/logistica",
};

export function moduleRoute(m: ModuleKey): string {
  return DEDICATED_MODULE_ROUTES[m] ?? `/modulos/${m}`;
}

// E1-H3: catálogos de la ficha central del proyecto (CRP).
// E5-H2: ENTREGADO es el estado final del proyecto (solo etapa_actual, no
// el estado por módulo).
export type EstadoEtapa = "PENDIENTE" | "EN_CURSO" | "CERRADO" | "BLOQUEADO" | "ENTREGADO";

export const ESTADO_ETAPA_LABELS: Record<EstadoEtapa, string> = {
  PENDIENTE: "Pendiente",
  EN_CURSO: "En curso",
  CERRADO: "Cerrado",
  BLOQUEADO: "Bloqueado",
  ENTREGADO: "Entregado",
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

// E2-H2: catálogo de la calculadora oficial de cotizaciones.
export type TipoPago = "CONTADO" | "CREDITO";

export const TIPO_PAGO_LABELS: Record<TipoPago, string> = {
  CONTADO: "Contado",
  CREDITO: "Crédito",
};

// E2-H4: clasificación que se pide al marcar el lead como Vendido (E2-H3).
export type TipoClasificacion = "GM" | "STOCK_MOBILITY" | "STOCK_INDUSTRY";

export const TIPO_CLASIFICACION_LABELS: Record<TipoClasificacion, string> = {
  GM: "GM (Registro Maestro)",
  STOCK_MOBILITY: "Stock — Mobility",
  STOCK_INDUSTRY: "Stock — Industry",
};

// E4-H1: catálogo del checklist documental de importación.
export type TipoItemChecklist = "REQUERIDO" | "OPCIONAL";
export type EstadoItemChecklist = "PENDIENTE" | "ARCHIVADO" | "NO_APLICA";

// E5-H1/E5-H2: catálogo de la instalación (módulo Técnico).
export type EstadoInstalacion = "PROGRAMADO" | "COMPLETADO";

export const ESTADO_INSTALACION_LABELS: Record<EstadoInstalacion, string> = {
  PROGRAMADO: "Programado",
  COMPLETADO: "Completado",
};

export const ESTADO_ITEM_CHECKLIST_LABELS: Record<EstadoItemChecklist, string> = {
  PENDIENTE: "Pendiente",
  ARCHIVADO: "Archivado",
  NO_APLICA: "No aplica",
};
