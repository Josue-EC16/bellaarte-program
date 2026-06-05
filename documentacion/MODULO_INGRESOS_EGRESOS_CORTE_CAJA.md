# MODULO INGRESOS, EGRESOS Y CORTE DE CAJA

## Resumen

El módulo `Economía` centraliza la lectura financiera operativa de BellaArte Boutique sin romper la lógica de los módulos origen.

En esta v1:

- `VENTA_BOUTIQUE`, `PAGO_PEDIDO` y `SALIDA_FLETE` siguen siendo ingresos históricos aun si luego se anulan o cancelan
- la salida real de dinero se registra exclusivamente con `egreso`
- toda devolución al cliente se fuerza mediante el flujo económico obligatorio
- `ADMIN` ve el panorama global
- `CAJA` opera su período activo y su historial propio con restricciones de privacidad
- todos los agregados oficiales se calculan en `BOB`
- cuando aplica, también se conserva `MONEDA`, `MONTO_MONEDA_ORIGEN` y `TIPO_CAMBIO_USADO`

## Objetivo funcional

El módulo resuelve tres necesidades del negocio:

1. Separar el hecho operativo del hecho económico.
2. Registrar devoluciones parciales o totales sin distorsionar el histórico bruto de ingresos.
3. Controlar períodos de caja por cajero mediante `corte_caja`.

## Tablas involucradas

### Núcleo económico

- `egreso`
- `corte_caja`

### Fuentes de ingreso derivadas

- `venta_boutique`
- `pago_pedido`
- `salida_flete`

### Relacionadas

- `usuarios`
- `cliente`
- `moneda`
- `comprobante_interno`
- `auditoria_sistema`

## Regla contable principal

Los ingresos válidos del sistema se consideran realizados cuando se registran en:

- `venta_boutique`
- `pago_pedido`
- `salida_flete`

Si luego el origen se anula o cancela:

- el ingreso bruto permanece visible en reportes económicos
- no se descuenta automáticamente del histórico
- la devolución real de dinero se refleja mediante uno o varios `egreso` de tipo `DEVOLUCION`

Esto permite cubrir correctamente:

- devoluciones totales
- devoluciones parciales
- devoluciones diferidas
- anulaciones con trazabilidad administrativa

## Estructura económica nueva

### `egreso`

Campos operativos principales:

- `usu_id`
- `cco_id`
- `egr_fec`
- `egr_tipo`
- `egr_concepto`
- `egr_cantidad`
- `egr_precio_unidad`
- `egr_beneficiario`
- `egr_monto`
- `egr_obs1`
- `egr_obs2`
- `egr_estado`
- `egr_fec_camb_est`
- `egr_motivo_camb_est`

Extensión aprobada para devoluciones:

- `egr_tabla_ref`
- `egr_id_ref`

Reglas:

- si `egr_tipo = DEVOLUCION`, ambas referencias son obligatorias
- `egr_tabla_ref` solo admite:
  - `venta_boutique`
  - `pago_pedido`
  - `salida_flete`
- si no es devolución, ambas referencias deben quedar nulas
- para devoluciones se fuerza:
  - `egr_cantidad = 1`
  - el monto se captura en `egr_precio_unidad`

### `corte_caja`

Campos operativos principales:

- `usu_id_cajero`
- `usu_id_admin`
- `cco_fec_apertura`
- `cco_fec_cierre`
- `cco_fondo_asignado`
- `cco_obs_apertura`
- `cco_obs_cierre`
- `cco_estado`

Reglas:

- solo puede existir un corte abierto por cajero
- `cerrado_observado` exige observación de cierre
- los cortes cerrados son inmutables

## Flujo obligatorio de devolución económica

Las anulaciones y cancelaciones económicas ya no se cierran directamente desde:

- ventas boutique
- pagos de pedido
- salidas de flete

Ahora el flujo correcto es:

1. el usuario inicia la anulación o cancelación desde el módulo origen
2. el frontend redirige a `/app/economia/egresos?mode=refund...`
3. el backend carga el `refund-context`
4. el usuario registra cuánto dinero se devuelve realmente
5. el backend crea el `egreso` de tipo `DEVOLUCION`
6. en la misma transacción cambia el estado del origen
7. se ejecutan stock, saldo, comprobante y auditoría ya existentes

## Casos soportados

### Venta boutique

- el ingreso bruto histórico sigue visible aunque la venta quede `CANCELADA` o `ANULADA`
- la devolución económica puede ser total o parcial
- el stock vuelve según la lógica del módulo de ventas

### Pago de pedido

- el pago sigue figurando como ingreso histórico realizado
- el saldo del pedido se recalcula cuando el pago se anula
- la devolución real al cliente se registra aparte como egreso

### Salida de flete

- el ingreso económico solo considera `SFL_TOTAL_FLETE`
- la garantía no se trata como ingreso principal
- una devolución económica asociada al flete queda como `egreso` de tipo `DEVOLUCION`

## Reportes económicos

### Administración global

`ADMIN` dispone de:

- `Estado de Resultados`
- `Flujo de Efectivo`
- reporte por cajero
- listado unificado de ingresos
- listado y detalle de egresos
- cortes de caja globales
- exportación CSV

### Vista del cajero

`CAJA` dispone de:

- `Mi Período`
- `Mi Estado de Resultados`
- `Mi Historial`
- su corte activo
- sus egresos y devoluciones dentro del período habilitado

Reglas de privacidad para cajero:

- el historial cerrado enmascara ingresos y resultados como `***`
- los CSV del cajero respetan el mismo enmascaramiento
- no se exponen observaciones internas del admin en cierres cerrados

## Moneda y conversión

Los reportes y listados de ingresos incluyen, cuando aplica:

- `MONEDA`
- `SIMBOLO`
- `MONTO_MONEDA_ORIGEN`
- `TIPO_CAMBIO_USADO`
- `MONTO_BOB`

Reglas:

- los gráficos agregados siempre usan `BOB`
- la moneda origen se muestra como dato de trazabilidad
- no se mezclan monedas distintas dentro de una misma serie agregada

## Seguridad y permisos

Permisos nuevos:

- `economy_expenses:list`
- `economy_expenses:view`
- `economy_expenses:create`
- `economy_expenses:annul`
- `cash_cuts:list`
- `cash_cuts:view`
- `cash_cuts:open`
- `cash_cuts:close`
- `cash_cuts:view_own`
- `economy_income:view`
- `economy_income:view_all`
- `economy_refunds:create`
- `economy_reports:view`
- `economy_reports:view_all`
- `economy_reports:export`

Asignación:

- `ADMIN`: acceso completo
- `CAJA`: acceso económico operativo limitado por backend
- otros roles: sin acceso por defecto

## API pública

Router:

- `/api/v1/economia`

Ingresos:

- `GET /api/v1/economia/ingresos`
- `GET /api/v1/economia/ingresos/{origin_type}/{origin_id}/refund-context`

Devoluciones:

- `POST /api/v1/economia/devoluciones`

Egresos:

- `POST /api/v1/economia/egresos`
- `GET /api/v1/economia/egresos`
- `GET /api/v1/economia/egresos/{expense_id}`
- `PATCH /api/v1/economia/egresos/{expense_id}/annul`

Cortes:

- `POST /api/v1/economia/cortes-caja`
- `PATCH /api/v1/economia/cortes-caja/{cut_id}/close`
- `GET /api/v1/economia/cortes-caja`
- `GET /api/v1/economia/cortes-caja/{cut_id}`
- `GET /api/v1/economia/cortes-caja/me`
- `GET /api/v1/economia/cortes-caja/me/history`

Reportes:

- `GET /api/v1/economia/reportes/estado-resultados`
- `GET /api/v1/economia/reportes/flujo-efectivo`
- `GET /api/v1/economia/reportes/cajeros/{user_id}`
- `GET /api/v1/economia/reportes/mi-periodo`
- `GET /api/v1/economia/reportes/mi-estado-resultados`
- `GET /api/v1/economia/reportes/mi-historial`

Todos los reportes aceptan:

- `format=json`
- `format=csv`

## Frontend

Rutas SPA nuevas:

- `/app/economia`
- `/app/economia/egresos`
- `/app/economia/cortes-caja`
- `/app/economia/reportes`

Páginas:

- `EconomyDashboardPage.jsx`
- `EconomyExpensesPage.jsx`
- `CashCutsPage.jsx`
- `EconomyReportsPage.jsx`

Experiencia de usuario:

- dashboard distinto para `ADMIN` y `CAJA`
- flujo `refund` obligatorio por query params
- drawers y modales con `maskClosable={false}`
- filtros persistidos con `sessionStorage`
- reportes con `Recharts`
- navegación de reversión desde ventas, pagos y fletes hacia economía

## Validaciones críticas

- `CAJA` no puede registrar egresos sin corte abierto
- `ADMIN` puede registrar egresos sin corte
- `CAJA` no puede anular egresos de cortes cerrados
- la suma de devoluciones activas no puede superar el monto bruto del ingreso origen
- las anulaciones directas de venta, pago y salida de flete ahora devuelven conflicto y exigen el flujo económico
- el ingreso de flete sigue tomando solo el servicio, no la garantía

## Auditoría

El módulo registra auditoría económica sobre:

- apertura de corte
- cierre de corte
- alta de egreso
- anulación de egreso
- devolución económica obligatoria

Evento explícito introducido en esta v1:

- `ECONOMY_REFUND_RECORDED`

## Migración y dependencias

Migración:

- `20260604_0010_economy_module.py`

Dependencia frontend nueva:

- `recharts`

## Validación ejecutada

Validación aplicada en esta implementación:

- `alembic upgrade head`
- `python scripts/seed_security.py`
- `pytest`
- `pnpm lint`
- `pnpm build`

Resultado:

- backend: `59 passed`
- frontend: `lint` OK
- frontend: `build` OK

## Regla que no debe romperse

La regla más importante del módulo es esta:

- una anulación operativa no borra un ingreso histórico
- una devolución real de dinero siempre debe vivir como egreso manual trazable

Esa separación mantiene consistencia contable, trazabilidad administrativa y flexibilidad para devoluciones parciales.
