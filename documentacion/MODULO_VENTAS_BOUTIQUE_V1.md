# Modulo Ventas Boutique v1

## Objetivo

Esta entrega implementa el submodulo `VENTA_BOUTIQUE` para registrar ventas directas de productos de la boutique, respetando el SQL documental, la arquitectura vigente del sistema y los lineamientos de UI/UX ya definidos para formularios y CRUD.

## Modelo de datos implementado

### Enums

- `METODO_PAGO`
- `MOTIVO_DESC_VENTA_BOUTIQUE`
- `ESTADO_VENTA_BOUTIQUE`

### Tabla

- `VENTA_BOUTIQUE`

### Columnas fisicas respetadas

- `VEB_ID`
- `ITB_ID`
- `USU_ID`
- `CLI_ID`
- `VEB_FEC`
- `VEB_CANT`
- `VEB_PRE_UNI`
- `VEB_DESCUENTO`
- `VEB_MOTIVO_DESC`
- `VEB_TOT`
- `VEB_METODO_PAGO`
- `VEB_OBS`
- `VEB_ESTADO`

## Reglas de negocio

- `VEB_TOT` se calcula desde la BD
- el precio unitario se toma automaticamente desde `ITEM_BOUTIQUE.ITB_PRECIO_VENTA`
- no se permite editar una venta despues de crearla
- `ACTIVA` es el unico estado inicial permitido
- `CANCELADA` y `ANULADA` revierten stock y no cuentan como ingreso real
- no se permite vender un item inactivo
- no se permite vender un item cuyo tipo boutique este inactivo
- no se permite vender sin stock suficiente
- si hay descuento, el motivo es obligatorio
- si no hay descuento, el motivo debe quedar nulo
- `MIXTO` existe en enum pero queda bloqueado hasta tener una estructura de desglose real
- el cliente es opcional
- `USU_ID` conserva nombre documental, pero referencia a la tabla real `usuarios`

## API

- `GET /api/v1/boutique/sales`
- `GET /api/v1/boutique/sales/{id}`
- `POST /api/v1/boutique/sales`
- `PATCH /api/v1/boutique/sales/{id}/cancel`
- `PATCH /api/v1/boutique/sales/{id}/annul`

### Filtros

- `search`
- `item_id`
- `client_id`
- `payment_method`
- `state`
- `date_from`
- `date_to`

## Permisos

`ADMIN`:

- listar ventas boutique
- ver detalle de venta
- registrar venta
- cancelar venta
- anular venta

`CAJA`:

- listar ventas boutique
- ver detalle de venta
- registrar venta
- cancelar venta
- anular venta
- lectura de clientes como referencia de venta

`INV_BOUTIQUE`:

- listar ventas boutique
- ver detalle de venta

## Frontend

### Ruta

- `/app/boutique/ventas`

### Componentes principales

- `BoutiqueSalesPage`
- `BoutiqueSaleForm`
- `BoutiqueSaleDetailCard`

### Comportamiento de UI

- tabla historica con filtros
- drawer para nueva venta
- modal de detalle con consulta fresca al backend
- modal de cancelacion o anulacion con motivo operativo obligatorio
- resumen de subtotal, descuento y total en tiempo real
- selector de producto con stock y precio visible
- selector opcional de cliente
- metodo de pago sin opcion operativa `MIXTO`

## Auditoria

Eventos registrados:

- `BOUTIQUE_SALE_CREATED`
- `BOUTIQUE_SALE_CANCELLED`
- `BOUTIQUE_SALE_ANNULLED`

## Validacion realizada

- `pytest` backend pasando
- `alembic upgrade head` ejecutado correctamente
- smoke test real de venta con rol `CAJA`
- smoke test real de lectura con rol `INV_BOUTIQUE`
- smoke test real de cancelacion y anulacion con reversión de stock
- `pnpm lint` frontend pasando
- `pnpm build` frontend pasando
