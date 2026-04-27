# Modulo Boutique v1

## Objetivo

Esta entrega implementa el inventario base de boutique del sistema BellaArte, respetando la logica documental de `BASE_DE_DATOS.postgres` y conectandola con la arquitectura ya creada para seguridad.

El modulo cubre:

- catalogo de tipos boutique
- inventario boutique
- detalle especializado por tipo
- permisos por rol
- auditoria
- integracion frontend/backend

No cubre todavia:

- `VENTA_BOUTIQUE` en este documento de inventario
- ingresos automaticos
- recibos
- movimientos financieros del modulo

La implementacion de ventas directas ahora vive en un documento separado:

- `documentacion/MODULO_VENTAS_BOUTIQUE_V1.md`

## Modelo de datos implementado

### Tablas

- `TIPO_ITEM_BOUTIQUE`
- `ITEM_BOUTIQUE`
- `DETALLE_VESTIDO_BOUTIQUE`
- `DETALLE_VELO_BOUTIQUE`
- `DETALLE_BOUQUET_BOUTIQUE`

### Enums

- `TAMANO`
- `TIPO_VESTIDO`
- `COPA_TALLA_VESTIDO_BOUTIQUE`
- `TALLA_VESTIDO_BOUTIQUE`

### Seed inicial

- `VESTIDO`
- `VELO`
- `BOUQUET`
- `OTRO`

## Reglas de negocio

- el backend crea las tablas desde ORM + Alembic
- los nombres fisicos de Boutique se mantienen en mayuscula para respetar el SQL documental
- `TIPO_ITEM_BOUTIQUE.TIB_NOM` es unico
- `ITEM_BOUTIQUE.ITB_COD` es unico
- los valores monetarios y stock no aceptan negativos
- un item tiene cero o un detalle especializado
- `VESTIDO` requiere detalle de vestido
- `VELO` requiere detalle de velo
- `BOUQUET` requiere detalle de bouquet
- `OTRO` no admite detalle
- no se permite desactivar un tipo con items activos
- no se permite activar un item si su tipo esta deshabilitado
- el tipo del item no se cambia desde UI una vez creado
- el precio de venta no puede ser menor o igual al precio de compra

## Permisos

`ADMIN`:

- CRUD de tipos boutique
- CRUD de inventario boutique

`INV_BOUTIQUE`:

- CRUD de tipos boutique
- CRUD de inventario boutique

`CAJA`:

- lectura de tipos boutique
- lectura de inventario boutique

## API

### Tipos boutique

- `GET /api/v1/boutique/types`
- `GET /api/v1/boutique/types/{id}`
- `POST /api/v1/boutique/types`
- `PATCH /api/v1/boutique/types/{id}`
- `PATCH /api/v1/boutique/types/{id}/status`

### Inventario boutique

- `GET /api/v1/boutique/items`
- `GET /api/v1/boutique/items/{id}`
- `POST /api/v1/boutique/items`
- `PATCH /api/v1/boutique/items/{id}`
- `PATCH /api/v1/boutique/items/{id}/status`

### Filtros

- `type_id`
- `search`
- `is_active`
- `low_stock`

## Frontend

### Rutas

- `/app/boutique/tipos`
- `/app/boutique/inventario`

### Componentes principales

- `BoutiqueTypesPage`
- `BoutiqueInventoryPage`
- `BoutiqueTypeForm`
- `BoutiqueItemForm`
- `BoutiqueItemDetailCard`

### Comportamiento de UI

- drawer para crear y editar tipos
- drawer para crear y editar items
- drawer de visualizacion de detalle
- filtros de listado
- alerta visual de stock bajo
- formulario dinamico por tipo

## Auditoria

Eventos registrados:

- `BOUTIQUE_TYPE_CREATED`
- `BOUTIQUE_TYPE_UPDATED`
- `BOUTIQUE_TYPE_STATUS_CHANGED`
- `BOUTIQUE_ITEM_CREATED`
- `BOUTIQUE_ITEM_UPDATED`
- `BOUTIQUE_ITEM_STATUS_CHANGED`

## Flujo de trabajo recomendado para modulos siguientes

Si el siguiente submodulo boutique es `VENTA_BOUTIQUE`, la secuencia correcta debe ser:

1. leer `ITEM_BOUTIQUE`
2. validar estado activo
3. validar stock suficiente
4. registrar venta
5. descontar stock
6. generar ingreso automaticamente
7. generar recibo automaticamente
8. auditar la operacion

## Validacion realizada en esta entrega

- `pytest` backend pasando
- `alembic upgrade head` ejecutado correctamente
- seed ejecutado correctamente
- prueba real de lectura de tipos boutique
- prueba real de alta de tipo boutique
- prueba real de alta de item vestido
- prueba real de lectura restringida con rol `CAJA`
- `pnpm lint` frontend pasando
- `pnpm build` frontend pasando
