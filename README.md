# Grupo Mactral — Plataforma de Gestión de Proyectos

Arquitectura de microservicios: **React** (frontend, Vite) + **Python/FastAPI**
(backend, `services/auth`) + **PostgreSQL**, con Docker para desplegar todo.

Implementa:

- **E1-H1 — Gestión de usuarios y roles**: alta/desactivación de usuarios,
  asignación de rol y línea de negocio, restringida a Gerencia/Administrador.
- **E1-H2 — Inicio de sesión seguro**: login con JWT, bloqueo tras 5 intentos
  fallidos (15 min), expiración de sesión por inactividad, recuperación de
  contraseña por correo, y control de acceso por módulo según rol.
- **E1-H3 — Ficha central del proyecto (CRP)**: búsqueda de un proyecto por
  código CRP o cliente, ficha de solo lectura con datos base, estado por
  módulo (con candado en las etapas cerradas) y línea de tiempo.

Ver `HU_AC_Mockups_GrupoMactral_Epica_1.pdf` para las historias de usuario
originales.

## Estructura

```
services/auth/       FastAPI + SQLAlchemy + Alembic (usuarios, roles, sesión)
services/projects/   FastAPI + SQLAlchemy + Alembic (ficha CRP, E1-H3)
frontend/            React + Vite + TypeScript (SPA)
docker-compose.yml
```

`auth` y `projects` comparten la misma instancia de Postgres (bases lógicas
separadas por prefijo de tabla, cada una con su propia tabla de versiones de
Alembic) y el mismo `JWT_SECRET`: `projects` no emite sesiones, solo verifica
el JWT que emitió `auth`.

## Puesta en marcha (Docker, recomendado)

```bash
docker compose up -d --build postgres auth projects frontend
docker compose run --rm seed             # usuario Gerencia/Admin inicial
docker compose run --rm seed-projects    # proyectos de ejemplo (GM26-03, GM26-04)
```

- Frontend: http://localhost:8080
- API auth: http://localhost:8000 (docs interactivas en `/docs`)
- API projects: http://localhost:8100 (docs interactivas en `/docs`)
- Usuario inicial: `maya@grupomactral.com` / `Mactral2026!` (configurable via
  `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD`)

## Puesta en marcha (desarrollo local, sin Docker)

Backend (repetir para `services/auth` y `services/projects`; ambos siguen el
mismo patrón):
```bash
cd services/auth   # o services/projects
python -m venv .venv && source .venv/Scripts/activate  # o .venv/bin/activate en Linux/Mac
pip install -r requirements-dev.txt
cp .env.example .env   # ajustar DATABASE_URL a un Postgres local; JWT_SECRET debe
                        # ser igual en ambos servicios
alembic upgrade head
python seed.py
uvicorn app.main:app --reload   # auth en :8000, projects usar --port 8100
```

Frontend:
```bash
cd frontend
npm install
cp .env.example .env
npm run dev   # http://localhost:5173
```

## Despliegue en producción (Railway)

**URLs actuales:**
- Frontend: https://frontend-production-1622.up.railway.app
- API auth: https://auth-production-b32d.up.railway.app (docs en `/docs`)
- Usuario inicial: `maya@grupomactral.com` / `Mactral2026!`

> `services/projects` (E1-H3) todavía no está desplegado en Railway — solo
> corre localmente / vía Docker por ahora. Desplegarlo sigue el mismo patrón
> que `auth` (ver comandos abajo, servicio nuevo + su propio dominio +
> `VITE_PROJECTS_API_BASE_URL` en el frontend).

Se desplegó con el [Railway CLI](https://docs.railway.com/guides/cli) (no vía
`docker-compose.yml` directamente — Railway despliega cada servicio por
separado a partir de su Dockerfile). Proyecto: `mactral`, 3 servicios:
`Postgres` (plugin gestionado), `auth` y `frontend`.

### Reproducir el despliegue desde cero

```bash
npm install -g @railway/cli
railway login                       # abre el navegador para autenticar

cd /ruta/al/repo
railway init --name mactral

# 1. Base de datos gestionada
railway add --database postgres

# 2. Backend (services/auth)
railway add --service auth
railway variable set "DATABASE_URL=postgresql+psycopg://\${{Postgres.PGUSER}}:\${{Postgres.PGPASSWORD}}@\${{Postgres.PGHOST}}:\${{Postgres.PGPORT}}/\${{Postgres.PGDATABASE}}" --service auth --skip-deploys
railway variable set "JWT_SECRET=$(openssl rand -hex 32)" --service auth --skip-deploys
railway variable set "SEED_ADMIN_EMAIL=maya@grupomactral.com" --service auth --skip-deploys
railway variable set "SEED_ADMIN_PASSWORD=Mactral2026!" --service auth --skip-deploys
railway up services/auth --path-as-root --service auth --detach --ci
railway domain --service auth                # genera <auth-domain>.up.railway.app
railway domain update <auth-domain> --port 8000 --service auth   # ver nota de puertos abajo

# 3. Frontend
railway add --service frontend
railway variable set "VITE_API_BASE_URL=https://<auth-domain>" --service frontend --skip-deploys
railway up frontend --path-as-root --service frontend --detach --ci
railway domain --service frontend            # genera <frontend-domain>.up.railway.app
railway domain update <frontend-domain> --port 80 --service frontend

# 4. Cerrar el círculo: el backend necesita saber el dominio del frontend
railway variable set "APP_BASE_URL=https://<frontend-domain>" --service auth --skip-deploys
railway variable set 'CORS_ORIGINS=["https://<frontend-domain>"]' --service auth   # dispara redeploy

# 5. Crear el usuario administrador inicial
railway variable list --service Postgres --json   # copiar DATABASE_PUBLIC_URL
cd services/auth && source .venv/Scripts/activate
DATABASE_URL="postgresql+psycopg://...<DATABASE_PUBLIC_URL con el driver +psycopg>..." \
SEED_ADMIN_EMAIL=maya@grupomactral.com SEED_ADMIN_PASSWORD='Mactral2026!' \
python seed.py
```

### Gotchas encontrados

- **502 "Application failed to respond"** en ambos servicios justo después del
  primer deploy: Railway no sabía a qué puerto interno enrutar el tráfico
  público. Se resolvió con `railway domain update <dominio> --port <puerto>`
  (8000 para `auth`, 80 para `frontend`/nginx). Si vuelve a pasar, revisar el
  puerto configurado en el dominio del servicio.
- **`railway ssh --service auth python seed.py` se queda colgado** — no se
  investigó a fondo por qué; como alternativa, se corrió `seed.py`
  *localmente* apuntando a `DATABASE_PUBLIC_URL` del plugin de Postgres (la
  URL con el proxy TCP público de Railway, reemplazando el esquema por
  `postgresql+psycopg://` para que SQLAlchemy la acepte). Esa URL es
  alcanzable desde cualquier máquina, no solo desde dentro de Railway.
- El correo de recuperación de contraseña sigue siendo un stub (ver sección
  E1-H2 más abajo): revisar `railway logs --service auth` para ver el enlace
  generado en vez de esperar un correo real.

### Costos

Plan Hobby de Railway: $5/mes de crédito incluido, luego pago por uso
(CPU/RAM/red). La carga de este proyecto es mínima, así que debería caber
holgadamente en el crédito gratuito, pero conviene revisar el consumo en el
dashboard de vez en cuando.

## Pruebas

Repetir en cada servicio (`services/auth`, `services/projects`):
```bash
cd services/auth   # o services/projects
source .venv/Scripts/activate
pytest --cov --cov-report=term-missing   # umbral 90%; auth 96%, projects 100%
```

## Qué cubre cada historia

### E1-H1
- Alta exitosa → estado `ACTIVO` + enlace de activación (mailer stub, logs).
- Correo duplicado → 409, sin crear registro.
- Desactivar/activar → cambia `status`, conserva historial.
- Solo `GERENCIA` puede gestionar usuarios (`app/domain.py: can_manage_users`).

### E1-H2
- Login exitoso → JWT, redirige a dashboard, solo se listan los módulos
  permitidos para el rol (`ROLE_MODULE_ACCESS` en `app/domain.py`).
- Credenciales incorrectas → mensaje genérico; **5 intentos fallidos bloquean
  la cuenta 15 minutos** (`app/services/auth_service.py`).
- Acceso a módulo no autorizado (p. ej. Técnico → Financiero) → 403 en la API
  y redirección a `/dashboard?denied=1` con el mensaje exacto de la historia,
  tanto si se navega por la UI como por URL directa o llamada a la API.
- Recuperación de contraseña por correo (`/forgot-password` → token →
  `/activar-cuenta?token=...`), sin revelar si el correo existe.
- Política de contraseña: mínimo 8 caracteres, mayúscula, número y carácter
  especial.
- Expiración por inactividad: JWT de 8h que el frontend renueva mientras la
  pestaña está activa (`AuthContext`); si el usuario deja de interactuar, la
  sesión expira naturalmente 8h después de la última renovación.

Los módulos Comercial/Importaciones/Técnico/Stock/Financiero/Reg. maestro son
endpoints *stub* (`app/routers/modules.py`): existen solo para poder ejercer
el control de acceso de E1-H2; su contenido real pertenece a otras épicas.

### E1-H3
- Búsqueda por código CRP o nombre de cliente (`/projects/search?q=...`,
  `services/projects/app/services/project_service.py`); sin coincidencias
  se muestra "No se encontraron proyectos con ese criterio".
- Ficha completa (código CRP, tipo, cliente, ciudad, producto, marca, etapa
  actual y semáforo) igual para todos los roles — accesible desde el módulo
  "Reg. maestro" (`frontend/src/pages/RegMaestroPage.tsx`), que todos los
  roles tienen habilitado.
- Estado por módulo (Comercial/Reg. maestro/Importaciones/Técnico) con ícono
  de candado 🔒 cuando la etapa está `CERRADO`; línea de tiempo con los
  eventos del proyecto ordenados por fecha.
- `editable_por_mi_rol` por módulo ya viene calculado en la respuesta de la
  API (según qué módulos puede editar cada rol), como base para las historias
  futuras que agreguen los formularios de edición por módulo — E1-H3 en sí es
  de solo lectura.

**Nota técnica:** el enum `Modulo` tiene nombres en mayúsculas
(`COMERCIAL`) pero valores en minúscula-con-guion (`"comercial"`, para que
coincidan con las claves de módulo del frontend). Por defecto SQLAlchemy
manda el *nombre* del enum de Python a Postgres, no el valor — hay que pasar
`values_callable` explícitamente en la columna (`app/models.py`) o falla con
`invalid input value for enum` en Postgres (no se detecta en SQLite porque
ahí no hay una restricción real, así que los tests unitarios no lo atrapan).

## Notas de la migración de stack

Este proyecto empezó como un monolito Next.js/Prisma/SQLite (historia E1-H1).
Se migró completamente a React + Python + Postgres a partir de E1-H2 por
decisión explícita del proyecto (ver `CLAUDE.md`, sección Arquitectura).
