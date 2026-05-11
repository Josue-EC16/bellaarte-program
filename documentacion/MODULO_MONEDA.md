# Modulo Moneda

## Objetivo

Documentar el catálogo `moneda` introducido para operar ventas boutique con moneda base y monedas adicionales.

## Tabla implementada

- `moneda`

## Columnas clave

- `mon_id`
- `mon_cod`
- `mon_nom`
- `mon_simbolo`
- `mon_es_base`
- `mon_hab`
- `mon_fec_reg`

## Reglas de negocio

- `mon_cod` es único
- solo puede existir una moneda base activa
- la moneda base no puede quedar deshabilitada
- el seed crea `BOB` como base activa

## API

- `GET /api/v1/monedas`
- `GET /api/v1/monedas/{id}`
- `POST /api/v1/monedas`
- `PATCH /api/v1/monedas/{id}`
- `PATCH /api/v1/monedas/{id}/status`

## Permisos

`ADMIN`:

- CRUD completo

`CAJA` e `INV_BOUTIQUE`:

- lectura

## Frontend

Ruta:

- `/app/monedas`

## Auditoría

- `CURRENCY_CREATED`
- `CURRENCY_UPDATED`
- `CURRENCY_STATUS_CHANGED`
