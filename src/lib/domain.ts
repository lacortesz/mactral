// SQLite (usado en desarrollo) no soporta enums nativos de Prisma, así que
// los catálogos de rol/línea/estado se definen aquí como fuente única de
// verdad y se almacenan como String en el esquema (`prisma/schema.prisma`).

export const ROLES = [
  "COMERCIAL",
  "IMPORTACIONES",
  "TECNICO",
  "ADMINISTRATIVO",
  "GERENCIA",
] as const;
export type Rol = (typeof ROLES)[number];

export const LINEAS_NEGOCIO = ["MOBILITY", "INDUSTRY", "AMBAS"] as const;
export type LineaNegocio = (typeof LINEAS_NEGOCIO)[number];

export const ESTADOS_USUARIO = ["ACTIVO", "INACTIVO"] as const;
export type EstadoUsuario = (typeof ESTADOS_USUARIO)[number];
