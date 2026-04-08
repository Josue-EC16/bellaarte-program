# Backend BellaArte

Backend del sistema `bellaarte-program`, construido con FastAPI, SQLAlchemy, Alembic, JWT y Casbin.

Esta primera fase ya implementa el modulo base de seguridad del sistema:

- login interno
- sesiones con `access token` + `refresh token`
- cambio obligatorio de contrasena
- roles base del negocio
- control de permisos con Casbin
- creacion interna de usuarios por `ADMIN`
- auditoria de eventos de seguridad

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

## Estado actual del modulo

Entidades implementadas:

- `roles`
- `usuarios`
- `cuentas`
- `auditoria_sistema`

Routers implementados:

- `auth`
- `roles`
- `users`

Politicas implementadas:

- acceso autenticado al dashboard
- lectura de sesion actual
- cambio de contrasena
- cierre de sesion
- gestion de usuarios solo para `ADMIN`
- lectura de roles solo para `ADMIN`

## Variables de entorno

Crear `.env` en `backend/` a partir de `.env.example`.

Variables soportadas:

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

### Regla importante

Si existe `DATABASE_URL`, el backend usa esa URL como fuente principal.

Si no existe, arma la conexion con:

- `DB_HOST`
- `DB_NAME`
- `DB_USER`
- `DB_PASS`
- `DB_PORT`

### Nota del entorno local actual

En la implementacion validada localmente se uso:

```env
DATABASE_URL=postgresql://MARCELO@localhost:5432/bellaarte_db
```

porque en el PostgreSQL local de Laragon no existia el rol `postgres`.

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

Ejecutar pruebas:

```powershell
pytest
```

Aplicar migraciones:

```powershell
python -m alembic -c alembic.ini upgrade head
```

Ejecutar seed de seguridad:

```powershell
python scripts/seed_security.py
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

## Responsabilidad por carpeta

### `app/main.py`

Factory principal de FastAPI.

Aqui se define:

- metadata de la app
- CORS
- healthcheck
- inclusion del router `/api/v1`

### `app/api/routers/`

Un router por dominio funcional.

Regla:

- no poner logica de negocio pesada aqui
- solo orquestacion HTTP, dependencias y respuestas

### `app/core/`

Infraestructura y piezas transversales:

- config
- database
- seguridad JWT
- permisos
- auditoria

### `app/deps/`

Dependencias reutilizables para FastAPI.

Ejemplo actual:

- autenticacion por bearer token
- validacion de permisos con Casbin

### `app/models/`

Modelos ORM de SQLAlchemy.

Reglas:

- una entidad por archivo
- `snake_case` fisico en tablas y columnas
- sin acentos en nombres tecnicos
- relaciones claras

### `app/schemas/`

Contratos de entrada y salida con Pydantic.

Regla:

- no exponer modelos ORM directamente en respuestas HTTP

### `app/services/`

Logica de negocio por dominio.

Regla:

- si una regla no es puramente HTTP ni puramente ORM, va aqui

### `app/security/`

Definicion base de Casbin:

- `model.conf`
- `policy.csv`

### `scripts/`

Scripts operativos.

Regla:

- deben ser idempotentes cuando sea posible
- no deben duplicar logica que ya vive en `services/`

### `tests/`

Pruebas automatizadas.

## Flujo oficial de base de datos

Este proyecto ya no debe crear tablas con `create_all()` como mecanismo principal de evolucion.

El flujo correcto es:

1. definir o modificar modelos SQLAlchemy
2. crear migracion Alembic
3. revisar migracion
4. aplicar migracion con `upgrade head`
5. correr seeds si corresponde

## Primera migracion actual

Archivo:

- `alembic/versions/20260408_0001_initial_security.py`

Contenido:

- tabla `roles`
- tabla `usuarios`
- tabla `cuentas`
- tabla `auditoria_sistema`

## Seed oficial

El seed base vive en:

- `scripts/seed_security.py`
- `app/services/seed_service.py`

Sembrado actual:

- `ADMIN`
- `INV_TALLER`
- `INV_BOUTIQUE`
- `CAJA`
- `MODISTA`

Tambien crea el primer admin usando variables `BOOTSTRAP_ADMIN_*`.

### Regla para futuros seeds

- no poner contrasenas hardcodeadas en el codigo
- usar variables de entorno
- hacer el seed idempotente

## Seguridad y autenticacion

### Tokens

Se usan dos tokens:

- `access token`
- `refresh token`

El `access token` viaja en header `Authorization: Bearer`.

El `refresh token` viaja en cookie `HttpOnly`.

### Reglas

- no guardar refresh token en base de datos en esta fase
- no devolver password hash bajo ninguna circunstancia
- toda cuenta nueva debe nacer con `must_change_password = true`

### Auditoria actual

Eventos auditados:

- `LOGIN_SUCCESS`
- `LOGIN_FAILED`
- `LOGOUT`
- `PASSWORD_CHANGED`
- `USER_CREATED`
- `ACCOUNT_STATUS_CHANGED`

## Casbin y permisos

Casbin se inicializa en:

- `app/api/router.py`

La politica actual usa como sujeto:

- `rol.codigo`

No usa el nombre visible del rol.

### Regla para futuros modulos

Cada nuevo modulo debe definir permisos con formato:

```text
<modulo>:<accion>
```

Ejemplos:

- `inventario_boutique:view`
- `inventario_boutique:create`
- `pedidos:update`
- `finanzas:read`

### Donde actualizar permisos

Si agregas un modulo nuevo, debes tocar estas piezas:

1. `app/security/policy.csv`
2. `app/core/permissions.py`
3. dependencias de proteccion en routers
4. frontend para mostrar u ocultar menu

## Endpoints actuales

### Auth

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/change-password`

### Roles

- `GET /api/v1/roles`

### Usuarios

- `GET /api/v1/users`
- `POST /api/v1/users`
- `PATCH /api/v1/users/{account_id}/status`

## Contratos clave

### Login request

```json
{
  "username": "admin",
  "password": "Admin12345!"
}
```

### Login response

```json
{
  "access_token": "token",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "full_name": "ADMIN BELLAARTE SISTEMA",
    "role_code": "ADMIN",
    "role_name": "ADMIN",
    "username": "admin",
    "must_change_password": true,
    "permissions": [
      "dashboard:view",
      "auth:me",
      "auth:change_password",
      "auth:logout"
    ]
  }
}
```

## Convenciones obligatorias para futuros modulos

### 1. Un dominio, un router, un servicio

Si agregas `pedidos`, debes crear como minimo:

- `app/api/routers/pedidos.py`
- `app/services/pedidos_service.py`
- `app/schemas/pedidos.py`

Y si aplica:

- `app/models/pedido.py`

### 2. No mezclar logica

- routers: HTTP
- services: negocio
- models: persistencia
- schemas: contrato

### 3. No leer `request` dentro de servicios salvo datos explicitamente necesarios

Los servicios deben recibir datos claros, no depender del contexto web completo.

### 4. Toda ruta protegida debe usar dependencia de permiso

Ejemplo esperado:

```python
account: Cuenta = Depends(require_permission("pedidos:create"))
```

### 5. Toda mutacion sensible debe auditarse

Si un modulo crea, modifica, cancela o anula informacion critica, debe registrar auditoria.

### 6. No saltarse Alembic

No usar cambios manuales en PostgreSQL como flujo normal de evolucion.

### 7. Mantener naming consistente

- tablas: `snake_case`
- columnas: `snake_case`
- clases Python: `PascalCase`
- funciones: `snake_case`
- permisos: `modulo:accion`

## Problemas conocidos

### Warning de Passlib con bcrypt

Puede aparecer este mensaje:

```text
(trapped) error reading bcrypt version
```

La autenticacion sigue funcionando, pero conviene revisar a futuro el pin de versiones de `passlib` y `bcrypt`.

### Diferencia entre documentacion historica y entorno real

La documentacion historica menciona Python 3.14, pero la implementacion actual fue validada localmente con el `venv` existente en Python 3.10.6.

## Checklist para agregar un nuevo modulo

1. crear modelos ORM
2. crear schemas
3. crear servicio
4. crear router
5. registrar router en `app/api/router.py`
6. agregar permisos en Casbin
7. crear migracion Alembic
8. agregar pruebas
9. documentar el modulo
10. conectar el frontend

