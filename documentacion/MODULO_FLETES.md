# Módulo Fletes

## 1. Objetivo

El módulo `Fletes` permite tomar vestidos ya registrados en `item_boutique`, habilitarlos para modalidad de alquiler y controlar todo su ciclo operativo:

- habilitación a flete
- reserva de salida
- entrega física
- devolución
- devolución con observación
- devolución con arreglo
- anulación
- resolución de revisión
- pase a venta como vestido usado
- retiro definitivo

El módulo también deja trazabilidad económica mínima mediante:

- `comprobante_interno`
- `detalle_comprobante`

## 2. Alcance implementado

La versión actual incluye:

- CRUD operativo de `flete_vestido`
- ciclo completo de `salida_flete`
- control de garantía
- control de descuento y motivo
- control de moneda y tipo de cambio congelado
- generación automática de comprobante interno por salida
- anulación automática del comprobante cuando se anula la salida
- auditoría de acciones críticas
- frontend operativo con rutas, menú, drawers, modales y validación visual

## 3. Tablas que interactúan

### Principales

- `flete_vestido`
- `salida_flete`

### Relacionadas por FK o lógica operativa

- `item_boutique`
- `detalle_vestido_boutique`
- `cliente`
- `usuarios`
- `moneda`
- `tipo_cambio_moneda`
- `tipo_comprobante`
- `comprobante_interno`
- `detalle_comprobante`
- `auditoria_sistema`

## 4. Modelo de datos implementado

### `flete_vestido`

Representa la habilitación de un vestido boutique al circuito de flete.

Campos clave:

- `fle_id`
- `itb_id`
- `usu_id`
- `fle_precio_flete_ref`
- `fle_max_salidas`
- `fle_salidas_actuales`
- `fle_estado`
- `fle_fec_hab_flete`
- `fle_obs`
- `fle_hab`

Relaciones:

- `itb_id -> item_boutique.itb_id`
- `usu_id -> usuarios.id`

Reglas técnicas:

- `itb_id` es único
- `fle_max_salidas` entre `1` y `4`
- `fle_salidas_actuales >= 0`
- `fle_salidas_actuales <= fle_max_salidas`
- `fle_precio_flete_ref > 0`

### `salida_flete`

Representa cada operación individual de alquiler.

Campos clave:

- `sfl_id`
- `fle_id`
- `cli_id`
- `usu_id`
- `mon_id`
- `sfl_num`
- `sfl_fec_salida`
- `sfl_fec_devolucion_prevista`
- `sfl_fec_devolucion_real`
- `sfl_precio`
- `sfl_descuento`
- `sfl_motivo_desc`
- `sfl_metodo_pago`
- `sfl_tipo_cambio_usado`
- `sfl_total_flete`
- `sfl_total_flete_moneda_orig`
- `sfl_garantia`
- `sfl_garantia_devuelta`
- `sfl_estado_salida`
- `sfl_fec_camb_est`
- `sfl_motivo_camb_est`
- `sfl_estado_entrega`
- `sfl_estado_devolucion`
- `sfl_requiere_arreglo`
- `sfl_monto_arreglo`
- `sfl_descripcion_arreglo`
- `sfl_obs_entrega`
- `sfl_obs_devolucion`
- `sfl_hab`

Relaciones:

- `fle_id -> flete_vestido.fle_id`
- `cli_id -> cliente.cli_id`
- `usu_id -> usuarios.id`
- `mon_id -> moneda.mon_id`

Reglas técnicas importantes:

- `sfl_num` es único por `fle_id`
- `sfl_num` entre `1` y `4`
- `sfl_precio > 0`
- `sfl_descuento <= sfl_precio`
- `sfl_total_flete` se calcula en base de datos
- `sfl_total_flete_moneda_orig > 0`
- `sfl_tipo_cambio_usado > 0`
- `sfl_garantia_devuelta <= sfl_garantia`
- `sfl_fec_devolucion_prevista >= sfl_fec_salida`
- si hay descuento, debe existir motivo
- si hay arreglo, debe existir descripción

### `tipo_comprobante`

Catálogo mínimo implementado para soportar Fletes.

Seed actual:

- `FLETE_INTERNO`

### `comprobante_interno`

Comprobante no fiscal generado automáticamente cuando se registra una salida de flete.

Origen implementado en esta fase:

- `sfl_id`

Campos más importantes:

- `coi_cod`
- `coi_subtotal`
- `coi_descuento`
- `coi_total`
- `coi_total_moneda_orig`
- `coi_garantia`
- `coi_tipo_cambio_usado`
- `coi_metodo_pago`
- `coi_estado`

### `detalle_comprobante`

Detalle mínimo con un solo concepto:

- servicio de flete del vestido

## 5. Enums usados

### `estado_flete`

- `disponible`
- `en_flete`
- `en_revision`
- `agotado`
- `pasado_para_venta`
- `retirado`

### `motivo_desc_flete`

- `rebaja`
- `promocion`
- `bonificacion`
- `administrativo`

### `estado_salida_flete`

- `reservado`
- `en_flete`
- `devuelto`
- `devuelto_con_observacion`
- `devuelto_con_arreglo`
- `anulado`

### `estado_flete_entrega`

- `bueno`
- `regular`
- `con_observacion`

### `estado_flete_devolucion`

- `bueno`
- `regular`
- `dañado`
- `incompleto`

### Reutilizados

- `metodo_pago`
- `estado_comprobante`

## 6. Lógica de negocio implementada

### 6.1 Habilitar vestido para flete

Condiciones:

- el producto debe existir en `item_boutique`
- debe estar activo
- debe tener stock `> 0`
- debe ser un item boutique de tipo `VESTIDO`
- debe tener `detalle_vestido_boutique`
- no debe existir ya un registro previo en `flete_vestido`

Efecto:

1. se crea `flete_vestido`
2. se descuenta `1` unidad de `item_boutique.itb_stock`
3. se registra auditoría

### 6.2 Crear salida de flete

Condiciones:

- el flete debe estar habilitado
- no debe tener una salida activa bloqueante
- no debe superar `fle_max_salidas`
- `sfl_num` se calcula secuencialmente
- cliente obligatorio y activo
- moneda obligatoria y activa
- si la moneda no es base, debe existir tipo de cambio activo
- descuento y motivo deben ser coherentes

Efecto:

1. la salida nace en `reservado`
2. se congela el tipo de cambio usado
3. se calcula `sfl_total_flete_moneda_orig`
4. se crea `comprobante_interno`
5. se crea `detalle_comprobante`
6. se registra auditoría

### 6.3 Entregar salida

Condiciones:

- la salida debe estar en `reservado`

Efecto:

1. la salida pasa a `en_flete`
2. `flete_vestido` pasa a `en_flete`
3. se registra auditoría

### 6.4 Devolver salida

Condiciones:

- la salida debe estar en `en_flete`
- la fecha real de devolución no puede ser anterior a la salida
- la garantía devuelta no puede superar la garantía recibida

Estados posibles al devolver:

- `devuelto`
- `devuelto_con_observacion`
- `devuelto_con_arreglo`

Efecto:

- siempre incrementa `fle_salidas_actuales`
- si el resultado es `devuelto`:
  - vuelve a `disponible` si no llegó al máximo
  - pasa a `agotado` si alcanzó el máximo
- si el resultado es con observación o arreglo:
  - `flete_vestido` pasa a `en_revision`

### 6.5 Anular salida

Condiciones:

- solo si la salida no está ya anulada
- exige motivo operativo

Efecto:

1. la salida pasa a `anulado`
2. guarda fecha y motivo de cambio
3. si ya había contado como válida, revierte `fle_salidas_actuales`
4. anula el `comprobante_interno`
5. recalcula el estado de `flete_vestido`
6. registra auditoría

### 6.6 Resolver revisión

Disponible cuando `flete_vestido` está en `en_revision`.

Resoluciones implementadas:

- volver a `disponible`
- pasar a `agotado`

### 6.7 Pasar vestido usado a venta

Condiciones:

- el flete no puede tener salida activa o reservada
- debe tener al menos una salida válida acumulada
- exige nuevo precio de venta

Efecto:

1. se crea un nuevo `item_boutique`
2. se copian datos base del vestido original
3. se duplica también `detalle_vestido_boutique`
4. el nuevo item nace con stock `1`
5. el código se genera con patrón derivado: `CODIGO-USADO-01`, `-02`, etc.
6. el nuevo item se marca como usado en nombre/detalle
7. el flete pasa a `pasado_para_venta`
8. se registra auditoría

### 6.8 Retirar vestido del circuito

Condiciones:

- no puede tener salida activa o reservada

Efecto:

- si no tuvo salidas válidas:
  - devuelve `1` unidad al stock del item original
- si ya tuvo salidas válidas:
  - no devuelve stock al item original
- el flete pasa a `retirado`
- queda inhabilitado

## 7. Reglas de garantía

- `sfl_garantia` se registra como respaldo
- `sfl_garantia_devuelta <= sfl_garantia`
- la garantía no suma al ingreso real del comprobante
- el comprobante conserva la garantía solo como dato documental

## 8. Reglas de moneda

- `sfl_precio` y `sfl_total_flete` están en Bs
- si la moneda es base:
  - `sfl_tipo_cambio_usado = 1`
  - `sfl_total_flete_moneda_orig = sfl_total_flete`
- si la moneda no es base:
  - se usa el tipo de cambio activo vigente
  - se congela en la salida

## 9. Conteo de salidas válidas

`fle_salidas_actuales` cuenta solamente:

- `devuelto`
- `devuelto_con_observacion`
- `devuelto_con_arreglo`

No cuenta:

- `reservado`
- `en_flete`
- `anulado`

## 10. Transacciones críticas implementadas

Se ejecutan como transacción lógica única:

- habilitar vestido para flete
- registrar salida de flete
- registrar devolución
- anular salida
- pasar a venta
- retirar

## 11. Permisos por rol

### `ADMIN`

Permisos completos:

- `fletes:*`
- `flete_outputs:*`

### `CAJA`

Permisos completos del módulo en esta v1:

- `fletes:list`
- `fletes:view`
- `fletes:create`
- `fletes:update`
- `fletes:disable`
- `fletes:resolve_review`
- `fletes:pass_to_sale`
- `fletes:retire`
- `flete_outputs:list`
- `flete_outputs:view`
- `flete_outputs:create`
- `flete_outputs:deliver`
- `flete_outputs:return`
- `flete_outputs:annul`

### Otros roles

- sin acceso operativo al módulo

## 12. Endpoints implementados

### Fletes

- `GET /api/v1/fletes`
- `GET /api/v1/fletes/eligible-items`
- `GET /api/v1/fletes/{id}`
- `POST /api/v1/fletes`
- `PATCH /api/v1/fletes/{id}`
- `PATCH /api/v1/fletes/{id}/disable`
- `PATCH /api/v1/fletes/{id}/resolve-review`
- `PATCH /api/v1/fletes/{id}/pass-to-sale`
- `PATCH /api/v1/fletes/{id}/retire`

### Salidas de flete

- `GET /api/v1/fletes/salidas`
- `GET /api/v1/fletes/salidas/{id}`
- `POST /api/v1/fletes/salidas`
- `PATCH /api/v1/fletes/salidas/{id}/deliver`
- `PATCH /api/v1/fletes/salidas/{id}/return`
- `PATCH /api/v1/fletes/salidas/{id}/annul`

## 13. Frontend implementado

### Rutas SPA

- `/app/fletes`
- `/app/fletes/salidas`

### Páginas

- `frontend/src/pages/fletes/FletesPage.jsx`
- `frontend/src/pages/fletes/FleteOutputsPage.jsx`
- `frontend/src/pages/fletes/fleteConstants.js`

### UX aplicada

- listado principal con filtros
- drawers de alta y edición
- modales de acciones críticas
- `maskClosable={false}`
- detalle cargado siempre con `GET` fresco
- resumen visual de moneda, garantía y total
- flujo específico para devolución y para pase a venta

## 14. Auditoría implementada

- `FLETE_CREATED`
- `FLETE_UPDATED`
- `FLETE_STATUS_CHANGED`
- `FLETE_PASSED_TO_SALE`
- `FLETE_RETIRED`
- `FLETE_OUTPUT_CREATED`
- `FLETE_OUTPUT_DELIVERED`
- `FLETE_OUTPUT_RETURNED`
- `FLETE_OUTPUT_ANNULLED`
- `FLETE_RECEIPT_CREATED`
- `FLETE_RECEIPT_ANNULLED`

## 15. Consideraciones y límites actuales

- el módulo solo acepta items boutique de tipo `VESTIDO`
- `comprobante_interno` se implementó con soporte operativo real para `sfl_id`
- la columna `ppd_id` quedó reservada para futura integración con `pago_pedido`
- no existe todavía un CRUD independiente de comprobantes
- la garantía se controla, pero no genera ingreso real automático
- no se implementan todavía notificaciones automáticas de vencimiento o devolución

## 16. Validación realizada

Se validó la entrega con:

- `pytest`
- `alembic upgrade head`
- `python scripts/seed_security.py`
- `pnpm lint`
- `pnpm build`

Smoke funcional esperado para continuar:

1. habilitar un vestido para flete
2. registrar salida reservada
3. entregar
4. devolver normal
5. devolver con observación
6. devolver con arreglo
7. anular
8. pasar a venta
9. retirar sin salidas
