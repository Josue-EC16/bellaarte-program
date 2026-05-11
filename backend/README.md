# Backend BellaArte

Backend del sistema `bellaarte-program`, construido con FastAPI, SQLAlchemy, Alembic, JWT y Casbin.

La version actual ya consolida:

- seguridad interna con login, refresh, roles, cuentas y auditoria
- CRUD operativo de usuarios y roles
- CRUD de `cliente`
- CRUD de `tipo_item_boutique`, `proveedor`, `item_boutique` y sus detalles
- CRUD de `moneda` y `tipo_cambio_moneda`
- ventas directas de `venta_boutique` con descuento de stock y reversión

## Stack

- Python
- FastAPI
- SQLAlchemy 2
- Alembic
- PostgreSQL
- Passlib + Bcrypt
- Python-JOSE
- Casbin
- Pytest

## Estado actual de base de datos

Tablas de seguridad:

- `roles`
- `usuarios`
- `cuentas`
- `auditoria_sistema`

Tablas comerciales y boutique refactorizadas en minúscula:

- `cliente`
- `proveedor`
- `moneda`
- `tipo_cambio_moneda`
- `tipo_item_boutique`
- `item_boutique`
- `detalle_vestido_boutique`
- `detalle_velo_boutique`
- `detalle_bouquet_boutique`
- `venta_boutique`

## Variables de entorno

Crear `.env` en `backend/` a partir de `.env.example`.

Variables principales:

- `DATABASE_URL`
- `DB_HOST`
- `DB_NAME`
- `DB_USER`
- `DB_PASS`
- `DB_PORT`
- `JWT_SECRET_KEY`
- `JWT_REFRESH_SECRET_KEY`
- `ACCESS_TOKEN_MINUTES`
- `REFRESH_TOKEN_DAYS`
- `FRONTEND_URL`
- `ENVIRONMENT`
- `BOOTSTRAP_ADMIN_USERNAME`
- `BOOTSTRAP_ADMIN_PASSWORD`
- `BOOTSTRAP_ADMIN_EMAIL`
- `BOOTSTRAP_ADMIN_NAMES`
- `BOOTSTRAP_ADMIN_LAST_NAME`
- `BOOTSTRAP_ADMIN_MOTHER_LAST_NAME`
- `BOOTSTRAP_ADMIN_CI`
- `BOOTSTRAP_ADMIN_CELLPHONE`
- `BOOTSTRAP_ADMIN_ZONE`
- `BOOTSTRAP_ADMIN_ADDRESS`

Regla:

- si existe `DATABASE_URL`, esa es la fuente principal
- si no existe, la conexión se arma con `DB_*`

## Comandos

Instalar dependencias:

```powershell
cd backend
.\venv\Scripts\activate
pip install -r requirements.txt
```

Levantar API:

```powershell
uvicorn main:app --reload
```

Aplicar migraciones:

```powershell
python -m alembic -c alembic.ini upgrade head
```

Ejecutar seed base:

```powershell
python scripts/seed_security.py
```

Ejecutar pruebas:

```powershell
pytest
```

## Estructura oficial

```text
backend/
├─ app/
│  ├─ api/
│  │  ├─ routers/
│  │  └─ router.py
│  ├─ core/
│  ├─ deps/
│  ├─ models/
│  ├─ schemas/
│  ├─ security/
│  ├─ services/
│  └─ main.py
├─ alembic/
│  ├─ versions/
│  └─ env.py
├─ scripts/
├─ tests/
├─ .env.example
├─ alembic.ini
├─ main.py
├─ requirements.txt
└─ README.md
```

## Flujo oficial de base de datos

No usar `create_all()` como mecanismo de evolución.

El flujo correcto es:

1. cambiar modelos ORM
2. crear o ajustar migración Alembic
3. revisar SQL y constraints
4. aplicar `upgrade head`
5. correr seeds

## Migraciones vigentes

- `20260408_0001_initial_security.py`
- `20260413_0002_boutique_inventory.py`
- `20260413_0003_clientes.py`
- `20260427_0004_venta_boutique.py`

Estas migraciones ya crean el bloque boutique/comercial con nombres físicos en minúscula.

## Seeds oficiales

El seed principal vive en:

- `scripts/seed_security.py`
- `app/services/seed_service.py`

Actualmente garantiza:

- roles base: `ADMIN`, `INV_TALLER`, `INV_BOUTIQUE`, `CAJA`, `MODISTA`
- admin inicial usando `BOOTSTRAP_ADMIN_*`
- tipos boutique base: `VESTIDO`, `VELO`, `BOUQUET`, `OTRO`
- moneda base `BOB`
- tipo de cambio activo de `BOB = 1`

Reglas del seed:

- debe ser idempotente
- no debe hardcodear credenciales sensibles
- no debe asumir datos previos del bloque boutique

## Seguridad y permisos

Autenticación:

- `access token` en header `Authorization`
- `refresh token` en cookie `HttpOnly`
- toda cuenta nueva nace con `must_change_password = true`

Casbin usa como sujeto:

- `rol.codigo`

Formato obligatorio de permisos:

- `<modulo>:<accion>`

Ejemplos actuales:

- `users:create`
- `clients:update`
- `boutique_items:list`
- `currencies:update`
- `exchange_rates:view`
- `boutique_sales:annul`

## Reglas de negocio por módulo

### Seguridad

- `USUARIO` y `CUENTA` se administran juntos desde UI, pero siguen separados en backend
- no se puede desactivar un rol con cuentas activas asociadas
- reset de contraseña administrativo vuelve a marcar `must_change_password = true`

### Cliente

- tabla física: `cliente`
- `cli_cod` es único
- si no se envía `cli_cod`, backend autogenera uno con patrón `CLI-00001`
- `cli_cor` y `cli_ci` son únicos cuando existen
- campos nuevos soportados:
  - `cli_fecha_nac`
  - `cli_pais`
  - `cli_ciudad`
- textos de negocio se normalizan en mayúsculas y correo en minúsculas

### Proveedor

- tabla física: `proveedor`
- `pro_cel` y `pro_cor` son únicos cuando existen
- no se puede desactivar un proveedor con items activos asociados

### Moneda

- tabla física: `moneda`
- `mon_cod` es único
- solo puede existir una moneda base activa
- la moneda base no puede quedar deshabilitada

### Tipo de cambio

- tabla física: `tipo_cambio_moneda`
- `tcm_valor_bob > 0`
- solo puede existir un tipo de cambio activo por moneda
- si la moneda es base, el valor activo debe ser `1`

### Inventario boutique

- `item_boutique.itb_cod` es único
- `itb_stock` e `itb_stock_min` son enteros y no negativos
- `pro_id` es opcional, pero si existe debe referenciar un proveedor habilitado
- `VESTIDO`, `VELO` y `BOUQUET` exigen detalle especializado
- `OTRO` no admite detalle especializado
- no se activa un item si su tipo o proveedor están deshabilitados

### Ventas boutique

- tabla física: `venta_boutique`
- `veb_pre_uni` siempre sale de `item_boutique.itb_precio_venta`
- `veb_cant` es entero y debe ser mayor a cero
- si hay descuento, `veb_motivo_desc` es obligatorio
- `veb_tot` se calcula en base de datos
- si la moneda es base, `veb_tipo_cambio_usado = 1`
- si la moneda no es base, se usa el tipo de cambio activo vigente
- `veb_total_moneda_orig` queda congelado al registrar la venta
- `cancelada` y `anulada` revierten stock, guardan motivo y fecha de cambio de estado

## Routers implementados

- `auth`
- `roles`
- `users`
- `clientes`
- `boutique`
- `monedas`

## Endpoints actuales

### Auth

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/change-password`

### Roles

- `GET /api/v1/roles`
- `GET /api/v1/roles/{id}`
- `POST /api/v1/roles`
- `PATCH /api/v1/roles/{id}`
- `PATCH /api/v1/roles/{id}/status`

### Usuarios

- `GET /api/v1/users`
- `GET /api/v1/users/{user_id}`
- `POST /api/v1/users`
- `PATCH /api/v1/users/{account_id}`
- `PATCH /api/v1/users/{account_id}/status`
- `POST /api/v1/users/{account_id}/reset-password`

### Clientes

- `GET /api/v1/clientes`
- `GET /api/v1/clientes/{id}`
- `POST /api/v1/clientes`
- `PATCH /api/v1/clientes/{id}`
- `PATCH /api/v1/clientes/{id}/status`

### Boutique

- `GET /api/v1/boutique/types`
- `GET /api/v1/boutique/types/{id}`
- `POST /api/v1/boutique/types`
- `PATCH /api/v1/boutique/types/{id}`
- `PATCH /api/v1/boutique/types/{id}/status`
- `GET /api/v1/boutique/proveedores`
- `GET /api/v1/boutique/proveedores/{id}`
- `POST /api/v1/boutique/proveedores`
- `PATCH /api/v1/boutique/proveedores/{id}`
- `PATCH /api/v1/boutique/proveedores/{id}/status`
- `GET /api/v1/boutique/items`
- `GET /api/v1/boutique/items/{id}`
- `POST /api/v1/boutique/items`
- `PATCH /api/v1/boutique/items/{id}`
- `PATCH /api/v1/boutique/items/{id}/status`
- `GET /api/v1/boutique/sales`
- `GET /api/v1/boutique/sales/{id}`
- `POST /api/v1/boutique/sales`
- `PATCH /api/v1/boutique/sales/{id}/cancel`
- `PATCH /api/v1/boutique/sales/{id}/annul`

### Monedas

- `GET /api/v1/monedas`
- `GET /api/v1/monedas/{id}`
- `POST /api/v1/monedas`
- `PATCH /api/v1/monedas/{id}`
- `PATCH /api/v1/monedas/{id}/status`
- `GET /api/v1/monedas/tipos-cambio`
- `GET /api/v1/monedas/tipos-cambio/{id}`
- `POST /api/v1/monedas/tipos-cambio`
- `PATCH /api/v1/monedas/tipos-cambio/{id}`
- `PATCH /api/v1/monedas/tipos-cambio/{id}/status`

## Auditoría mínima actual

- `LOGIN_SUCCESS`
- `LOGIN_FAILED`
- `LOGOUT`
- `PASSWORD_CHANGED`
- `USER_CREATED`
- `ACCOUNT_STATUS_CHANGED`
- `CLIENT_CREATED`
- `CLIENT_UPDATED`
- `CLIENT_STATUS_CHANGED`
- `BOUTIQUE_PROVIDER_CREATED`
- `BOUTIQUE_PROVIDER_UPDATED`
- `BOUTIQUE_PROVIDER_STATUS_CHANGED`
- `BOUTIQUE_TYPE_CREATED`
- `BOUTIQUE_TYPE_UPDATED`
- `BOUTIQUE_TYPE_STATUS_CHANGED`
- `BOUTIQUE_ITEM_CREATED`
- `BOUTIQUE_ITEM_UPDATED`
- `BOUTIQUE_ITEM_STATUS_CHANGED`
- `CURRENCY_CREATED`
- `CURRENCY_UPDATED`
- `CURRENCY_STATUS_CHANGED`
- `EXCHANGE_RATE_CREATED`
- `EXCHANGE_RATE_UPDATED`
- `EXCHANGE_RATE_STATUS_CHANGED`
- `BOUTIQUE_SALE_CREATED`
- `BOUTIQUE_SALE_CANCELLED`
- `BOUTIQUE_SALE_ANNULLED`

## Convenciones obligatorias para próximos módulos

1. un dominio nuevo debe tener modelo, schema, service, router, migración y permisos
2. no mezclar lógica HTTP con reglas de negocio
3. toda mutación sensible debe auditarse
4. toda ruta protegida debe usar `require_permission(...)`
5. los módulos nuevos de base de datos deben usar nombres físicos en minúscula
6. no modificar la base manualmente como flujo oficial

## Validación recomendada después de cambios grandes

1. `python -m alembic -c alembic.ini upgrade head`
2. `python scripts/seed_security.py`
3. `pytest`
4. smoke tests manuales de login, inventario y ventas

## Problema conocido

Puede aparecer el warning de `passlib` con `bcrypt`. La autenticación sigue funcionando, pero conviene revisar el pin de versiones más adelante.
