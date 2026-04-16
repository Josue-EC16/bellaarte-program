# Modulo Seguridad v2

## Objetivo

Esta version amplía el modulo de seguridad inicial para convertirlo en un CRUD operativo completo de:

- `ROL`
- `USUARIO`
- `CUENTA`

La implementacion conserva las tablas tecnicas reales ya existentes en el sistema:

- `roles`
- `usuarios`
- `cuentas`
- `auditoria_sistema`

## Alcance funcional

- listar roles
- ver rol
- crear rol
- editar rol
- activar y desactivar rol
- listar usuarios y cuentas
- ver ficha operativa de usuario
- crear usuario interno
- editar datos personales y cuenta en una sola operacion
- activar y desactivar usuario/cuenta
- resetear contrasena temporal

## Reglas de negocio

- `codigo` y `nombre` de rol deben ser unicos
- no se puede desactivar un rol con cuentas activas asociadas
- `USUARIO` y `CUENTA` se administran juntos desde frontend, pero siguen separados en backend
- `username`, `correo` y `ci` deben ser unicos
- no se puede asignar un rol deshabilitado a una cuenta
- el reset de contrasena vuelve a marcar `must_change_password = true`
- el cambio de estado operativo desde UI desactiva tanto `usuario.activo` como `cuenta.is_active`

## API

### Roles

- `GET /api/v1/roles`
- `GET /api/v1/roles/{id}`
- `POST /api/v1/roles`
- `PATCH /api/v1/roles/{id}`
- `PATCH /api/v1/roles/{id}/status`

### Usuarios y cuentas

- `GET /api/v1/users`
- `GET /api/v1/users/{user_id}`
- `POST /api/v1/users`
- `PATCH /api/v1/users/{account_id}`
- `PATCH /api/v1/users/{account_id}/status`
- `POST /api/v1/users/{account_id}/reset-password`

## Permisos

`ADMIN`:

- CRUD completo de roles
- CRUD completo de usuarios y cuentas
- reset de contrasena temporal

## Frontend

### Rutas

- `/app/seguridad/roles`
- `/app/seguridad/usuarios`

### Pantallas

- gestion de roles con tabla y drawer
- gestion de usuarios con tabla operativa, edicion, estado y reset de clave

## Auditoria

Eventos relevantes:

- `ROLE_CREATED`
- `ROLE_UPDATED`
- `ROLE_STATUS_CHANGED`
- `USER_CREATED`
- `USER_UPDATED`
- `ACCOUNT_STATUS_CHANGED`
- `PASSWORD_RESET`

## Validacion realizada

- pruebas de contrato backend
- lint frontend
- build frontend
- smoke test real de creacion de rol
- smoke test real de creacion, edicion y reset de usuario
