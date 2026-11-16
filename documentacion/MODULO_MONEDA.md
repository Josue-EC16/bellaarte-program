# Modulo Moneda

**TC-02 activa, 04/11/2026:** solo USD/BOB se consulta automáticamente mediante
factura.bo; el resto permanece manual. Estado y registros técnicos forman parte
de Monedas, con registros exclusivos ADMIN. La estructura del catálogo sigue
intacta. Ver [operación y tarea Windows](SPEC_TC_02_IMPLEMENTACION.md).

Actualización 04/11/2026: SPEC-TC-01 conserva intacta la estructura de `moneda`.
BOB conserva código/base y referencia 1. No se permite cambiar código/base de una
moneda que tenga cotizaciones o intentos automáticos. Los cambios y desactivación
de moneda comparten bloqueo de fila con el alta de tasas. Ver
[tipos de cambio](MODULO_TIPO_CAMBIO_MONEDA.md).

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
