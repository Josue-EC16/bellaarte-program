# MODULO NOTIFICACIONES

## Objetivo

El módulo de `NOTIFICACIONES` centraliza las alertas internas de BELLAARTE BOUTIQUE para que cada área reciba a tiempo los avisos que realmente le corresponden:

- stock bajo en boutique
- stock bajo en taller
- entregas próximas de pedidos
- pruebas próximas de pedidos
- alertas de alistar material para prueba 1 y 2
- devoluciones próximas o vencidas de fletes
- fletes que alcanzaron su máximo de salidas válidas
- errores de envío de correo de credenciales

No existe alta manual de notificaciones en v1. La creación es automática por evento o por script programado.

## Estructura técnica

### Base de datos

Se agregó el dominio:

- `notificacion`
- enum `prioridad_notificacion`

Campos nuevos relevantes:

- `not_tabla_ref`
- `not_id_ref`
- `not_resuelta`
- `not_fec_resuelta`

Checks e índices:

- `ck_not_resuelta_fecha`
- índices por usuario/fecha, tipo/fecha, prioridad/fecha, módulo/fecha, referencia
- índices parciales para no leídas y no resueltas en migración

### Backend

Archivos principales:

- `backend/app/models/notification.py`
- `backend/app/schemas/notification.py`
- `backend/app/services/notification_service.py`
- `backend/app/services/notification_job_service.py`
- `backend/app/api/routers/notifications.py`
- `backend/scripts/run_notification_checks.py`
- `backend/alembic/versions/20260529_0009_notifications.py`

### Frontend

Archivos principales:

- `frontend/src/pages/notificaciones/NotificationsPage.jsx`
- `frontend/src/pages/notificaciones/notificationUtils.js`
- `frontend/src/layout/AuthenticatedLayout.jsx`
- `frontend/src/routes/AppRoutes.jsx`

## Tipos soportados

- `STOCK_BAJO_BOUTIQUE`
- `STOCK_BAJO_TALLER`
- `ENTREGA_PEDIDO_2_DIAS`
- `ENTREGA_PEDIDO_1_DIA`
- `ENTREGA_PEDIDO_HOY`
- `PRUEBA_PEDIDO_2_DIAS`
- `PRUEBA_PEDIDO_1_DIA`
- `PRUEBA_PEDIDO_HOY`
- `PRUEBA_1_ALISTAR_MATERIAL`
- `PRUEBA_2_ALISTAR_MATERIAL`
- `DEVOLUCION_FLETE_2_DIAS`
- `DEVOLUCION_FLETE_1_DIA`
- `DEVOLUCION_FLETE_HOY`
- `DEVOLUCION_FLETE_VENCIDA`
- `FLETE_MAX_SALIDAS`
- `ERROR_ENVIO_CORREO`
- `SISTEMA`

## Prioridades

La prioridad conceptual `CRITICA` se implementa con el enum `URGENTE`.

- `BAJA`
- `MEDIA`
- `ALTA`
- `URGENTE`

## Lógica operativa

### 1. Stock bajo boutique

Se evalúa cada vez que cambia el stock de `item_boutique` por:

- venta boutique
- reversión de venta
- entrada boutique
- cambio de estado de entrada boutique

Regla:

- si `itb_stock <= itb_stock_min` y el item está activo, se crea o mantiene una alerta
- si el stock vuelve a estar por encima del mínimo, la alerta se resuelve

Destinatarios:

- `ADMIN`
- `INV_BOUTIQUE`

### 2. Stock bajo taller

Se evalúa cada vez que cambia el stock de `inventario_taller` por:

- entrada taller
- cambio de estado de entrada taller
- salida taller
- cambio de estado de salida taller

Destinatarios:

- `ADMIN`
- `INV_TALLER`

### 3. Entregas próximas de pedidos

Se sincronizan:

- al crear/editar/cambiar estado/entregar pedido
- al registrar o anular pagos de pedido
- por script diario

Destinatarios:

- `ADMIN`
- `MODISTA`
- `INV_BOUTIQUE`
- `CAJA` solo si el pedido conserva saldo pendiente

### 4. Pruebas próximas

Se sincronizan:

- al crear o editar una prueba
- por script diario

Destinatarios:

- `ADMIN`
- `MODISTA`
- `INV_BOUTIQUE`

### 5. Alistar material para prueba 1 y 2

Se emite inmediatamente al registrar o reprogramar una prueba `1` o `2`.

Destinatarios:

- `ADMIN`
- `MODISTA`
- `CAJA`

### 6. Devoluciones de flete

Se sincronizan:

- al crear una salida de flete
- al devolver una salida
- al anular una salida
- por script diario

Destinatarios base:

- `ADMIN`
- `INV_BOUTIQUE`

`CAJA` también recibe la alerta cuando hay señal económica operativa:

- `garantia > garantia_devuelta`
- o `monto_arreglo > 0`

### 7. Máximo de salidas de flete

Se evalúa al:

- devolver una salida válida
- anular una salida contada
- resolver revisión
- pasar a venta
- retirar flete
- por script diario

Destinatarios:

- `ADMIN`
- `INV_BOUTIQUE`

### 8. Error de envío de correo

Cuando falla el envío del correo de bienvenida:

- no se expone la contraseña
- se crea `ERROR_ENVIO_CORREO`
- solo lo recibe `ADMIN`

Reintento:

- botón manual desde notificación
- modo técnico por script `retry-emails`

Si el reintento sale bien:

- la notificación se marca como resuelta
- la cuenta vuelve a quedar con contraseña temporal basada en `CI`
- `must_change_password = true`

## Prevención de duplicados

La deduplicación se hace por:

- usuario destinatario
- tipo de notificación
- tabla origen
- id origen
- estado no resuelto

Eso evita que el mismo evento cree múltiples alertas abiertas para la misma persona.

## Estados conceptuales

La tabla trabaja con:

- `not_leida`
- `not_resuelta`

Y el frontend interpreta:

- `PENDIENTE`
- `LEÍDA`
- `RESUELTA`

## Permisos

### ADMIN

- `notifications:list`
- `notifications:view`
- `notifications:mark_read`
- `notifications:mark_all_read`
- `notifications:resolve`
- `notifications:retry_email`
- `notifications:report`
- `notifications:list_all`

### INV_BOUTIQUE

- `notifications:list`
- `notifications:view`
- `notifications:mark_read`
- `notifications:mark_all_read`

### INV_TALLER

- `notifications:list`
- `notifications:view`
- `notifications:mark_read`
- `notifications:mark_all_read`

### MODISTA

- `notifications:list`
- `notifications:view`
- `notifications:mark_read`
- `notifications:mark_all_read`

### CAJA

- `notifications:list`
- `notifications:view`
- `notifications:mark_read`
- `notifications:mark_all_read`

## Endpoints

- `GET /api/v1/notificaciones/resumen`
- `GET /api/v1/notificaciones`
- `GET /api/v1/notificaciones/{notification_id}`
- `PATCH /api/v1/notificaciones/{notification_id}/read`
- `PATCH /api/v1/notificaciones/read-all`
- `PATCH /api/v1/notificaciones/{notification_id}/resolve`
- `POST /api/v1/notificaciones/{notification_id}/retry-email`
- `GET /api/v1/notificaciones/reportes/resumen`

## Script programado

Script:

- `backend/scripts/run_notification_checks.py`

Modos:

- `python backend/scripts/run_notification_checks.py --mode daily`
- `python backend/scripts/run_notification_checks.py --mode retry-emails`

Uso recomendado:

- `daily` a primera hora, por ejemplo `08:00`
- `retry-emails` varias veces al día si se quiere reintento técnico automático

## UX/UI implementada

### Header

- campana de notificaciones en la barra superior
- contador de no leídas
- panel desplegable con las últimas alertas
- acceso rápido a:
  - ver detalle
  - marcar leída
  - ir al origen
  - ver todas

### Página completa

Ruta:

- `/app/notificaciones`

Incluye:

- filtros
- tabs rápidas
- tabla histórica
- detalle con `GET` fresco
- acción de resolver para admin
- acción de reintentar correo para admin
- resumen superior para admin

## Validaciones y seguridad

- usuarios y cuentas inactivas no reciben nuevas notificaciones
- backend filtra por destinatario real
- usuarios no admin no pueden ver notificaciones ajenas
- errores técnicos solo llegan a `ADMIN`
- no se exponen contraseñas ni credenciales sensibles en mensajes
- la referencia al origen queda en `not_tabla_ref` + `not_id_ref`

## Validación ejecutada

- `pytest backend/tests -q`
- `pnpm lint`
- `pnpm build`

## Resultado

El sistema ahora tiene un módulo transversal de notificaciones listo para operación real, con generación automática, deduplicación, resolución, control por rol, campana en el header y script programado para chequeos diarios.
