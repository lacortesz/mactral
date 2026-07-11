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
- **E2-H1 — Registro de lead**: alta de leads con datos de contacto y equipo
  solicitado, consecutivo automático por línea de negocio (MOB/IND), y
  registro de interacciones posteriores.
- **E2-H2 — Cotización en PDF con calculadora oficial**: generación de una
  cotización en PDF (valor del equipo, tipo de pago, % de anticipos, fecha
  estimada de entrega) adjunta al lead con numeración basada en su
  consecutivo; el estado cambia automáticamente a Enviada la primera vez, y
  cada regeneración crea una nueva versión conservando el historial completo.

Ver `HU_AC_Mockups_GrupoMactral_v1_optimizado.pdf` (32 historias, 11 épicas)
para las historias de usuario originales.

## Estructura

```
services/auth/        FastAPI + SQLAlchemy + Alembic (usuarios, roles, sesión)
services/projects/    FastAPI + SQLAlchemy + Alembic (ficha CRP, E1-H3)
services/comercial/   FastAPI + SQLAlchemy + Alembic (leads, E2-H1/E2-H2)
frontend/             React + Vite + TypeScript (SPA)
docker-compose.yml
```

`auth`, `projects` y `comercial` comparten la misma instancia de Postgres
(bases lógicas separadas por prefijo de tabla, cada una con su propia tabla
de versiones de Alembic) y el mismo `JWT_SECRET`: `projects` y `comercial`
no emiten sesiones, solo verifican el JWT que emitió `auth`.

## Puesta en marcha (Docker, recomendado)

```bash
docker compose up -d --build postgres auth projects comercial frontend
docker compose run --rm seed              # usuario Gerencia/Admin inicial
docker compose run --rm seed-projects     # proyectos de ejemplo (GM26-03, GM26-04)
docker compose run --rm seed-comercial    # leads de ejemplo (MOB26-01x, IND26-00x)
```

- Frontend: http://localhost:8080
- API auth: http://localhost:8000 (docs interactivas en `/docs`)
- API projects: http://localhost:8100 (docs interactivas en `/docs`)
- API comercial: http://localhost:8200 (docs interactivas en `/docs`)
- Usuario inicial: `maya@grupomactral.com` / `Mactral2026!` (configurable via
  `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD`)

## Puesta en marcha (desarrollo local, sin Docker)

Backend (repetir para `services/auth`, `services/projects` y
`services/comercial`; los tres siguen el mismo patrón):
```bash
cd services/auth   # o services/projects, o services/comercial
python -m venv .venv && source .venv/Scripts/activate  # o .venv/bin/activate en Linux/Mac
pip install -r requirements-dev.txt
cp .env.example .env   # ajustar DATABASE_URL a un Postgres local; JWT_SECRET debe
                        # ser igual en los tres servicios
alembic upgrade head
python seed.py
uvicorn app.main:app --reload   # auth :8000, projects :8100, comercial :8200
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
- API projects: https://projects-production-826d.up.railway.app (docs en `/docs`)
- API comercial: https://comercial-production-7e35.up.railway.app (docs en `/docs`)
- Usuario inicial: `maya@grupomactral.com` / `Mactral2026!`

Se desplegó con el [Railway CLI](https://docs.railway.com/guides/cli) (no vía
`docker-compose.yml` directamente — Railway despliega cada servicio por
separado a partir de su Dockerfile). Proyecto: `mactral`, 5 servicios:
`Postgres` (plugin gestionado), `auth`, `projects`, `comercial` y `frontend`.

> El plan gratuito de Railway tiene un límite de recursos (falló al crear el
> 5to servicio con "Free plan resource provision limit exceeded"); se
> resolvió reintentando tras que el plan quedara disponible. Si vuelve a
> pasar al agregar un servicio nuevo, revisar el plan/límites en el
> dashboard antes de asumir que es un problema del CLI.

### Auto-deploy desde GitHub (pendiente de un paso manual)

Los 3 servicios de código están conectados al repo `lacortesz/mactral`, rama
`dev` (`railway service source connect --repo ... --branch dev --service ...`),
pero el build automático **todavía falla** porque el CLI de Railway no
expone la opción "Root Directory", necesaria en un monorepo (cada Dockerfile
vive en una subcarpeta, no en la raíz del repo — Railway intenta compilar
desde la raíz y no encuentra nada: `Railpack could not determine how to
build the app`). Sin este ajuste, cada `git push` a `dev` deja un deployment
en `FAILED` (Railway sigue sirviendo la última versión buena, así que no hay
caída de servicio, pero tampoco se actualiza solo).

Pendiente, una sola vez por servicio, desde el dashboard de Railway
(Settings → Source → Root Directory):
- `auth` → `services/auth`
- `projects` → `services/projects`
- `comercial` → `services/comercial`
- `frontend` → `frontend`

`projects` y `comercial` ni siquiera están conectados todavía a GitHub (solo
`auth` y `frontend` lo están); se agregaron directo con `railway up` sin
`service source connect`. Conectarlos es un paso aparte y de todos modos no
sirve de nada mientras el Root Directory no esté fijado.

Hasta que se haga eso, los despliegues se siguen haciendo a mano con
`railway up <carpeta> --path-as-root --service <nombre> --detach --ci` (ver
comandos abajo) cada vez que haya cambios que llevar a producción.

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

# 3. Servicio de proyectos (services/projects, E1-H3) — mismo JWT_SECRET que auth
railway add --service projects
railway variable set "DATABASE_URL=postgresql+psycopg://\${{Postgres.PGUSER}}:\${{Postgres.PGPASSWORD}}@\${{Postgres.PGHOST}}:\${{Postgres.PGPORT}}/\${{Postgres.PGDATABASE}}" --service projects --skip-deploys
railway variable set "JWT_SECRET=<el mismo valor usado en auth>" --service projects --skip-deploys
railway up services/projects --path-as-root --service projects --detach --ci
railway domain --service projects            # genera <projects-domain>.up.railway.app
# El puerto real lo decide el $PORT que Railway inyecta en el contenedor (ver
# gotcha de puertos abajo); revisar con `railway logs --service projects` qué
# puerto imprime uvicorn y usar ese valor, no asumir uno fijo.
railway domain update <projects-domain> --port <puerto-real> --service projects

# 4. Servicio comercial (services/comercial, E2-H1) — mismo JWT_SECRET que auth
railway add --service comercial
railway variable set "DATABASE_URL=postgresql+psycopg://\${{Postgres.PGUSER}}:\${{Postgres.PGPASSWORD}}@\${{Postgres.PGHOST}}:\${{Postgres.PGPORT}}/\${{Postgres.PGDATABASE}}" --service comercial --skip-deploys
railway variable set "JWT_SECRET=<el mismo valor usado en auth>" --service comercial --skip-deploys
railway up services/comercial --path-as-root --service comercial --detach --ci
railway domain --service comercial           # genera <comercial-domain>.up.railway.app
railway domain update <comercial-domain> --port <puerto-real> --service comercial

# 5. Frontend
railway add --service frontend
railway variable set "VITE_API_BASE_URL=https://<auth-domain>" --service frontend --skip-deploys
railway variable set "VITE_PROJECTS_API_BASE_URL=https://<projects-domain>" --service frontend --skip-deploys
railway variable set "VITE_COMERCIAL_API_BASE_URL=https://<comercial-domain>" --service frontend --skip-deploys
railway up frontend --path-as-root --service frontend --detach --ci
railway domain --service frontend            # genera <frontend-domain>.up.railway.app
railway domain update <frontend-domain> --port 80 --service frontend

# 6. Cerrar el círculo: los backends necesitan saber el dominio del frontend
railway variable set "APP_BASE_URL=https://<frontend-domain>" --service auth --skip-deploys
railway variable set 'CORS_ORIGINS=["https://<frontend-domain>"]' --service auth   # dispara redeploy
railway variable set 'CORS_ORIGINS=["https://<frontend-domain>"]' --service projects
railway variable set 'CORS_ORIGINS=["https://<frontend-domain>"]' --service comercial

# 7. Crear el usuario administrador y los datos de ejemplo
railway variable list --service Postgres --json   # copiar DATABASE_PUBLIC_URL
cd services/auth && source .venv/Scripts/activate
DATABASE_URL="postgresql+psycopg://...<DATABASE_PUBLIC_URL con el driver +psycopg>..." \
SEED_ADMIN_EMAIL=maya@grupomactral.com SEED_ADMIN_PASSWORD='Mactral2026!' \
python seed.py

cd ../projects && source .venv/Scripts/activate
DATABASE_URL="postgresql+psycopg://...<misma DATABASE_PUBLIC_URL>..." python seed.py

cd ../comercial && source .venv/Scripts/activate
DATABASE_URL="postgresql+psycopg://...<misma DATABASE_PUBLIC_URL>..." python seed.py
```

### Gotchas encontrados

- **502 "Application failed to respond"** justo después de cada primer
  deploy: Railway no sabía a qué puerto interno enrutar el tráfico público.
  Con `auth` y `frontend` (puertos fijos 8000 y 80 en su Dockerfile) se
  resolvió con `railway domain update <dominio> --port <puerto-fijo>`. Con
  `projects` (cuyo Dockerfile usa `${PORT:-8100}`, portable a propósito)
  Railway inyectó su propio `$PORT` (resultó ser 8080, no 8100 ni el que uno
  esperaría) — hay que revisar `railway logs --service <nombre>` para ver en
  qué puerto quedó escuchando uvicorn realmente y usar ese valor en
  `railway domain update`, no asumirlo.
- **Auto-deploy por GitHub falla en un monorepo** sin poder fijar "Root
  Directory" desde el CLI (ver sección de arriba) — hay que hacerlo una vez
  por servicio desde el dashboard.
- **"Free plan resource provision limit exceeded"** al agregar el 5to
  servicio (`comercial`): el plan gratuito de Railway limita cuántos
  servicios/recursos se pueden crear. Se resolvió reintentando el mismo
  `railway add --service ...` más tarde; si vuelve a pasar, revisar el plan
  en el dashboard antes de gastar tiempo depurando el comando.
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

Repetir en cada servicio (`services/auth`, `services/projects`,
`services/comercial`):
```bash
cd services/auth   # o services/projects, o services/comercial
source .venv/Scripts/activate
pytest --cov --cov-report=term-missing
# umbral 90%; auth 96%, projects 100%, comercial 97%
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

### E2-H1
- Alta exitosa (`POST /leads`, `services/comercial/app/services/lead_service.py`)
  → lead con estado `COTIZAR` y consecutivo automático `MOB26-XXX` /
  `IND26-XXX` según línea de negocio, con contador por (línea, año) protegido
  con `SELECT ... FOR UPDATE` para altas concurrentes.
- Campos obligatorios incompletos (nombre, y al menos teléfono o correo) →
  422 con el mensaje exacto "Completa los campos requeridos"
  (`app/schemas.py`), sin crear el registro.
- Registro de interacción posterior (`POST /leads/{id}/interactions`) → queda
  en el historial del lead con fecha, canal, resumen y usuario.
- Solo el vendedor asignado (por `vendedor_id`, tomado del JWT al crear el
  lead) o Gerencia pueden agregar interacciones; solo roles Comercial o
  Gerencia pueden crear leads (`can_manage_leads` en `app/domain.py`).
- Frontend: página dedicada del módulo Comercial
  (`frontend/src/pages/ComercialPage.tsx`) con KPIs por estado, listado,
  formulario de alta y panel de interacciones por lead.

### E2-H2
- Generación de cotización (`POST /leads/{id}/quotations`,
  `services/comercial/app/services/quotation_service.py`) → PDF construido
  con `reportlab` (`app/pdf.py`), guardado como `LargeBinary` directamente en
  Postgres (no en el filesystem, para portabilidad en Railway), adjunto al
  lead; si el lead estaba en `COTIZAR` el estado cambia a `ENVIADA` (solo la
  primera vez, no en regeneraciones posteriores).
- Calculadora oficial: la API valida que `anticipo_inicial_pct +
  segundo_anticipo_pct + saldo_final_pct == 100` y que `valor_equipo > 0`
  (`app/schemas.py`, `QuotationCreate`); no admite texto libre.
- Regeneración (`POST` repetido sobre el mismo lead) → incrementa la versión
  (`v1`, `v2`, ...) conservando las versiones anteriores en el historial;
  número de cotización = `{código del lead}-v{versión}`.
- Descarga del PDF (`GET /leads/{id}/quotations/{version}/pdf`); solo el
  vendedor asignado o Gerencia pueden generar/ver cotizaciones (mismo
  `can_edit_lead` de E2-H1).
- Frontend: tarjeta "Cotización" en `ComercialPage.tsx` con formulario,
  desglose en vivo, historial de versiones y botón "Vista previa" que abre el
  PDF en una pestaña nueva (usando `comercialFetchBlob` porque un `<a href>`
  normal no puede enviar el header `Authorization`).

## Notas de la migración de stack

Este proyecto empezó como un monolito Next.js/Prisma/SQLite (historia E1-H1).
Se migró completamente a React + Python + Postgres a partir de E1-H2 por
decisión explícita del proyecto (ver `CLAUDE.md`, sección Arquitectura).
