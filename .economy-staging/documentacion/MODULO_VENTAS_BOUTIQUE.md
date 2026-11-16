# Modulo Ventas Boutique

## Objetivo

Esta versión implementa `venta_boutique` sobre el nuevo bloque boutique normalizado, incorporando moneda, tipo de cambio congelado y reversión de stock.

## Modelo de datos implementado

### Enums

- `metodo_pago`
- `motivo_desc_venta_boutique`
- `estado_venta_boutique`

### Tablas relacionadas

- `venta_boutique`
- `item_boutique`
- `cliente`
- `moneda`
- `tipo_cambio_moneda`
- `usuarios`

### Columnas clave de `venta_boutique`

- `veb_id`
- `itb_id`
- `usu_id`
- `cli_id`
- `mon_id`
- `veb_fec`
- `veb_cant`
- `veb_pre_uni`
- `veb_descuento`
- `veb_motivo_desc`
- `veb_tot`
- `veb_tipo_cambio_usado`
- `veb_total_moneda_orig`
- `veb_metodo_pago`
- `veb_obs`
- `veb_estado`
- `veb_fec_camb_est`
- `veb_motivo_camb_est`

## Reglas de negocio

- `veb_pre_uni` se toma automáticamente de `item_boutique.itb_precio_venta`
- `veb_cant` es entero y debe ser mayor a cero
- `veb_tot` se calcula en base de datos
- `veb_descuento` no puede ser mayor al subtotal
- si hay descuento, `veb_motivo_desc` es obligatorio
- si no hay descuento, `veb_motivo_desc` debe quedar nulo
- si la moneda es base, `veb_tipo_cambio_usado = 1`
- si la moneda no es base, se usa el tipo de cambio activo vigente
- `veb_total_moneda_orig` se calcula y queda congelado en la venta
- no se vende stock insuficiente
- no se vende un item inactivo o con tipo deshabilitado
- el cliente es opcional, pero si se envía debe estar habilitado
- la venta no se edita después de creada
- solo se permite `activa -> cancelada` o `activa -> anulada`
- cancelar o anular devuelve stock exactamente una vez
- al revertir se registra fecha y motivo de cambio de estado

## API

- `GET /api/v1/boutique/sales`
- `GET /api/v1/boutique/sales/{id}`
- `POST /api/v1/boutique/sales`
- `PATCH /api/v1/boutique/sales/{id}/cancel`
- `PATCH /api/v1/boutique/sales/{id}/annul`

Filtros:

- `search`
- `item_id`
- `client_id`
- `currency_id`
- `payment_method`
- `state`
- `date_from`
- `date_to`

## Permisos

`ADMIN`:

- listar
- ver
- crear
- cancelar
- anular

`CAJA`:

- listar
- ver
- crear
- cancelar
- anular

`INV_BOUTIQUE`:

- listar
- ver

## Frontend

### Ruta

- `/app/boutique/ventas`

### Comportamiento

- filtro por producto, cliente, moneda, método, estado y fechas
- drawer de nueva venta con `maskClosable={false}`
- resumen en tiempo real:
  - subtotal en Bs
  - descuento
  - total en Bs
  - total en moneda origen
- si la moneda no tiene tipo de cambio activo, la venta se bloquea
- el detalle se consulta siempre con `GET` fresco
- cancelar y anular exigen motivo operativo

## Auditoría

- `BOUTIQUE_SALE_CREATED`
- `BOUTIQUE_SALE_CANCELLED`
- `BOUTIQUE_SALE_ANNULLED`

## Validación objetivo del módulo

- venta con `BOB` usa tipo de cambio `1`
- venta con moneda no base toma el tipo de cambio activo
- cancelación y anulación restauran stock
- `CAJA` puede vender y `INV_BOUTIQUE` solo leer
