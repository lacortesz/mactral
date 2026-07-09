import { z } from "zod";
import { LINEAS_NEGOCIO, ROLES } from "@/lib/domain";

export const rolEnum = z.enum(ROLES);

export const lineaNegocioEnum = z.enum(LINEAS_NEGOCIO);

export const createUserSchema = z.object({
  name: z.string().trim().min(1, "El nombre es obligatorio"),
  email: z.string().trim().toLowerCase().email("Correo electrónico inválido"),
  role: rolEnum,
  lineaNegocio: lineaNegocioEnum,
});

export type CreateUserInput = z.infer<typeof createUserSchema>;

export const loginSchema = z.object({
  email: z.string().trim().toLowerCase().email("Correo electrónico inválido"),
  password: z.string().min(1, "La contraseña es obligatoria"),
});

export type LoginInput = z.infer<typeof loginSchema>;

const PASSWORD_RULES =
  /^(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$/;

export const setPasswordSchema = z.object({
  token: z.string().min(1, "Token requerido"),
  password: z
    .string()
    .regex(
      PASSWORD_RULES,
      "La contraseña debe tener mínimo 8 caracteres, una mayúscula, un número y un carácter especial"
    ),
});

export type SetPasswordInput = z.infer<typeof setPasswordSchema>;
