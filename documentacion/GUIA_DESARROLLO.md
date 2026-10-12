# Guia de Desarrollo del Proyecto

Guía transversal para seguir creciendo sin romper la base ya implementada.

## Documentación vigente

Las referencias principales del estado actual son:

- `backend/README.md`
- `frontend/README.md`
- `documentacion/MODULO_SEGURIDAD_V1.md`
- `documentacion/MODULO_SEGURIDAD_V2.md`
- `documentacion/MODULO_CLIENTE_V1.md`
- `documentacion/MODULO_BOUTIQUE_V1.md`
- `documentacion/MODULO_PROVEEDOR.md`
- `documentacion/MODULO_MONEDA.md`
- `documentacion/MODULO_TIPO_CAMBIO_MONEDA.md`
- `documentacion/MODULO_VENTAS_BOUTIQUE.md`
- `documentacion/MODULO_TALLER.md`
- `documentacion/MODULO_FLETES.md`

## Regla madre del proyecto

Cada módulo nuevo debe crecer como dominio claro, con backend, frontend, permisos, migración, auditoría y documentación.

## Contrato de crecimiento backend

Por cada módulo nuevo se espera:

1. modelo ORM si aplica
2. schemas Pydantic
3. service
4. router
5. migración Alembic
6. permisos Casbin
7. pruebas
8. documentación

## Contrato de crecimiento frontend

Por cada módulo nuevo se espera:

1. carpeta en `src/pages/<modulo>/`
2. página principal
3. integración con la API oficial
4. ruta protegida
5. entrada de menú según permisos
6. validación visual y flujo de lectura/edición

## Variables y entorno

### Backend

Toda variable debe centralizarse en:

- `backend/app/core/config.py`

### Frontend

Toda variable visible para Vite debe salir de:

- `frontend/src/config/env.js`

## API

Toda API debe exponerse bajo:

- `/api/v1`

## Base de datos

Flujo oficial:

1. cambiar modelos
2. crear o revisar migración
3. aplicar `upgrade head`
4. correr seeds

Regla vigente:

- los módulos nuevos y los módulos reescritos de base de datos deben usar nombres físicos en minúscula

## Permisos

Formato obligatorio:

- `modulo:accion`

Ejemplos:

- `clients:update`
- `boutique_items:list`
- `currencies:update`
- `exchange_rates:view`
- `boutique_sales:annul`

## Auditoría

Toda acción crítica nueva debe auditarse.

Mínimo recomendado:

- creación
- actualización sensible
- cambio de estado
- cancelación
- anulación

## Estándar actual de dominios ya implementados

- seguridad
- clientes
- boutique
- proveedores
- monedas
- tipos de cambio
- ventas boutique
- taller
- fletes
- pedidos, pagos y pruebas

## Orden sugerido de crecimiento

1. inventario taller
2. movimientos de stock
3. ingresos y egresos
4. comprobantes internos generales
5. notificaciones automáticas
6. reportes avanzados

## Checklist para agregar un módulo

1. crear modelos ORM
2. crear schemas
3. crear service
4. crear router
5. registrar router en `app/api/router.py`
6. agregar permisos en Casbin
7. crear migración Alembic
8. escribir pruebas
9. documentar el módulo
10. integrar el frontend
