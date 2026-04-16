# Modulo Cliente v1

## Objetivo

Esta entrega implementa el registro y CRUD del modulo `CLIENTE`, alineado al SQL documental y a la arquitectura ya usada en Boutique.

## Tabla implementada

- `CLIENTE`

## Columnas fisicas respetadas

- `CLI_ID`
- `CLI_COD`
- `CLI_NOM`
- `CLI_APE_PAT`
- `CLI_APE_MAT`
- `CLI_CEL`
- `CLI_CEL_REF`
- `CLI_NOM_CEL_REF`
- `CLI_COR`
- `CLI_CI`
- `CLI_NAC`
- `CLI_ZONA`
- `CLI_CALLE`
- `CLI_OBS`
- `CLI_HAB`
- `CLI_FEC_REG`

## Reglas de negocio

- `CLI_COD` es unico
- si no se envia `CLI_COD`, el backend genera uno automatico
- si se envia `CLI_COD`, debe seguir el formato `CLI-00001`
- `CLI_NOM`, `CLI_APE_PAT` y `CLI_CEL` son obligatorios
- el estado del cliente es logico mediante `CLI_HAB`
- nombres, apellidos, zona, calle, nacionalidad y observaciones se normalizan en mayusculas
- correo se normaliza en minusculas

## API

- `GET /api/v1/clientes`
- `GET /api/v1/clientes/{id}`
- `POST /api/v1/clientes`
- `PATCH /api/v1/clientes/{id}`
- `PATCH /api/v1/clientes/{id}/status`

## Filtros

- `search`
- `is_active`

La busqueda contempla:

- codigo
- nombres
- apellidos
- CI
- celular

## Permisos

`ADMIN`:

- CRUD completo

`MODISTA`:

- CRUD completo

## Frontend

### Ruta

- `/app/clientes`

### Comportamiento

- tabla con filtros
- drawer de alta y edicion
- activacion y desactivacion logica
- campo de codigo editable
- soporte para autogeneracion backend

## Auditoria

Eventos registrados:

- `CLIENT_CREATED`
- `CLIENT_UPDATED`
- `CLIENT_STATUS_CHANGED`

## Validacion realizada

- migracion aplicada correctamente
- smoke test real de alta de cliente
- smoke test real de acceso permitido para `MODISTA`
- smoke test real de acceso denegado a roles para `MODISTA`
