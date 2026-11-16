# Modulo Taller

## Objetivo

Este módulo implementa el bloque operativo inicial del Taller dentro del sistema BellaArte. Su propósito es controlar:

- el catálogo de tipos de inventario del taller
- el inventario base de materiales e insumos
- las entradas de materiales al taller
- las salidas o consumo de materiales del taller
- el stock disponible en tiempo real

El módulo fue diseñado para convivir con Boutique, Proveedores, Seguridad y Auditoría, siguiendo la misma arquitectura del proyecto:

- backend con `FastAPI + SQLAlchemy + Alembic`
- frontend con `React + Ant Design`
- permisos con `Casbin`
- trazabilidad con `auditoria_sistema`

## Alcance implementado

Esta versión del módulo Taller cubre:

- CRUD de `tipo_inventario_taller`
- CRUD de `inventario_taller`
- registro de `entrada_inventario_taller`
- registro de `salida_material_taller`
- activación y desactivación lógica de movimientos
- reversión automática de stock al desactivar entradas o salidas
- validación estricta de unidad de medida
- integración de permisos por rol
- integración de frontend con formularios, listados y detalle

No se incluye todavía:

- conversión entre unidades de medida
- edición de movimientos después del registro
- ajuste manual especializado de stock
- integración con pedidos o producción detallada por orden

## Tablas que interactúan

### Tablas principales del módulo

- `tipo_inventario_taller`
- `inventario_taller`
- `entrada_inventario_taller`
- `salida_material_taller`

### Tablas externas relacionadas

- `proveedor`
- `usuarios`
- `auditoria_sistema`

## Modelo de datos implementado

### Enum `unidad_medida`

Valores soportados:

- `metro`
- `centimetro`
- `rollo`
- `caja`
- `kilogramo`
- `gramo`
- `yarda`
- `randa`
- `unidad`
- `otro`

### Enum `motivo_entrada_taller`

Valores soportados:

- `entrada_stock`
- `devolucion`
- `ajuste_positivo`
- `registro_inicial`
- `otro`

## Tabla `tipo_inventario_taller`

Catálogo maestro para clasificar materiales del taller.

Campos:

- `tit_id`
- `tit_nom`
- `tit_des`
- `tit_hab`
- `tit_fec_reg`

Reglas:

- `tit_nom` es único
- no se puede desactivar un tipo con materiales activos asociados
- los textos se normalizan a mayúsculas desde backend

## Tabla `inventario_taller`

Representa cada material o insumo base del taller.

Campos principales:

- `int_id`
- `tit_id`
- `pro_id`
- `int_cod`
- `int_nom`
- `int_color`
- `int_largo`
- `int_ancho`
- `int_material`
- `int_des`
- `int_costo_ref`
- `int_stock`
- `int_uni_med`
- `int_stock_min`
- `int_estado`
- `int_obs`
- `int_fec_reg`

Relaciones:

- pertenece a un `tipo_inventario_taller`
- puede relacionarse opcionalmente con un `proveedor`
- puede tener muchas `entrada_inventario_taller`
- puede tener muchas `salida_material_taller`

Checks implementados:

- `int_costo_ref >= 0`
- `int_stock >= 0`
- `int_stock_min >= 0`
- `int_largo is null or int_largo >= 0`
- `int_ancho is null or int_ancho >= 0`

Reglas de negocio:

- `int_cod` es único
- `pro_id` es opcional
- si existe `pro_id`, el proveedor debe estar habilitado
- no se puede activar un material si su tipo está deshabilitado
- no se puede activar un material si su proveedor está deshabilitado
- si el material ya tiene movimientos activos, el stock no puede editarse libremente desde el CRUD base

## Tabla `entrada_inventario_taller`

Registra el ingreso de material al stock del taller.

Campos principales:

- `emt_id`
- `int_id`
- `usu_id`
- `pro_id`
- `emt_fec`
- `emt_can`
- `emt_uni_med`
- `emt_costo_unitario`
- `emt_motivo`
- `emt_doc_ref`
- `emt_obs`
- `emt_estado`

Relaciones:

- pertenece a un `inventario_taller`
- pertenece a un `usuario`
- puede referenciar opcionalmente a un `proveedor`

Checks implementados:

- `emt_can > 0`
- `emt_costo_unitario >= 0`

Lógica de negocio:

- una entrada suma stock al material base
- la unidad de la entrada debe coincidir exactamente con `inventario_taller.int_uni_med`
- al crear la entrada, se actualiza `inventario_taller.int_costo_ref` con `emt_costo_unitario`
- el movimiento es inmutable después del alta
- solo puede cambiar su estado
- al desactivar una entrada, el stock se revierte una sola vez
- al reactivar una entrada, el stock se vuelve a sumar y se reaplica el costo unitario como costo de referencia

## Tabla `salida_material_taller`

Registra el consumo o salida de material desde el taller.

Campos principales:

- `smt_id`
- `int_id`
- `usu_id`
- `smt_fec`
- `smt_can`
- `smt_uni_med`
- `smt_destino`
- `smt_obs1`
- `smt_obs2`
- `smt_estado`

Relaciones:

- pertenece a un `inventario_taller`
- puede estar asociada a un `usuario`

Checks implementados:

- `smt_can > 0`

Lógica de negocio:

- una salida descuenta stock del material base
- la unidad de salida debe coincidir exactamente con `inventario_taller.int_uni_med`
- no se permite salida con stock insuficiente
- el movimiento es inmutable después del alta
- solo puede cambiar su estado
- al desactivar una salida, el stock se devuelve una sola vez
- al reactivar una salida, el stock vuelve a descontarse si sigue habiendo disponibilidad

## Flujo funcional del módulo

### 1. Crear tipos de inventario taller

Primero se registran categorías como referencia de materiales, por ejemplo:

- ENCAJES
- FORROS
- TULES
- INSUMOS
- APLICACIONES

### 2. Registrar materiales en inventario

Después se crean los materiales concretos en `inventario_taller`, definiendo:

- código
- nombre
- color
- dimensiones opcionales
- material
- costo referencia
- unidad de medida
- stock inicial
- stock mínimo
- proveedor opcional

### 3. Registrar entradas

Cada entrada:

- identifica el material
- identifica al usuario que registra
- puede vincular proveedor
- define cantidad, unidad, costo unitario y motivo
- incrementa stock
- actualiza costo de referencia

### 4. Registrar salidas

Cada salida:

- identifica el material
- identifica al usuario que registra
- define cantidad, unidad y destino
- reduce stock
- sirve para reflejar consumo real del taller

## Reglas de negocio críticas

### Unidad de medida

La unidad de un movimiento debe coincidir con la unidad del material base.

Ejemplo:

- si el material está en `metro`, no puede registrarse una entrada o salida en `unidad`

Esto evita inconsistencias de stock y errores de conversión.

### Inmutabilidad de movimientos

Las entradas y salidas no se editan después de creadas.

Solo se permite:

- listar
- ver detalle
- activar
- desactivar

La razón de esta decisión es proteger trazabilidad, evitar alteraciones históricas y mantener integridad del stock.

### Reversión de stock

La reversión funciona así:

- desactivar entrada: resta del stock la cantidad del movimiento
- reactivar entrada: vuelve a sumar esa cantidad
- desactivar salida: devuelve esa cantidad al stock
- reactivar salida: vuelve a descontarla si el stock alcanza

Cada reversión se hace exactamente una vez por cambio de estado.

### Materiales y catálogos inactivos

No se permite operar entradas o salidas sobre materiales que:

- estén inactivos
- tengan tipo de inventario inactivo
- en el caso de entradas, tengan proveedor base inactivo cuando corresponda

## Permisos por rol

### `ADMIN`

Acceso total al módulo:

- tipos
- inventario
- entradas
- salidas

### `INV_TALLER`

Acceso operativo completo del Taller:

- CRUD de tipos
- CRUD de inventario
- crear y listar entradas
- crear y listar salidas
- cambiar estado de entradas y salidas

### `MODISTA`

Acceso parcial orientado a operación:

- ver inventario del taller
- listar inventario del taller
- ver salidas
- listar salidas
- crear salidas
- cambiar estado de salidas

No puede:

- crear tipos
- editar catálogo de tipos
- crear entradas
- editar inventario base

### `CAJA`

No tiene permisos operativos en Taller.

## API implementada

El router del módulo es:

- `/api/v1/taller`

### Tipos de inventario

- `GET /api/v1/taller/types`
- `GET /api/v1/taller/types/{type_id}`
- `POST /api/v1/taller/types`
- `PATCH /api/v1/taller/types/{type_id}`
- `PATCH /api/v1/taller/types/{type_id}/status`

### Inventario taller

- `GET /api/v1/taller/inventory`
- `GET /api/v1/taller/inventory/{item_id}`
- `POST /api/v1/taller/inventory`
- `PATCH /api/v1/taller/inventory/{item_id}`
- `PATCH /api/v1/taller/inventory/{item_id}/status`

Filtros soportados:

- `type_id`
- `search`
- `is_active`
- `low_stock`

### Entradas taller

- `GET /api/v1/taller/entries`
- `GET /api/v1/taller/entries/{entry_id}`
- `POST /api/v1/taller/entries`
- `PATCH /api/v1/taller/entries/{entry_id}/status`

Filtros soportados:

- `search`
- `item_id`
- `is_active`

### Salidas taller

- `GET /api/v1/taller/outputs`
- `GET /api/v1/taller/outputs/{output_id}`
- `POST /api/v1/taller/outputs`
- `PATCH /api/v1/taller/outputs/{output_id}/status`

Filtros soportados:

- `search`
- `item_id`
- `is_active`

## Orden de rutas en FastAPI

Para evitar conflictos con rutas dinámicas, el módulo se dejó ordenado así:

1. rutas de colección
2. rutas de detalle `/{id}`
3. rutas de acción `/{id}/status`

Este criterio debe mantenerse si el módulo crece.

## Frontend implementado

### Rutas SPA

- `/app/taller/tipos`
- `/app/taller/inventario`
- `/app/taller/entradas`
- `/app/taller/salidas`

### Pantallas creadas

#### Tipos Taller

Permite:

- listar tipos
- crear tipos
- editar tipos
- activar o desactivar tipos

#### Inventario Taller

Permite:

- listar materiales
- filtrar por tipo, estado, texto y stock bajo
- crear materiales
- editar materiales
- activar o desactivar materiales
- ver detalle completo del material

#### Entradas Taller

Permite:

- listar entradas
- filtrar por material, estado y texto
- registrar nuevas entradas
- ver detalle completo
- activar o desactivar entradas

El formulario muestra:

- material
- proveedor opcional
- cantidad
- unidad bloqueada heredada del material
- costo unitario
- motivo
- documento de referencia
- observaciones

#### Salidas Taller

Permite:

- listar salidas
- filtrar por material, estado y texto
- registrar nuevas salidas
- ver detalle completo
- activar o desactivar salidas

El formulario muestra:

- material
- cantidad
- unidad bloqueada heredada del material
- destino
- observación 1
- observación 2

## Criterios de UX/UI aplicados

Se siguieron los lineamientos ya usados en el sistema:

- `Drawer` y `Modal` con `maskClosable={false}`
- uso de `Row` y `Col` en formularios
- placeholders descriptivos
- normalización de campos de texto a mayúsculas cuando aplica
- detalle consultado siempre con `GET` fresco
- mensajes de error mapeados a campos cuando es posible

## Auditoría implementada

Eventos registrados:

- `WORKSHOP_TYPE_CREATED`
- `WORKSHOP_TYPE_UPDATED`
- `WORKSHOP_TYPE_STATUS_CHANGED`
- `WORKSHOP_ITEM_CREATED`
- `WORKSHOP_ITEM_UPDATED`
- `WORKSHOP_ITEM_STATUS_CHANGED`
- `WORKSHOP_ENTRY_CREATED`
- `WORKSHOP_ENTRY_STATUS_CHANGED`
- `WORKSHOP_OUTPUT_CREATED`
- `WORKSHOP_OUTPUT_STATUS_CHANGED`

Cada evento registra:

- acción
- descripción legible
- cuenta responsable
- usuario responsable
- referencia del registro
- ip
- user agent

## Validaciones importantes del backend

### Tipos

- nombre único

### Inventario

- código único
- costos y stock no negativos
- largo y ancho nulos o positivos
- proveedor válido si se informa

### Entradas

- cantidad mayor a cero
- costo unitario no negativo
- unidad igual a la del material base
- material activo

### Salidas

- cantidad mayor a cero
- unidad igual a la del material base
- stock suficiente
- material activo

## Escenarios soportados

### Caso 1: ingreso de material comprado

1. se crea o identifica el material en inventario
2. se registra una entrada con proveedor, costo y cantidad
3. el stock aumenta
4. el costo referencia se actualiza

### Caso 2: consumo para confección

1. la modista busca el material
2. registra la salida indicando cantidad y destino
3. el stock disminuye
4. la operación queda auditada

### Caso 3: anulación lógica de un movimiento

1. se cambia el estado de la entrada o salida
2. el sistema revierte automáticamente el stock
3. la operación queda auditada

## Relación con otros módulos

### Proveedor

`inventario_taller` y `entrada_inventario_taller` pueden relacionarse con `proveedor`.

### Seguridad

Todas las operaciones del módulo dependen de:

- autenticación
- cuenta activa
- rol activo
- permisos Casbin

### Auditoría

Todo cambio relevante del módulo registra trazabilidad en `auditoria_sistema`.

## Consideraciones para futuras ampliaciones

El módulo quedó preparado para crecer hacia:

- ajustes de stock especializados
- consumo por pedido u orden de confección
- reservas de material para producción
- integración con costos de pedidos
- reportes de consumo por modista o por destino
- conversión entre unidades de medida si el negocio lo requiere

## Validación realizada

Este módulo quedó validado en la implementación con:

- migración Alembic aplicada correctamente
- pruebas backend pasando
- frontend con `lint` correcto
- frontend con `build` correcto

## Resumen operativo

El módulo Taller ya permite controlar materiales reales del taller con una lógica consistente de:

- catálogo
- stock
- ingresos
- salidas
- permisos
- auditoría

Con esto, el sistema ya no solo controla Boutique y Ventas, sino también el flujo operativo base de materiales para confección y producción interna.
