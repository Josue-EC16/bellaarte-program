# Modulo Cliente

## Objetivo

Esta versión implementa el CRUD de `cliente` ya normalizado a minúsculas y alineado con el bloque comercial actual.

## Tabla implementada

- `cliente`

## Columnas clave

- `cli_id`
- `cli_cod`
- `cli_nom`
- `cli_ape_pat`
- `cli_ape_mat`
- `cli_cel`
- `cli_cel_ref`
- `cli_nom_cel_ref`
- `cli_cor`
- `cli_ci`
- `cli_fecha_nac`
- `cli_pais`
- `cli_ciudad`
- `cli_zona`
- `cli_calle`
- `cli_obs`
- `cli_hab`
- `cli_fec_reg`

## Reglas de negocio

- `cli_cod` es único
- si no se envía `cli_cod`, backend lo genera con patrón `CLI-00001`
- si se envía `cli_cod`, debe respetar ese mismo formato
- `cli_nom`, `cli_ape_pat` y `cli_cel` son obligatorios
- `cli_cor` y `cli_ci` son únicos cuando existen
- `cli_fecha_nac` es opcional
- nombres, país, ciudad, zona, calle y observaciones se normalizan en mayúsculas
- correo se normaliza en minúsculas
- el estado es lógico mediante `cli_hab`

## API

- `GET /api/v1/clientes`
- `GET /api/v1/clientes/{id}`
- `POST /api/v1/clientes`
- `PATCH /api/v1/clientes/{id}`
- `PATCH /api/v1/clientes/{id}/status`

Filtros:

- `search`
- `is_active`

La búsqueda contempla:

- código
- nombres
- apellidos
- celular
- CI
- ciudad

## Permisos

`ADMIN`:

- CRUD completo

`MODISTA`:

- CRUD completo

`CAJA`:

- lectura técnica para referencia en ventas boutique

## Frontend

### Ruta

- `/app/clientes`

### Campos visibles principales

- código
- nombres
- apellidos
- celular
- celular de referencia
- nombre de referencia
- correo
- CI
- fecha de nacimiento
- país
- ciudad
- zona
- calle
- observaciones

## Auditoría

- `CLIENT_CREATED`
- `CLIENT_UPDATED`
- `CLIENT_STATUS_CHANGED`

## Validación objetivo del módulo

- autogeneración de `cli_cod`
- edición manual válida de `cli_cod`
- unicidad de correo y CI
- acceso completo para `MODISTA`
