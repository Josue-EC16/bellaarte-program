# Modulo Proveedor

## Objetivo

Documentar el catálogo `proveedor` incorporado al refactor boutique.

## Tabla implementada

- `proveedor`

## Columnas clave

- `pro_id`
- `pro_nom`
- `pro_ape_pat`
- `pro_ape_mat`
- `pro_nom_comercial`
- `pro_cel`
- `pro_cel_sec`
- `pro_cor`
- `pro_pais`
- `pro_ciudad`
- `pro_dir`
- `pro_obs`
- `pro_hab`
- `pro_fec_reg`

## Reglas de negocio

- `pro_cel` y `pro_cor` son únicos cuando existen
- los textos de negocio se normalizan en mayúsculas
- el correo se normaliza en minúsculas
- no se puede desactivar un proveedor con items activos asociados

## API

- `GET /api/v1/boutique/proveedores`
- `GET /api/v1/boutique/proveedores/{id}`
- `POST /api/v1/boutique/proveedores`
- `PATCH /api/v1/boutique/proveedores/{id}`
- `PATCH /api/v1/boutique/proveedores/{id}/status`

## Permisos

`ADMIN` e `INV_BOUTIQUE`:

- CRUD completo

`CAJA`:

- lectura

## Frontend

Ruta:

- `/app/boutique/proveedores`

## Auditoría

- `BOUTIQUE_PROVIDER_CREATED`
- `BOUTIQUE_PROVIDER_UPDATED`
- `BOUTIQUE_PROVIDER_STATUS_CHANGED`
