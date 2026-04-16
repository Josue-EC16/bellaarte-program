# Guia de Desarrollo del Proyecto

Guia transversal para construir los siguientes modulos sin romper la base ya implementada.

## Fuente de verdad actual

Para el estado implementado del proyecto, la referencia principal ya no es la documentacion historica sino:

- `backend/README.md`
- `frontend/README.md`
- `documentacion/MODULO_SEGURIDAD_V1.md`
- `documentacion/MODULO_SEGURIDAD_V2.md`
- `documentacion/MODULO_CLIENTE_V1.md`
- `documentacion/MODULO_BOUTIQUE_V1.md`

## Regla madre del proyecto

Todo modulo nuevo debe crecer siguiendo dominios claros y respetando separacion de responsabilidades.

## Backend: contrato de crecimiento

Por cada modulo nuevo se espera:

1. modelo ORM si aplica
2. schema Pydantic
3. service
4. router
5. migracion Alembic
6. permisos Casbin
7. pruebas
8. documentacion

## Frontend: contrato de crecimiento

Por cada modulo nuevo se espera:

1. carpeta en `src/pages/<modulo>/`
2. pagina principal
3. integracion con API oficial
4. ruta protegida si aplica
5. entrada de menu segun permisos
6. validacion visual del flujo

## Permisos

Formato obligatorio:

```text
modulo:accion
```

Ejemplos:

- `inventario_boutique:view`
- `inventario_taller:update`
- `pedidos:create`
- `finanzas:read`

## Variables y entorno

### Backend

Nunca leer variables de entorno dispersas en cualquier archivo.

Toda variable debe centralizarse en:

- `backend/app/core/config.py`

### Frontend

Toda variable visible para Vite debe salir de:

- `frontend/src/config/env.js`

## API

Toda API debe exponerse bajo:

```text
/api/v1
```

No crear endpoints fuera de ese prefijo.

## Base de datos

Nunca usar SQL manual como flujo principal de evolucion.

El camino oficial es:

1. cambiar modelo
2. crear migracion
3. revisar migracion
4. aplicar migracion

## Auditoria

Toda accion critica nueva debe auditarse.

Minimo recomendado:

- creacion
- actualizacion sensible
- anulacion
- cancelacion
- cambio de estado

## Orden sugerido de trabajo futuro
1. ventas de boutique
2. inventario taller / movimiento de inventario
3. pedidos
4. pagos de pedido
5. ingresos
6. egresos
7. logs del sistema

## Convencion de tablas documentales

Si un modulo ya tiene contrato fisico cerrado en la documentacion oficial SQL, se puede respetar ese nombre fisico en mayuscula dentro del ORM y Alembic.

Casos vigentes:

- `TIPO_ITEM_BOUTIQUE`
- `ITEM_BOUTIQUE`
- `DETALLE_VESTIDO_BOUTIQUE`
- `DETALLE_VELO_BOUTIQUE`
- `DETALLE_BOUQUET_BOUTIQUE`
- `CLIENTE`
