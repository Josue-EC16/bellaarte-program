# MÓDULO DE AUDITORÍA DEL SISTEMA

## Resumen

El módulo de `AUDITORÍA DEL SISTEMA` quedó implementado como un bloque transversal, exclusivo para `ADMIN`, con captura híbrida:

- `backend` como fuente principal de auditoría funcional
- `triggers` PostgreSQL como refuerzo mínimo de trazabilidad
- agrupación por `aud_id_evento`
- exportación `CSV`
- vista imprimible HTML para `PDF` mediante `window.print()`

La tabla `auditoria_sistema` ahora usa la estructura rica aprobada:

- `aud_id`
- `usu_id`
- `aud_fec`
- `aud_modulo`
- `aud_submodulo`
- `aud_tabla`
- `aud_id_registro`
- `aud_accion`
- `aud_accion_funcional`
- `aud_descripcion`
- `aud_campo`
- `aud_valor_anterior`
- `aud_valor_nuevo`
- `aud_metodo_http`
- `aud_ip`
- `aud_user_agent`
- `aud_dispositivo`
- `aud_navegador`
- `aud_sistema_operativo`
- `aud_id_evento`

## Arquitectura aplicada

### 1. Capa backend principal

Se reemplazó el helper legacy por un servicio central en:

- `backend/app/core/audit.py`

Funciones principales:

- `start_audit_event(...)`
- `prime_audit_request_context(...)`
- `reset_audit_request_context(...)`
- `register_audit_summary(...)`
- `register_audit_field_change(...)`
- `register_audit_failure(...)`
- `register_audit_event(...)`
- `parse_user_agent(...)`

Reglas:

- cada request recibe un `aud_id_evento` base mediante middleware
- cada mutación sensible reutiliza ese `aud_id_evento`
- la fila resumen se registra desde backend
- los cambios de campos relevantes se registran automáticamente desde trigger cuando hay `UPDATE`
- no se guardan contraseñas, hashes ni tokens en claro

### 2. Middleware de contexto

Se añadió un middleware en `backend/app/main.py` para:

- crear contexto por request
- propagar método HTTP, IP y user-agent
- limpiar el contexto al terminar la petición

Esto permite agrupar:

- acción principal
- cambios secundarios
- anulaciones relacionadas
- reversiones operativas dentro del mismo evento

### 3. Triggers de refuerzo

La migración crea la función:

- `fn_auditoria_trazabilidad()`

Y registra triggers sobre tablas críticas:

- `venta_boutique`
- `pago_pedido`
- `pedido`
- `prueba_pedido`
- `comprobante_interno`
- `salida_flete`
- `flete_vestido`
- `item_boutique`
- `entrada_item_boutique`
- `inventario_taller`
- `entrada_inventario_taller`
- `salida_material_taller`
- `egreso`
- `moneda`
- `tipo_cambio_moneda`
- `usuarios`
- `cuentas`

Comportamiento:

- si existe contexto del backend:
  - el trigger registra filas por campo modificado en `UPDATE`
  - usa el mismo `aud_id_evento`
- si no existe contexto:
  - registra una traza mínima automática con:
    - `aud_modulo = SISTEMA`
    - `aud_submodulo = TRIGGER_BD`
    - `aud_accion_funcional = TRAZABILIDAD AUTOMATICA DE BD`

## Migración aplicada

Nueva migración:

- `backend/alembic/versions/20260605_0011_audit_system_module.py`

Responsabilidades:

- crear enum `tipo_accion_auditoria`
- transformar la tabla legacy `auditoria_sistema`
- preservar el histórico anterior en la medida mapeable
- crear índices operativos
- crear funciones auxiliares de auditoría
- crear triggers de refuerzo en BD

## Mapeo funcional

El backend normaliza acciones existentes hacia módulo, submódulo, tabla y tipo general de auditoría.

Ejemplos:

- `LOGIN_SUCCESS` -> `SEGURIDAD / LOGIN / cuentas / LOGIN`
- `CLIENT_UPDATED` -> `CLIENTES / EDICION / cliente / UPDATE`
- `BOUTIQUE_SALE_CANCELLED` -> `VENTAS_BOUTIQUE / ANULAR_VENTA / venta_boutique / CANCELACION`
- `ORDER_PAYMENT_ANNULLED` -> `PAGOS_PEDIDO / PAGOS / pago_pedido / ANULACION`
- `CASH_CUT_CLOSED` -> `CORTE_CAJA / CIERRE / corte_caja / CAMBIO_ESTADO`
- `NOTIFICATION_RESOLVED` -> `NOTIFICACIONES / RESOLUCION / notificacion / CAMBIO_ESTADO`

## Seguridad

Permisos nuevos:

- `audit:list`
- `audit:view`
- `audit:view_event`
- `audit:export`

Asignación:

- `ADMIN`: acceso completo
- otros roles: sin acceso

También se auditan accesos denegados relevantes desde `require_permission(...)`.

## API administrativa

Router:

- `/api/v1/auditoria`

Endpoints implementados:

- `GET /api/v1/auditoria`
- `GET /api/v1/auditoria/{audit_id}`
- `GET /api/v1/auditoria/eventos/{event_id}`
- `GET /api/v1/auditoria/export?format=csv|html`

Filtros soportados:

- `user_id`
- `module`
- `submodule`
- `table`
- `record_id`
- `action`
- `functional_action`
- `date_from`
- `date_to`
- `ip`
- `device`
- `browser`
- `operating_system`
- `http_method`
- `event_id`
- `search_description`
- `search_old_value`
- `search_new_value`
- `search_field`

## Frontend

Ruta nueva:

- `/app/auditoria`

Pantalla:

- `frontend/src/pages/auditoria/AuditPage.jsx`

Utilidades:

- `frontend/src/pages/auditoria/auditUtils.js`

Integración:

- menú en `AuthenticatedLayout`
- guard por permiso en `AppRoutes`
- exportación CSV
- impresión / guardado PDF vía HTML imprimible
- drawer de detalle
- vista agrupada por `aud_id_evento`

UX aplicada:

- panel administrativo elegante y denso
- filtros persistidos en `sessionStorage`
- badges por acción
- énfasis visual en:
  - anulaciones
  - cancelaciones
  - cambios de estado
  - eventos de seguridad

## Buenas prácticas aplicadas

- normalización en MAYÚSCULAS de:
  - `aud_modulo`
  - `aud_submodulo`
  - `aud_accion_funcional`
  - descripciones funcionales visibles
- no se exponen:
  - contraseñas
  - hashes
  - tokens
  - secretos
- la auditoría sigue siendo de solo lectura
- no existe creación manual, edición, anulación ni eliminación desde UI o API

## Pruebas realizadas

Validación ejecutada:

- `pytest backend/tests -q` -> `64 passed`
- `alembic upgrade head` -> OK
- `pnpm lint` -> OK
- `pnpm build` -> OK

Pruebas contractuales nuevas:

- `backend/tests/test_audit_contracts.py`

Cobertura validada:

- permisos del módulo
- normalización de filtros
- parseo de user-agent
- creación de fila resumen rica desde el helper central

## Riesgos y notas

- los triggers están diseñados como refuerzo, no como fuente principal
- en operaciones con `flush()` muy temprano, la fila resumen sigue viniendo del backend y los cambios posteriores del `UPDATE` quedan capturados por trigger
- la exportación PDF de v1 usa HTML imprimible para mantener consistencia con el resto del sistema

## Estado final

El sistema queda con auditoría administrativa real, utilizable para:

- trazabilidad operativa
- control de seguridad
- revisión de anulaciones y cancelaciones
- análisis de cambios por campo
- navegación por evento lógico
- exportación e impresión para revisión administrativa
