# Documento de Arquitectura — Plataforma Grupo Mactral

## 1. Visión general

Arquitectura de **microservicios**: frontend SPA en React y tres backends
independientes en Python/FastAPI, todos respaldados por una única instancia
de **PostgreSQL** (bases lógicas separadas por prefijo/tabla de versión de
Alembic, no por base de datos física). Todo el stack corre en contenedores
Docker, tanto en desarrollo local (`docker-compose.yml`) como en producción
(Railway, un servicio Railway por contenedor).

```
                         ┌─────────────────────┐
                         │   Frontend (React)  │
                         │  Vite + TypeScript   │
                         │  nginx (prod build)  │
                         └──────────┬───────────┘
                                    │ HTTPS (JWT en Authorization header)
            ┌───────────────────────┼───────────────────────┐
            │                       │                       │
   ┌────────▼────────┐    ┌─────────▼─────────┐   ┌─────────▼─────────┐
   │  services/auth   │    │ services/projects  │   │ services/comercial │
   │  FastAPI         │    │  FastAPI           │   │  FastAPI           │
   │  usuarios/roles  │    │  CRP, financiero,   │   │  leads, cotiza-    │
   │  login/JWT       │    │  logística, KPIs,   │   │  ciones, stock     │
   │                  │    │  notificaciones,    │   │                    │
   │                  │    │  comentarios        │   │                    │
   └────────┬─────────┘    └─────────┬──────────┘   └─────────┬──────────┘
            │                        │                        │
            └────────────────────────┼────────────────────────┘
                                      │
                             ┌────────▼────────┐
                             │   PostgreSQL     │
                             │  (una instancia,  │
                             │ tablas por        │
                             │  servicio)        │
                             └──────────────────┘
```

`comercial` llama internamente a `projects` (HTTP, reenviando el JWT del
usuario que cerró la venta) para crear el Registro Maestro — es el único
acoplamiento directo entre servicios de negocio; el resto de la
comunicación pasa siempre por el frontend.

## 2. Stack tecnológico

| Capa | Tecnología |
|---|---|
| Frontend | React 18 + TypeScript + Vite, sin librería de UI de terceros (CSS propio) |
| Backend | Python 3.12/3.13 + FastAPI + SQLAlchemy 2.0 (ORM) + Alembic (migraciones) + Pydantic (validación) |
| Base de datos | PostgreSQL 16 (producción y Docker); SQLite en memoria para tests unitarios |
| Autenticación | JWT firmado con `JWT_SECRET` compartido entre los 3 backends (HS256); `auth` es el único que emite tokens, `projects` y `comercial` solo los verifican |
| Contenedores | Docker (`Dockerfile` por servicio) + `docker-compose.yml` para desarrollo local |
| Despliegue | Railway (`railway up <carpeta> --path-as-root --service <nombre>`), un servicio por contenedor + Postgres gestionado |
| Testing | `pytest` + `pytest-cov` (umbral 90% de cobertura por servicio) en backend; Playwright para pruebas end-to-end del flujo completo |
| PDF | `reportlab` (cotizaciones comerciales), almacenado como `LargeBinary` en Postgres (no en filesystem, por portabilidad en Railway) |

## 3. Servicios backend

### 3.1 `services/auth`
Fuente única de verdad de usuarios, roles y control de acceso por módulo.

- **Modelos**: `User` (nombre, correo, rol, línea de negocio, estado,
  contraseña hasheada), tokens de activación/recuperación.
- **Roles fijos** (`app/domain.py`, `Rol`): `COMERCIAL`, `IMPORTACIONES`,
  `TECNICO`, `ADMINISTRATIVO`, `GERENCIA`.
- **`ROLE_MODULE_ACCESS`**: mapa rol → conjunto de módulos visibles; es la
  única fuente de autorización real (el frontend mantiene una copia mínima
  solo para no renderizar enlaces a módulos prohibidos — la autorización
  efectiva siempre se revalida en el backend correspondiente).
- **Endpoints clave**: `POST /auth/login`, `POST /auth/refresh`,
  `POST /auth/forgot-password`, `POST /auth/reset-password`,
  `GET /me` (perfil + `accessible_modules`), CRUD de usuarios
  (`POST/PATCH /users`, solo Gerencia).
- Bloqueo de cuenta tras 5 intentos fallidos (15 min), expiración de sesión
  por inactividad vía JWT de 8h renovado por el frontend mientras hay
  actividad.

### 3.2 `services/projects`
El servicio más grande: contiene la ficha central del proyecto (CRP) y
todo lo construido sobre ella en las épicas 3 a 11.

- **`Project`**: entidad raíz — código CRP, tipo, cliente, ciudad,
  producto, marca, etapa actual, semáforo de entrega, `valor_contrato`,
  `costo_fabricacion`, `planos_aprobados_fecha`,
  `anticipo1_solicitud_confirmada`.
- **`ProjectModuleStatus`**: estado (`PENDIENTE`/`EN_CURSO`/`CERRADO`/
  `BLOQUEADO`/`ENTREGADO`) de cada módulo (Comercial, Reg. maestro,
  Importaciones, Técnico) para ese proyecto.
- **`ProjectEvent`**: línea de tiempo — cada acción relevante de cualquier
  módulo agrega un evento (`origen`, `mensaje`, `fecha`); es el mecanismo
  central de trazabilidad y el que alimenta casi todas las notificaciones
  automáticas de la plataforma.
- **`ImportChecklistItem`**: checklist documental de importación (14 ítems,
  solo proyectos GM).
- **`Installation` / `InstallationReprogramming`**: programación de
  instalación, historial de reprogramaciones, acta de entrega.
- **`Cuota`**: cuotas/anticipos del contrato (cuenta por cobrar), máximo 3
  por proyecto, con flags `alertada_proxima` / `alertada_vencida` para no
  duplicar alertas.
- **`CuentaPorPagar`**: gasto logístico / obligación con proveedor — diseño
  deliberadamente compartido entre E7-H3 (CxP consolidado), E8-H1 (registro
  de gasto logístico) y E8-H3 (imputación automática): cada fila lleva su
  `project_id`, así que aparece "gratis" en el tablero financiero y en el
  consolidado del proyecto sin lógica adicional.
- **`Notificacion`**: bandeja de asignación a módulo / inactividad (>5 días
  sin eventos nuevos), filtrada por los módulos visibles del rol.
- **`Comentario`**: comentarios de texto libre por proyecto, con detección
  de menciones `@usuario` al leer (no requiere un directorio de usuarios en
  este servicio).
- **Routers**: `projects.py` (CRP, checklist, instalación),
  `financiero.py` (cuotas, tablero, CxP consolidado, confirmación de
  Anticipo 1), `logistica.py` (gastos y soportes), `notificaciones.py`,
  `comentarios.py`, `reportes.py` (dashboard, rentabilidad, KPIs).

### 3.3 `services/comercial`
Ciclo de vida del lead comercial hasta el cierre de la venta.

- **`Lead`**: datos de contacto, línea de negocio, estado
  (`COTIZAR`→`ENVIADA`→`VENDIDO`, secuencial y no reversible), consecutivo
  `MOB26-XXX`/`IND26-XXX`.
- **`Quotation`**: cotización en PDF versionada (`v1`, `v2`, ...), generada
  con `reportlab` y guardada en base de datos.
- **`StockItem` / `StockMovement`**: inventario de unidades disponibles
  (Mobility/Industry) con historial de entradas/salidas.
- Al marcar un lead como `VENDIDO`, `estado_service.py` llama a
  `services/projects` (`clients/projects_client.py`) reenviando el JWT del
  vendedor para crear el Registro Maestro correspondiente.

## 4. Frontend

SPA de React con rutas protegidas por rol (`ProtectedRoute` +
`AuthContext`, que guarda el JWT y el usuario en memoria/localStorage).

- **`domain.ts`**: copia mínima de catálogos del backend (roles, módulos,
  labels de UI) — solo para render, la autorización real vive en el
  backend.
- **`AppShell.tsx`**: layout común (sidebar de módulos filtrado por
  `accessibleModules`, topbar con búsqueda rápida y notificaciones).
- Una página dedicada por módulo (`ComercialPage`, `RegMaestroPage`,
  `ImportacionesPage`, `TecnicoPage`, `StockPage`, `FinancieroPage`,
  `LogisticaPage`, `NotificacionesPage`, `UsuariosPage`,
  `DashboardPage`), cada una consumiendo el backend correspondiente vía
  `api/client.ts` (`apiFetch`/`projectsApiFetch`/`comercialApiFetch`, y
  variantes multipart/blob para adjuntos).

## 5. Patrones de diseño reutilizados

Estos patrones se establecieron en las primeras historias y se repitieron
deliberadamente en todas las siguientes para mantener el código
predecible:

- **Alertas "una sola vez"**: en vez de un job/cron en segundo plano (no
  existe infraestructura de background jobs), las alertas que dependen del
  tiempo (semáforo de entrega, cuotas por vencer, inactividad de
  notificaciones) se **recalculan en cada lectura** y usan un flag booleano
  en el modelo (`alertada_proxima`, `notificado_anticipo2`, etc.) para no
  duplicar el evento/notificación en lecturas sucesivas.
- **Disparadores automáticos vía eventos de checklist**: en lugar de crear
  endpoints nuevos para "avisar que hay que cobrar", el archivado de un
  ítem específico del checklist (BL → Anticipo 2; los dos ítems de plano →
  Anticipo 1) dispara automáticamente un `ProjectEvent` de origen
  "Sistema".
- **Contadores concurrentes con `SELECT ... FOR UPDATE`**: todos los
  consecutivos (leads, proyectos, cuotas) usan lock de fila para evitar
  duplicados con altas simultáneas.
- **Diseño de modelos reutilizado entre historias**: `CuentaPorPagar` sirve
  a tres historias distintas (E7-H3, E8-H1, E8-H3) sin duplicar tablas ni
  lógica de negocio, apoyándose en que cada fila ya lleva su `project_id`.
- **Adjuntos como `LargeBinary` en Postgres**: cotizaciones PDF, actas de
  entrega, soportes de checklist y de gastos logísticos se guardan en la
  base de datos, no en el filesystem del contenedor (que no persiste entre
  despliegues en Railway).
- **JWT compartido, sin sesión centralizada**: `projects` y `comercial` no
  emiten tokens ni consultan a `auth` en cada request — solo verifican la
  firma del JWT con el mismo `JWT_SECRET`, lo que evita un punto único de
  fallo síncrono entre servicios.

## 6. Base de datos

Una sola instancia física de PostgreSQL, con:
- Tablas prefijadas/agrupadas lógicamente por servicio.
- Una tabla `alembic_version_<servicio>` por servicio, para que cada uno
  gestione sus propias migraciones de forma independiente sin pisarse.
- Migraciones secuenciales por servicio (ej. `services/projects/alembic/
  versions/0001...0009`), cada una con su `upgrade()`/`downgrade()`.

**Nota técnica sobre enums de Postgres** (relevante para quien agregue
migraciones nuevas):
- `op.create_table()` con una columna `sa.Enum(...)` **sí** emite
  automáticamente el `CREATE TYPE`.
- `op.add_column()` con una columna de tipo enum **no** lo emite — hay que
  llamar explícitamente a `enum.create(op.get_bind(), checkfirst=True)`
  antes.
- Si un tipo enum ya existe y se referencia en un `create_table` **nuevo**,
  hay que usar `postgresql.ENUM(..., create_type=False)` (no
  `sa.Enum(create_type=False)`, que pierde el flag) para evitar un
  `DuplicateObject` al desplegar.

## 7. Despliegue

- **Desarrollo local**: `docker-compose.yml` levanta Postgres + los 3
  backends + frontend + contenedores `seed*` de una sola corrida para datos
  de ejemplo.
- **Producción (Railway)**: 5 servicios — `Postgres` (plugin gestionado),
  `auth`, `projects`, `comercial`, `frontend` — cada uno desplegado con
  `railway up <carpeta> --path-as-root --service <nombre> --detach --ci`
  desde su propio `Dockerfile`. Variables de entorno clave: `DATABASE_URL`,
  `JWT_SECRET` (igual en los 3 backends), `CORS_ORIGINS`,
  `VITE_*_API_BASE_URL` (frontend, baked at build time).
- **URLs actuales**:
  - Frontend: https://frontend-production-1622.up.railway.app
  - Auth: https://auth-production-b32d.up.railway.app
  - Projects: https://projects-production-826d.up.railway.app
  - Comercial: https://comercial-production-7e35.up.railway.app
- El auto-deploy desde GitHub está conectado pero pendiente de fijar "Root
  Directory" por servicio en el dashboard de Railway (ver `README.md` para
  el detalle); mientras tanto, cada cambio se despliega manualmente con
  `railway up`.

## 8. Flujo de trabajo de desarrollo (convención del proyecto)

Definido en `CLAUDE.md` y aplicado a partir de la Épica 3:
1. Una rama por historia de usuario, creada desde `dev`.
2. Implementación + pruebas unitarias con cobertura ≥90%.
3. Verificación end-to-end con Playwright: capturas y video por historia
   (solo se conservan los artefactos de la corrida exitosa).
4. `Prueba_e2e.mjs` (`.scratch/`, no versionado) se extiende — no se
   reemplaza — con cada historia nueva, cubriendo en un solo video
   acumulativo todo lo implementado hasta ese momento.
5. Merge a `dev` con `--no-ff`, reconfirmando la suite completa de los 3
   servicios backend post-merge.
6. Push a `origin` solo si todas las pruebas pasan.
7. Deploy a Railway del/los servicio(s) modificado(s).

## 9. Límites conocidos / deuda técnica

- El envío de correo (recuperación de contraseña, notificación de
  anticipos) es un *stub*: queda registrado en los logs del servicio, no
  se envía un correo real.
- No hay infraestructura de background jobs / cron; toda alerta dependiente
  del tiempo se recalcula de forma perezosa en cada lectura (ver sección 5).
- El auto-deploy por GitHub en Railway no está completamente configurado
  (falta fijar Root Directory por servicio); los despliegues son manuales.
- Las tasas de cambio del tablero financiero son valores de referencia
  estáticos, no una integración en vivo con un proveedor de tasas.
