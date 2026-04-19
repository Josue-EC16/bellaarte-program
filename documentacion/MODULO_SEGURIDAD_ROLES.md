# Modulo de Seguridad V1

Documento operativo de la primera implementacion real del sistema.

## Objetivo del modulo

Construir la base estable para todos los modulos futuros del sistema:

- autenticacion
- autorizacion
- sesion
- roles
- usuarios internos
- estructura tecnica de frontend y backend

Si esta base se mantiene consistente, el resto del sistema puede crecer sin rehacer auth, permisos o estructura.

## Alcance implementado

### Backend

- FastAPI modular
- SQLAlchemy 2
- Alembic
- JWT access token
- refresh token por cookie `HttpOnly`
- Casbin con `model.conf` y `policy.csv`
- seed inicial de roles y admin
- auditoria de eventos de seguridad

### Frontend

- React 19
- Vite 6
- Ant Design
- React Router
- AuthProvider
- guards de rutas
- login
- cambio obligatorio de clave
- home operativo
- gestion de usuarios
- pagina 403

## Modelo de datos de seguridad

### `roles`

Representa los roles del sistema.

Campos principales:

- `id`
- `codigo`
- `nombre`
- `descripcion`
- `activo`
- `created_at`

### `usuarios`

Representa los datos personales del colaborador.

Campos principales:

- `id`
- `nombres`
- `apellido_paterno`
- `apellido_materno`
- `ci`
- `celular`
- `correo`
- `zona`
- `direccion`
- `activo`
- `created_at`
- `updated_at`

### `cuentas`

Representa el acceso tecnico al sistema.

Campos principales:

- `id`
- `usuario_id`
- `rol_id`
- `username`
- `password_hash`
- `must_change_password`
- `last_login_at`
- `is_active`
- `created_at`
- `updated_at`

### `auditoria_sistema`

Representa eventos de trazabilidad de seguridad.

Campos principales:

- `id`
- `cuenta_id`
- `usuario_id`
- `accion`
- `descripcion`
- `referencia`
- `ip_address`
- `user_agent`
- `created_at`

## Roles base sembrados

- `ADMIN`
- `INV_TALLER`
- `INV_BOUTIQUE`
- `CAJA`
- `MODISTA`

## Politica funcional actual

Todos los roles autenticados pueden:

- ver el home
- consultar su sesion
- cambiar su contrasena
- cerrar sesion

Solo `ADMIN` puede:

- listar usuarios
- crear usuarios
- activar o desactivar cuentas
- listar roles

## Flujo tecnico de autenticacion

### Login

1. frontend envia `username` y `password`
2. backend valida credenciales
3. backend audita login exitoso o fallido
4. backend devuelve `access_token` y `user`
5. backend fija `refresh token` en cookie `HttpOnly`

### Refresh

1. frontend detecta `401`
2. interceptor llama a `/auth/refresh`
3. backend valida cookie
4. backend devuelve nuevo `access_token`

### Cambio obligatorio de contrasena

1. cuenta nueva nace con `must_change_password = true`
2. frontend detecta ese estado
3. bloquea navegacion normal
4. redirige a `/app/cambiar-clave`
5. backend actualiza hash y deja `must_change_password = false`

## Endpoints implementados

### Auth

```http
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
GET /api/v1/auth/me
POST /api/v1/auth/change-password
```

### Roles

```http
GET /api/v1/roles
```

### Usuarios

```http
GET /api/v1/users
POST /api/v1/users
PATCH /api/v1/users/{account_id}/status
```

## Frontend: estructura de navegacion

### Rutas publicas

- `/login`

### Rutas privadas

- `/app`
- `/app/cambiar-clave`
- `/app/usuarios`

### Rutas auxiliares

- `/403`

## Reglas obligatorias para futuros modulos

### 1. Toda funcionalidad protegida debe tener permiso

No crear rutas privadas sin permiso explicito.

Formato obligatorio:

```text
<modulo>:<accion>
```

### 2. Todo modulo nuevo debe existir en ambas capas

Backend:

- router
- service
- schema
- modelo si aplica

Frontend:

- pagina
- ruta
- entrada en layout si corresponde

### 3. El backend decide autorizacion

Aunque el frontend oculte opciones, el backend debe seguir protegiendo el acceso.

### 4. Toda tabla nueva debe entrar por migracion

No crear nuevas tablas manualmente desde SQL como flujo normal.

### 5. Toda entidad sensible debe definir auditoria

Especialmente en:

- pedidos
- pagos
- ventas
- stock
- ingresos
- egresos

## Flujo recomendado para siguiente modulo

Ejemplo: `inventario_boutique`

1. crear modelo `inventory_boutique.py`
2. crear schema `inventory_boutique.py`
3. crear service `inventory_boutique_service.py`
4. crear router `inventory_boutique.py`
5. registrar router en `app/api/router.py`
6. agregar permisos Casbin
7. crear migracion Alembic
8. agregar pagina en frontend
9. agregar ruta protegida
10. agregar acceso en menu segun permiso
11. documentar

## Variables de entorno criticas

Backend:

- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `JWT_REFRESH_SECRET_KEY`
- `ACCESS_TOKEN_MINUTES`
- `REFRESH_TOKEN_DAYS`
- `FRONTEND_URL`

Frontend:

- `VITE_API_URL`

## Riesgos a evitar en futuros cambios

### Mezclar nombres de roles visibles con codigos tecnicos

Correcto:

- codigo: `INV_TALLER`
- nombre visible: `ENCARGADA(O) DEL INVENTARIO TALLER`

### Crear logica de negocio dentro de routers

La logica debe ir a `services`.

### Duplicar clientes HTTP en frontend

Debe existir un solo cliente oficial con interceptores.

### Guardar access token en localStorage

No se debe hacer.

### Agregar modulo sin actualizar permisos

Eso rompe la coherencia entre menu, backend y seguridad real.

## Resultado esperado de esta base

Con esta version ya puedes:

- iniciar sesion
- renovar sesion
- cambiar clave
- crear usuarios internos
- controlar acceso por rol
- usar esta estructura como plantilla para inventarios, pedidos y finanzas
