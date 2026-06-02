# MÓDULO DE COMPROBANTES INTERNOS

## Resumen

El módulo `Comprobantes Internos` documenta automáticamente los ingresos reales de BellaArte Boutique sin convertirse en factura ni documento fiscal.

En esta v1:

- no existe alta manual de comprobantes
- no existe cambio manual de estado desde el módulo
- cada comprobante nace desde un único origen operativo
- la emisión ocurre en la misma transacción del movimiento económico
- si el origen se anula, el comprobante también se anula

Orígenes soportados:

- `venta_boutique`
- `pago_pedido`
- `salida_flete`

## Objetivo funcional

El comprobante interno sirve como:

- constancia comercial no fiscal
- respaldo administrativo y documental
- snapshot histórico del cliente al momento del cobro
- documento imprimible y exportable a PDF desde el navegador
- rastro consistente entre operación, usuario, moneda, tipo de cambio y detalle económico

## Tablas involucradas

### Catálogo

- `tipo_comprobante`

### Núcleo documental

- `comprobante_interno`
- `detalle_comprobante`

### Tablas origen

- `venta_boutique`
- `pago_pedido`
- `salida_flete`

### Relacionadas

- `cliente`
- `usuarios`
- `moneda`
- `tipo_cambio_moneda`
- `auditoria_sistema`

## Regla estructural principal

Cada `comprobante_interno` debe tener un solo origen operativo.

Se controla con:

- constraint `ck_comprobante_un_origen`
- índices únicos parciales por `veb_id`, `ppd_id`, `sfl_id`

Esto evita:

- doble emisión para una misma venta
- doble emisión para un mismo pago
- doble emisión para una misma salida de flete
- mezcla de múltiples operaciones dentro de un mismo comprobante

## Tipos de comprobante sembrados

El seed deja habilitados:

- `VENTA_BOUTIQUE_INTERNO`
- `PAGO_PEDIDO_INTERNO`
- `FLETE_INTERNO`

Todos nacen con:

- `tco_es_fiscal = false`
- `tco_hab = true`

## Catálogo administrable de tipos

El módulo ahora expone un submódulo operativo para `tipo_comprobante`.

Permite:

- listar tipos
- ver detalle
- crear nuevos tipos manuales
- editar descripción y naturaleza fiscal
- activar o desactivar tipos personalizados

Reglas especiales:

- los tipos base del sistema siguen visibles en el catálogo
- `VENTA_BOUTIQUE_INTERNO`
- `PAGO_PEDIDO_INTERNO`
- `FLETE_INTERNO`
- estos tipos no se pueden desactivar porque participan en la emisión automática
- su nombre técnico no debe alterarse

## Lógica de emisión automática

### 1. Venta Boutique

Se emite al crear una venta activa.

#### Mapeo principal

- `tco_id`: `VENTA_BOUTIQUE_INTERNO`
- `cli_id`: cliente de la venta o `NULL`
- `usu_id`: usuario que registró la venta
- `veb_id`: id de la venta
- `ppd_id`: `NULL`
- `sfl_id`: `NULL`
- `mon_id`: moneda usada en la venta
- `coi_cod`: prefijo `COI-VEB-`
- `coi_subtotal`: `veb_cant * veb_pre_uni`
- `coi_descuento`: `veb_descuento` o `0`
- `coi_total`: `veb_tot`
- `coi_total_moneda_orig`: total congelado en moneda origen
- `coi_saldo_posterior`: `0`
- `coi_garantia`: `0`
- `coi_tipo_cambio_usado`: tipo de cambio congelado de la venta
- `coi_metodo_pago`: método de pago de la venta
- `coi_estado`: `emitido`

#### Detalle

Siempre una línea:

- `dco_concepto`: `VENTA BOUTIQUE {ITB_COD} - {ITB_NOM}`
- `dco_cantidad`: cantidad vendida
- `dco_precio_unidad`: precio unitario
- `dco_descuento`: descuento aplicado
- `dco_subtotal`: total final de la línea

### 2. Pago de Pedido

Se emite al registrar cada pago válido de pedido.

#### Mapeo principal

- `tco_id`: `PAGO_PEDIDO_INTERNO`
- `cli_id`: cliente del pedido
- `usu_id`: usuario que registró el pago
- `veb_id`: `NULL`
- `ppd_id`: id del pago
- `sfl_id`: `NULL`
- `mon_id`: moneda del pago
- `coi_cod`: prefijo `COI-PPD-`
- `coi_subtotal`: `ppd_monto_bob`
- `coi_descuento`: `0`
- `coi_total`: `ppd_monto_bob`
- `coi_total_moneda_orig`: `ppd_monto`
- `coi_saldo_posterior`: saldo del pedido luego del pago
- `coi_garantia`: `0`
- `coi_tipo_cambio_usado`: tipo de cambio congelado del pago
- `coi_metodo_pago`: método de pago del pago
- `coi_estado`: `emitido`

#### Detalle

- `dco_concepto`: `PAGO DE PEDIDO {PED_COD}`
- `dco_cantidad`: `1`
- `dco_precio_unidad`: monto en Bs del pago
- `dco_descuento`: `0`
- `dco_subtotal`: monto en Bs del pago

### 3. Salida de Flete

Se emite al crear la salida de flete, porque allí ocurre el ingreso real del servicio.

#### Mapeo principal

- `tco_id`: `FLETE_INTERNO`
- `cli_id`: cliente del flete
- `usu_id`: usuario que registró la salida
- `veb_id`: `NULL`
- `ppd_id`: `NULL`
- `sfl_id`: id de la salida
- `mon_id`: moneda del cobro
- `coi_cod`: prefijo `COI-SFL-`
- `coi_subtotal`: `sfl_precio`
- `coi_descuento`: `sfl_descuento` o `0`
- `coi_total`: `sfl_total_flete`
- `coi_total_moneda_orig`: total del flete en moneda origen
- `coi_saldo_posterior`: `0`
- `coi_garantia`: `sfl_garantia`
- `coi_tipo_cambio_usado`: tipo de cambio congelado
- `coi_metodo_pago`: método de pago
- `coi_estado`: `emitido`

#### Detalle

- `dco_concepto`: `SERVICIO DE FLETE {ITB_COD} - {ITB_NOM}`
- `dco_cantidad`: `1`
- `dco_precio_unidad`: precio del servicio
- `dco_descuento`: descuento aplicado
- `dco_subtotal`: total final del servicio
- `dco_obs`: nota explícita de que la garantía no es ingreso real

## Snapshot documental del cliente

El comprobante congela:

- nombre
- CI/NIT
- celular

Reglas:

- si existe cliente y ya tiene los datos, se reutilizan
- si falta alguno, el frontend solicita completar solo lo faltante
- si el origen no tiene cliente ligado, el frontend exige registrar snapshot completo
- el snapshot no modifica automáticamente la tabla `cliente`

## Reglas de moneda

- los montos base viven en Bs
- la moneda de cobro puede ser otra
- el tipo de cambio usado se congela en el origen
- el comprobante muestra:
  - subtotal Bs
  - descuento Bs
  - total Bs
  - total en moneda origen
  - tipo de cambio usado
  - moneda de cobro

## Reglas de garantía en fletes

- `coi_garantia` se muestra documentalmente
- no forma parte del total comercial del servicio
- aparece separada del bloque de totales para evitar lecturas erróneas

## Estados

Estados vigentes:

- `emitido`
- `anulado`

### Emisión

Nace siempre en `emitido`.

### Anulación

No existe endpoint manual de anulación desde el módulo.

Se anula automáticamente cuando se anula el origen:

- venta boutique cancelada o anulada
- pago pedido anulado
- salida flete anulada

Al anular:

- cambia `coi_estado`
- guarda `coi_fec_camb_est`
- guarda `coi_motivo_camb_est`
- `coi_hab` pasa a `false`

## Backend implementado

### Modelos

- `app/models/receipt.py`

### Schemas

- `app/schemas/receipt.py`

### Servicio central

- `app/services/receipt_service.py`

Responsabilidades:

- resolver snapshot documental
- emitir comprobantes por origen
- evitar duplicados
- generar códigos únicos
- anular automáticamente
- listar historial
- devolver detalle
- construir HTML imprimible

### Integraciones

- `app/services/boutique_sale_service.py`
- `app/services/order_payment_service.py`
- `app/services/flete_service.py`

### Router

- `app/api/routers/receipts.py`

## Endpoints públicos

- `GET /api/v1/comprobantes/tipos`
- `GET /api/v1/comprobantes/tipos/{type_id}`
- `POST /api/v1/comprobantes/tipos`
- `PATCH /api/v1/comprobantes/tipos/{type_id}`
- `PATCH /api/v1/comprobantes/tipos/{type_id}/status`
- `GET /api/v1/comprobantes`
- `GET /api/v1/comprobantes/{receipt_id}`
- `GET /api/v1/comprobantes/{receipt_id}/printable`

No existen:

- `POST /api/v1/comprobantes`
- `PATCH /api/v1/comprobantes/{id}/status`

## Filtros del historial

- `search`
- `origin_type`
- `state`
- `currency_id`
- `payment_method`
- `client_id`
- `user_id`
- `date_from`
- `date_to`

## Permisos

Permisos nuevos:

- `receipt_types:list`
- `receipt_types:view`
- `receipt_types:create`
- `receipt_types:update`
- `receipt_types:update_status`
- `receipts:list`
- `receipts:view`
- `receipts:print`

Asignación inicial:

- `ADMIN`
- `CAJA`

Sin acceso por defecto:

- `MODISTA`
- `INV_BOUTIQUE`
- `INV_TALLER`

## Frontend implementado

### Ruta SPA

- `/app/comprobantes`
- `/app/comprobantes/tipos`

### Integración en menú

- `Comprobantes Internos`
- `Historial`
- `Tipos de Comprobante`

### Comportamiento

- listado histórico con filtros
- detalle con `GET` fresco
- watermark visible si está anulado
- acción `Ver`
- acción `Imprimir`
- acción `Ir al origen`
- catálogo visual de tipos de comprobante
- alta manual de tipos personalizados
- edición de descripción y naturaleza fiscal
- desactivación protegida para tipos base del sistema

### Formularios origen actualizados

Se añadió captura guiada de snapshot en:

- `Ventas Boutique`
- `Pagos de Pedidos`
- `Salidas de Flete`

Cuando faltan datos documentales:

- el formulario muestra alerta
- pide completar los campos faltantes
- todo se normaliza a MAYÚSCULAS

## Diseño del comprobante HTML

El documento imprimible incluye:

- logo
- nombre `BELLAARTE BOUTIQUE`
- título `COMPROBANTE INTERNO`
- subtítulo del tipo
- código
- fecha y hora
- datos del cliente
- usuario responsable
- origen operativo
- tabla de detalle
- subtotal
- descuento
- total en Bs
- total en moneda origen
- tipo de cambio
- método de pago
- saldo posterior si aplica
- garantía si aplica
- pie legal no fiscal

Salida:

- vista previa HTML
- impresión por navegador
- guardado en PDF desde `window.print()`

## Seguridad y control

- sin creación manual
- sin anulación manual directa
- sin edición de montos del comprobante
- sin mezcla de múltiples orígenes
- sin doble emisión por origen
- todo dentro de transacción
- trazabilidad por auditoría del origen
- control de concurrencia en generación de código

## Migración correctiva aplicada

- `20260525_0008_internal_receipts_module.py`

Agrega:

- FK real de `ppd_id` hacia `pago_pedido`
- índices operativos de búsqueda
- índices únicos parciales por origen

## Validación realizada

- `alembic upgrade head`
- `pytest`
- `pnpm lint`
- `pnpm build`

## Diferencias por origen

### Venta Boutique

- puede tener descuento
- no tiene saldo posterior
- no tiene garantía
- representa la venta final del producto

### Pago Pedido

- no maneja descuento documental propio
- sí muestra saldo posterior
- representa un cobro parcial o final

### Salida Flete

- puede tener descuento
- no tiene saldo posterior
- sí muestra garantía separada
- representa ingreso por servicio, no por venta de producto
