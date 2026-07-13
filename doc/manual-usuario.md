# Manual de Usuario — Plataforma Grupo Mactral

## 1. Introducción

Esta plataforma acompaña el ciclo completo de un proyecto de Grupo Mactral:
desde que un lead comercial entra por primera vez, pasando por la
importación del equipo, su instalación, la gestión financiera y logística,
hasta el reporte gerencial de rentabilidad. Está organizada en módulos que
aparecen en el menú lateral según el rol del usuario que inició sesión.

**URL de producción:** https://frontend-production-1622.up.railway.app

## 2. Roles

La plataforma tiene 5 roles fijos. Cada uno ve solo los módulos que le
corresponden en el menú lateral (si intenta entrar a un módulo no permitido
por la URL, la aplicación lo redirige al Dashboard con un aviso):

| Rol | Módulos visibles |
|---|---|
| **Gerencia** | Todos: Comercial, Reg. maestro, Importaciones, Técnico, Stock, Financiero, Logística, Administración, Notificaciones, Dashboard (con KPIs y rentabilidad) |
| **Comercial** | Comercial, Reg. maestro, Stock (solo consulta) |
| **Importaciones** | Importaciones, Reg. maestro |
| **Técnico** | Técnico, Reg. maestro, Stock (solo consulta) |
| **Administrativo** | Financiero, Logística, Stock, Reg. maestro |

Todos los roles, sin excepción, tienen acceso a **Reg. maestro** (la ficha
central del proyecto) y a **Notificaciones**.

## 3. Iniciar sesión

1. Ir a la URL de la plataforma → pantalla de login.
2. Ingresar correo y contraseña.
3. Tras 5 intentos fallidos seguidos, la cuenta queda bloqueada 15 minutos.
4. "¿Olvidaste tu contraseña?" envía un enlace de recuperación (válido una
   sola vez) al correo registrado.
5. La sesión expira automáticamente tras 8 horas de inactividad.

Usuario de referencia (ambiente de pruebas/demo):
`maya@grupomactral.com` / `Mactral2026!` (rol Gerencia).

## 4. Administración de usuarios (solo Gerencia)

En **Administración**:
- **Crear usuario**: nombre, correo, rol y línea de negocio (Mobility /
  Industry / Ambas). Se genera un enlace de activación de un solo uso donde
  el nuevo usuario define su contraseña.
- **Activar / desactivar**: cambia el estado del usuario sin borrar su
  historial.

## 5. Módulo Comercial

Gestión de leads (clientes potenciales), del primer contacto hasta el
cierre de la venta.

1. **Registrar un lead**: nombre, teléfono/correo, ciudad, canal de entrada,
   línea de negocio, producto solicitado y marca. Se genera un consecutivo
   automático (`MOB26-XXX` / `IND26-XXX`).
2. **Cotizar**: desde la ficha del lead, "Generar cotización PDF" abre la
   calculadora oficial (valor del equipo, tipo de pago, % de anticipos que
   deben sumar 100%, fecha estimada de entrega). Cada regeneración crea una
   nueva versión y conserva el historial completo; el estado pasa
   automáticamente a **Enviada** la primera vez.
3. **Avanzar el estado**: Cotizar → Enviada → Vendido, en ese orden
   estricto (no se puede saltar ni retroceder).
4. **Marcar como Vendido**: obliga a elegir la clasificación de la venta:
   - **GM (Registro Maestro)**: abre el flujo completo (Importaciones →
     Técnico). Se genera un código `GM26-XX`.
   - **Stock — Mobility / Industry**: reserva una unidad del inventario y
     va directo a Técnico. Se genera un código `STMB26-XX` / `STIN26-XX`.
     Si no hay unidades disponibles, el sistema bloquea el cierre con el
     mensaje "No hay unidades disponibles".
5. El código generado queda visible en la ficha del lead y es el mismo que
   se usa para buscar el proyecto en **Reg. maestro** y en el resto de los
   módulos.

## 6. Reg. maestro — Ficha central del proyecto (CRP)

Accesible para todos los roles. Buscar por código CRP (`GM26-XX`, etc.) o
por nombre de cliente.

La ficha muestra, de solo lectura:
- **Datos del proyecto**: tipo, cliente, ciudad, producto, marca.
- **Estado de módulos**: en qué módulo está el proyecto y si esa etapa está
  cerrada (🔒 candado).
- **Línea de tiempo**: todos los eventos del proyecto en orden cronológico
  — ventas, notificaciones automáticas, cuotas, pagos, gastos logísticos,
  instalación, etc. — con su origen (Comercial, Sistema, Financiero,
  Logística, Importaciones, Técnico).
- **Comentarios**: cualquier usuario puede dejar un comentario de texto
  libre en el proyecto. Escribir `@usuario` resalta la mención (no envía
  notificación automática, es solo una referencia visual).

## 7. Módulo Importaciones (proyectos GM)

Checklist documental de 14 ítems (planos, proforma, SWIFT, BL, etc.), cada
uno **Requerido** u **Opcional**.

1. Marcar cada ítem como **Archivado** (con adjunto opcional) o **No
   aplica** (requiere justificación escrita obligatoria).
2. Al archivar el ítem "HAWBL / BL" se dispara automáticamente en la línea
   de tiempo del proyecto la solicitud de **Anticipo 2** a Financiero.
3. Al archivar los dos ítems de plano ("Detalle de Plano" y "Planos / OT")
   se dispara automáticamente la solicitud de **Anticipo 1**.
4. **Enviar a Técnico**: solo se habilita cuando todos los ítems requeridos
   están completos. Si queda algún ítem requerido pendiente, existe una
   excepción de "ingreso a bodega" que exige una nota de justificación.

## 8. Módulo Técnico

1. **Programar instalación**: fecha, técnico asignado, ciudad. No se puede
   programar antes de la fecha de ingreso a bodega registrada en
   Importaciones.
2. **Reprogramar**: cambia la fecha con un motivo obligatorio; queda un
   historial de reprogramaciones.
3. **Registrar acta de entrega**: fecha real de entrega, observaciones y
   adjunto opcional del acta firmada. Si no se adjunta el acta, la
   plataforma muestra una advertencia (no bloquea el cierre).
4. Al registrar la entrega se dispara automáticamente la solicitud del
   **Pago Final** en la línea de tiempo.
5. **Semáforo de cumplimiento** (visible en la ficha del proyecto):
   - 🟢 Verde: instalación completada dentro de la fecha comprometida.
   - 🟡 Amarillo: instalación completada con retraso menor, o próxima a
     vencer sin cerrar.
   - 🔴 Rojo: instalación programada cuya fecha ya venció sin cerrarse.

## 9. Módulo Stock

Inventario de unidades disponibles para venta directa (Mobility/Industry).

1. **Registrar entrada**: línea de negocio, tipo de producto, color,
   cantidad. Si la referencia no existía, se crea automáticamente.
2. Cada venta clasificada como Stock (ver Comercial, paso 4) descuenta
   automáticamente una unidad disponible.
3. La tabla muestra disponible / total / último movimiento, con la
   etiqueta "Agotado" cuando el disponible llega a cero.

## 10. Módulo Financiero

Gestión de cuotas, cobros y el tablero financiero de cada proyecto.

1. **Configurar el esquema de pagos**: valor del contrato, costo de
   fabricación, y hasta 3 cuotas (etiqueta, monto, % y fecha de
   vencimiento). La suma de las cuotas debe igualar exactamente el valor
   del contrato. Una vez configurado no se puede reconfigurar.
2. **Registrar un pago**: fecha, monto y referencia bancaria; queda en la
   línea de tiempo del proyecto.
3. **Tablero financiero** por proyecto: total cobrado / por cobrar, gastos
   logísticos, margen bruto, semáforo de pago (🟢 al día / 🟡 por vencer en
   7 días / 🔴 vencida) y tasas de cambio de referencia (USD/EUR/GBP/CNY).
4. **Alertas de cuotas**: una cuota pendiente que vence en menos de 7 días
   o que ya venció muestra un badge ("Por vencer" / "Vencida") junto a la
   fila y queda registrada en la línea de tiempo (una sola vez).
5. **Confirmar solicitud de Anticipo 1**: cuando los planos quedan
   aprobados (ver Importaciones), aparece un botón para que Administrativo
   confirme que ya envió la solicitud al cliente; queda registrado con su
   nombre en la línea de tiempo.
6. **Cuentas por pagar (consolidado)**: todos los gastos logísticos de
   todos los proyectos, con filtros por proveedor, moneda y estado, y
   totales pendiente/pagado.

## 11. Módulo Logística

Registro de la programación de viajes asociados a la instalación de un
proyecto (vuelos, hospedaje, transporte, viáticos).

1. **Registrar un gasto logístico**: tipo, proveedor, concepto, monto,
   moneda y fecha. Los **viáticos exigen marcar la casilla de autorización
   del Gerente General**; sin ella, el sistema rechaza el registro.
2. **Adjuntar el soporte** (factura/comprobante) una vez registrado el
   gasto.
3. Cada gasto queda automáticamente imputado al proyecto: aparece en su
   margen bruto (módulo Financiero) y en el consolidado de cuentas por
   pagar, sin ningún paso adicional.

## 12. Notificaciones

Bandeja accesible a todos los roles desde la topbar ("Notificaciones").
Muestra, filtradas a los módulos visibles para el rol:
- **Asignación**: un proyecto entró a un módulo (ej. "Proyecto GM26-05
  asignado al módulo" Técnico).
- **Inactividad**: un proyecto lleva más de 5 días sin novedades en un
  módulo que sigue En curso.

Cada notificación enlaza al módulo correspondiente y se puede marcar como
leída (deja de listarse).

## 13. Dashboard

- **Todos los roles**: proyectos activos vs. entregados, conteo por
  semáforo (verde/amarillo/rojo) y listado completo de proyectos con su
  etapa y semáforo.
- **Solo Gerencia**: además del dashboard general —
  - **Rentabilidad por proyecto**: contrato, fabricación, logística, margen
    bruto y margen % de cada proyecto con esquema de pagos configurado, más
    los totales agregados.
  - **KPIs operativos**: proyectos GM con checklist incompleto,
    instalaciones programadas/completadas, notificaciones pendientes.
  - **KPIs financieros**: total cobrado, por cobrar, gastos logísticos
    pendientes/pagados y margen bruto total, agregados de toda la
    plataforma.

## 14. Preguntas frecuentes

**¿Por qué no veo un módulo en el menú?**
Tu rol no tiene acceso a ese módulo. Ver la tabla de la sección 2.

**¿Por qué no puedo editar un campo/etapa que aparece con 🔒?**
Esa etapa ya está cerrada; los datos quedan protegidos de edición para
mantener la trazabilidad histórica.

**Configuré mal el esquema de pagos, ¿puedo corregirlo?**
No desde la interfaz normal — una vez configuradas, las cuotas de un
proyecto no se pueden reconfigurar. Contactar a Gerencia.

**¿Dónde veo el correo de recuperación de contraseña si no llega?**
En el ambiente de pruebas el envío de correo es un *stub*: el enlace queda
registrado en los logs del servicio `auth`, no se envía un correo real.
