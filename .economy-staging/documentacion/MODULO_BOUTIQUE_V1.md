# Modulo Boutique

## Objetivo

Esta versión consolida el bloque Boutique ya refactorizado a nombres físicos en minúscula y lo deja listo para operar con proveedores, inventario especializado y ventas.

El módulo cubre:

- catálogo `tipo_item_boutique`
- catálogo `proveedor`
- inventario `item_boutique`
- detalles especializados:
  - `detalle_vestido_boutique`
  - `detalle_velo_boutique`
  - `detalle_bouquet_boutique`

## Modelo de datos implementado

### Tablas

- `tipo_item_boutique`
- `proveedor`
- `item_boutique`
- `detalle_vestido_boutique`
- `detalle_velo_boutique`
- `detalle_bouquet_boutique`

### Enums

- `tipo_vestido`
- `copa_talla_vestido_boutique`
- `talla_vestido_boutique`

### Seed inicial

- `VESTIDO`
- `VELO`
- `BOUQUET`
- `OTRO`

## Estructura de `item_boutique`

Campos relevantes:

- `tib_id`
- `pro_id`
- `itb_cod`
- `itb_nom`
- `itb_color_prim`
- `itb_color_secun`
- `itb_material`
- `itb_largo`
- `itb_ancho`
- `itb_precio_compra`
- `itb_precio_venta`
- `itb_stock`
- `itb_stock_min`
- `itb_detalle`
- `itb_estado`

## Reglas de negocio

- `tipo_item_boutique.tib_nom` es único
- `item_boutique.itb_cod` es único
- `itb_stock` e `itb_stock_min` son enteros y no negativos
- `itb_largo` e `itb_ancho` aceptan `null` o valores `>= 0`
- un item tiene cero o un detalle especializado
- `VESTIDO` exige detalle de vestido
- `VELO` exige detalle de velo
- `BOUQUET` exige detalle de bouquet
- `OTRO` no admite detalle especializado
- no se permite activar un item si su tipo está deshabilitado
- no se permite activar un item si su proveedor está deshabilitado
- no se permite desactivar un tipo con items activos asociados
- no se permite desactivar un proveedor con items activos asociados
- si un item ya tuvo ventas, el stock no se edita libremente desde este CRUD

## Permisos

`ADMIN`:

- CRUD de tipos boutique
- CRUD de proveedores
- CRUD de inventario boutique

`INV_BOUTIQUE`:

- CRUD de tipos boutique
- CRUD de proveedores
- CRUD de inventario boutique

`CAJA`:

- lectura de tipos
- lectura de proveedores
- lectura de inventario

## API

### Tipos boutique

- `GET /api/v1/boutique/types`
- `GET /api/v1/boutique/types/{id}`
- `POST /api/v1/boutique/types`
- `PATCH /api/v1/boutique/types/{id}`
- `PATCH /api/v1/boutique/types/{id}/status`

### Proveedores

- `GET /api/v1/boutique/proveedores`
- `GET /api/v1/boutique/proveedores/{id}`
- `POST /api/v1/boutique/proveedores`
- `PATCH /api/v1/boutique/proveedores/{id}`
- `PATCH /api/v1/boutique/proveedores/{id}/status`

### Inventario boutique

- `GET /api/v1/boutique/items`
- `GET /api/v1/boutique/items/{id}`
- `POST /api/v1/boutique/items`
- `PATCH /api/v1/boutique/items/{id}`
- `PATCH /api/v1/boutique/items/{id}/status`

Filtros:

- `type_id`
- `search`
- `is_active`
- `low_stock`

## Frontend

### Rutas

- `/app/boutique/tipos`
- `/app/boutique/proveedores`
- `/app/boutique/inventario`

### Contrato de formulario de item

Campos base:

- `code`
- `name`
- `color_primary`
- `color_secondary`
- `material`
- `length`
- `width`
- `provider_id`
- `purchase_price`
- `sale_price`
- `stock`
- `stock_min`
- `detail`

El detalle especializado cambia según `detail_kind`.

## Auditoría

- `BOUTIQUE_TYPE_CREATED`
- `BOUTIQUE_TYPE_UPDATED`
- `BOUTIQUE_TYPE_STATUS_CHANGED`
- `BOUTIQUE_PROVIDER_CREATED`
- `BOUTIQUE_PROVIDER_UPDATED`
- `BOUTIQUE_PROVIDER_STATUS_CHANGED`
- `BOUTIQUE_ITEM_CREATED`
- `BOUTIQUE_ITEM_UPDATED`
- `BOUTIQUE_ITEM_STATUS_CHANGED`

## Validación objetivo del módulo

- migración boutique crea todas las tablas en minúsculas
- seed de tipos boutique es idempotente
- proveedor no puede desactivarse con items activos
- item no puede crearse con proveedor deshabilitado
- el formulario frontend usa el contrato nuevo sin campos legacy
