# Modulo Tipo Cambio Moneda

## Objetivo

Documentar `tipo_cambio_moneda`, usado para congelar el valor de conversión en ventas boutique.

## Tabla implementada

- `tipo_cambio_moneda`

## Columnas clave

- `tcm_id`
- `mon_id`
- `usu_id`
- `tcm_valor_bob`
- `tcm_fec_reg`
- `tcm_obs`
- `tcm_activo`

## Reglas de negocio

- `tcm_valor_bob > 0`
- solo puede existir un tipo de cambio activo por moneda
- si se crea uno nuevo activo, el anterior activo se desactiva
- para la moneda base, el valor activo debe ser `1`
- no se pueden activar tipos de cambio sobre monedas deshabilitadas

## API

- `GET /api/v1/monedas/tipos-cambio`
- `GET /api/v1/monedas/tipos-cambio/{id}`
- `POST /api/v1/monedas/tipos-cambio`
- `PATCH /api/v1/monedas/tipos-cambio/{id}`
- `PATCH /api/v1/monedas/tipos-cambio/{id}/status`

## Permisos

`ADMIN`:

- CRUD completo

`CAJA` e `INV_BOUTIQUE`:

- lectura

## Frontend

Ruta:

- `/app/monedas/tipos-cambio`

## Auditoría

- `EXCHANGE_RATE_CREATED`
- `EXCHANGE_RATE_UPDATED`
- `EXCHANGE_RATE_STATUS_CHANGED`
