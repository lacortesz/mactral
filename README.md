# Grupo Mactral — Plataforma de Gestión de Proyectos

Implementación de la historia **E1-H1 — Gestión de usuarios y roles** (Épica 1,
ver `HU_AC_Mockups_GrupoMactral_Epica_1.pdf`), con soporte mínimo de login
(E1-H2) para poder autenticar al rol Gerencia/Administrador.

Stack: Next.js 14 (App Router) + TypeScript + Prisma/SQLite + Vitest.

## Puesta en marcha

```bash
npm install
cp .env.example .env      # ajustar JWT_SECRET
npx prisma migrate dev --name init
npm run prisma:seed       # crea el usuario Gerencia/Admin inicial
npm run dev
```

Usuario inicial (definido en `.env` / `prisma/seed.ts`):
`SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` (por defecto
`maya@grupomactral.com` / `Mactral2026!`).

Abrir `http://localhost:3000`, iniciar sesión y entrar a **Gestión de
usuarios** (`/usuarios`).

## Pruebas

```bash
npm test              # vitest run
npm run test:coverage # cobertura (umbral 90% líneas/funciones en src/lib)
```

## Qué cubre esta implementación

- **Escenario 1 (alta exitosa)**: formulario nombre/correo/rol/línea de
  negocio, usuario creado en estado `ACTIVO`, enlace de activación generado
  (el envío de correo es un stub que registra el enlace en la consola del
  servidor — no hay proveedor SMTP configurado; ver `src/lib/mailer.ts`).
- **Escenario 2 (correo duplicado)**: `src/lib/userService.ts` valida
  unicidad antes de crear y lanza `DuplicateEmailError`.
- **Escenario 3 (desactivación)**: cambia `status` a `INACTIVO` sin borrar el
  registro; también se soporta reactivar.
- **Restricción de rol**: solo `GERENCIA` puede crear/activar/desactivar
  usuarios (`src/lib/permissions.ts`); el resto de roles ve la lista en modo
  lectura.

Fuera de alcance de E1-H1 (pertenecen a E1-H2, no implementadas a fondo):
bloqueo de cuenta tras 5 intentos fallidos, expiración de sesión por
inactividad más allá del `maxAge` del JWT, y el guard de "acceso a módulo no
autorizado" para módulos distintos a `/usuarios`.

## Limitación de este entorno

Esta máquina no tiene Node.js/npm instalados, así que no fue posible
ejecutar `npm install`, `npm test` ni levantar el servidor de desarrollo para
verificar visualmente la UI. El código no ha sido compilado ni probado en
este entorno — revísalo con `npm install && npm test` antes de darlo por
válido.
