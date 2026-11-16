# Módulo Pedidos, Pagos y Pruebas

## Resumen

Este módulo gestiona el ciclo operativo de pedidos de confección de BellaArte Boutique: registro del pedido principal, detalle especializado, pruebas/agendas, pagos parciales o finales, saldos, entrega, cancelación, inactivación y reportes.

La v1 sigue sin integrar `comprobante_interno`; los pagos afectan únicamente `pago_pedido` y el saldo persistido en `pedido`.

## Ajustes Aplicados Sobre La V1

Se reforzó el módulo con base en la auditoría funcional y técnica:

- normalización a MAYÚSCULAS en backend para textos de negocio del módulo;
- normalización visual y de captura en frontend para formularios de pedidos, pagos y pruebas;
- validación de `fecha_entrega >= HOY`;
- validación de pruebas para que no queden después de la entrega comprometida;
- restricción de cambios de estado para que `CANCELADO` e `INACTIVO` solo se apliquen desde `ACTIVO`;
- doble confirmación para cancelar pedidos con pagos registrados;
- selector guiado de país y ciudad en pedidos de viaje;
- visualización opcional de totales convertidos a otra moneda solo para consulta;
- agenda de pruebas mejorada con vista operativa por horas;
- detalle del pedido renderizado con tarjetas y descripciones, sin bloques crudos de JSON;
- ampliación del formulario especializado de `VESTIDO` con medidas faltantes.

## Tablas

Tablas creadas por Alembic y usadas por el módulo:

- `pedido`: contrato principal del cliente.
- `pedido_vestido`: detalle especializado para vestidos.
- `pedido_velo`: detalle especializado para velos.
- `pedido_cola`: detalle especializado para colas.
- `pedido_manga`: detalle especializado para mangas.
- `pedido_bouquet`: detalle especializado para bouquets.
- `pedido_otro`: detalle especializado para pedidos no categorizados.
- `prueba_pedido`: agenda y estado de pruebas.
- `pago_pedido`: pagos sobre pedidos.

Tablas relacionadas:

- `cliente`: cliente dueño del pedido.
- `usuarios`: usuario responsable del pedido, pago o cambio.
- `moneda`: moneda usada en pagos.
- `tipo_cambio_moneda`: tipo de cambio activo para moneda no base.
- `auditoria_sistema`: trazabilidad de mutaciones críticas.

## Enums

En base de datos e implementación actual siguen existiendo con sus valores técnicos definidos en el sistema. En UI y validaciones de negocio se presentan y normalizan en MAYÚSCULAS para el usuario.

- `tipo_pedido`: `VESTIDO`, `VELO`, `COLA`, `MANGA`, `BOUQUET`, `OTRO`.
- `motivo_descuento_pedido`: `REBAJA`, `PROMOCION`, `BONIFICACION`, `ADMINISTRATIVO`.
- `estado_pedido_general`: `ACTIVO`, `INACTIVO`, `ENTREGADO`, `CANCELADO`.
- `estado_pago_pedido`: `REGISTRADO`, `ANULADO`.
- `prueba_estado_pedido`: `LISTO`, `COSTURERO_TALLER`, `DECORACION`, `COSTURERO_EXTERNO`, `OTRO`.

## Reglas De Pedido

- El cliente debe existir y estar habilitado.
- El usuario encargado es el usuario autenticado que registra el pedido y debe estar activo.
- `ped_cod` es único; si no se envía, el backend genera `PED-00001`, `PED-00002`, etc.
- `ped_pre_tot` es columna generada: `ped_precio - coalesce(ped_descuento, 0)`.
- `ped_total_pagado` y `ped_saldo` no se editan manualmente; se recalculan desde pagos válidos.
- Si existe descuento, debe existir motivo.
- Si `ped_viaje = true`, debe registrarse país o ciudad destino.
- `fecha_entrega` no puede ser anterior al día actual.
- El tipo del pedido no se puede cambiar después de creado.
- Cada pedido debe tener exactamente un detalle especializado correspondiente a `ped_tipo`.
- `pedido_otro` usa la tabla exacta definida: nombre, color principal/secundario, largo, ancho, descripción y observaciones.
- Los textos de negocio se guardan en MAYÚSCULAS desde backend: código, observaciones, país, ciudad, colores, materiales, diseños, descripciones y motivos.

## Detalle Especializado De Vestido

El formulario y la estructura especializada de `VESTIDO` incluyen:

- `tipo_vestido`
- `color_principal`
- `color_secundario`
- `descripcion_material`
- `descripcion_diseno`
- `descripcion_adicional`
- `ancho_espalda`
- `talle_espalda`
- `talle_delantero`
- `contorno_cintura`
- `contorno_cadera`
- `largo_falda`
- `sisa`
- `ancho_busto`
- `separacion_busto`
- `talle_busto`
- `talle_costado`
- `observaciones`

Los cinco campos agregados en UI para cerrar la brecha con la base ya existente son:

- `pdv_sisa`
- `pdv_anb_bus`
- `pdv_sep_bus`
- `pdv_tal_bus`
- `pdv_tal_cos`

## Estados

`ACTIVO` permite edición, pagos y pruebas.

`INACTIVO` representa error o baja lógica. Ahora solo se permite si el pedido está actualmente `ACTIVO` y no tiene pagos registrados.

`CANCELADO` conserva historial y bloquea pagos/pruebas nuevos. Exige motivo y, si el pedido ya tiene pagos, el frontend obliga una confirmación final adicional antes de ejecutar la acción.

`ENTREGADO` exige saldo `0`, fecha final de entrega y coherencia con la fecha comprometida.

## Reglas De Pagos

- Los pagos solo se registran sobre pedidos activos y habilitados.
- No se permite pagar más que el saldo pendiente.
- El pago queda en `REGISTRADO`.
- La moneda debe estar habilitada.
- Si la moneda es base, el tipo de cambio usado es `1`.
- Si la moneda no es base, debe existir tipo de cambio activo en `tipo_cambio_moneda`.
- `ppd_monto_bob` es columna generada: `ppd_monto * ppd_tipo_cambio_usado`.
- Al anular un pago se guarda fecha, motivo, auditoría y se recalcula el saldo.
- Los pagos anulados no cuentan para deuda, saldo ni reportes económicos reales.
- El listado de pagos ahora soporta filtros por estado, método, moneda, usuario y rango de fechas.

## Reglas De Pruebas

- Las pruebas solo se registran sobre pedidos activos y habilitados.
- `prp_num` debe ser mayor a `0`.
- No se puede repetir número de prueba por pedido.
- La secuencia debe ser lógica: no se registra prueba 2 si no existe prueba 1.
- La fecha no puede ser anterior al día actual.
- La fecha tampoco puede quedar después de la fecha de entrega comprometida.
- Si existe `fecha_entrega_final`, la prueba tampoco puede quedar después de esa fecha.
- Se permite editar fecha, hora, estado y observación.
- El calendario frontend soporta vista día, semana y mes sin dependencia externa nueva.
- La vista diaria incluye agenda por horas para facilitar la coordinación real de clientas.

## APIs

Pedidos:

- `GET /api/v1/pedidos`
- `GET /api/v1/pedidos/{pedido_id}`
- `POST /api/v1/pedidos`
- `PATCH /api/v1/pedidos/{pedido_id}`
- `PATCH /api/v1/pedidos/{pedido_id}/status`
- `PATCH /api/v1/pedidos/{pedido_id}/deliver`

Pagos:

- `GET /api/v1/pedidos/pagos`
- `GET /api/v1/pedidos/pagos/{pago_id}`
- `POST /api/v1/pedidos/{pedido_id}/pagos`
- `PATCH /api/v1/pedidos/pagos/{pago_id}/annul`

Pruebas:

- `GET /api/v1/pedidos/pruebas`
- `GET /api/v1/pedidos/pruebas/{prueba_id}`
- `POST /api/v1/pedidos/{pedido_id}/pruebas`
- `PATCH /api/v1/pedidos/pruebas/{prueba_id}`

Reportes:

- `GET /api/v1/pedidos/reportes/clientes/{cliente_id}/resumen`
- `GET /api/v1/pedidos/reportes/saldos`
- `GET /api/v1/pedidos/reportes/pagos`
- `GET /api/v1/pedidos/reportes/pruebas`
- `GET /api/v1/pedidos/reportes/entregas`
- `GET /api/v1/pedidos/reportes/clientes/{cliente_id}/imprimible`

## Permisos

Permisos del módulo:

- `orders:list`
- `orders:view`
- `orders:create`
- `orders:update`
- `orders:update_status`
- `orders:deliver`
- `order_payments:list`
- `order_payments:view`
- `order_payments:create`
- `order_payments:annul`
- `order_tests:list`
- `order_tests:view`
- `order_tests:create`
- `order_tests:update`
- `order_reports:view`
- `order_reports:print`

Asignación:

- `ADMIN`: acceso completo.
- `MODISTA`: pedidos, detalles, pruebas, lectura de pagos y reportes; no anula pagos.
- `CAJA`: lectura de pedidos, registro/anulación de pagos y reportes; no edita detalles.
- `INV_TALLER`: sin acceso por defecto.
- `INV_BOUTIQUE`: sin acceso por defecto.

## Auditoría

Eventos registrados:

- `ORDER_CREATED`
- `ORDER_UPDATED`
- `ORDER_STATUS_CHANGED`
- `ORDER_DELIVERED`
- `ORDER_CANCELLED`
- `ORDER_PAYMENT_CREATED`
- `ORDER_PAYMENT_ANNULLED`
- `ORDER_TEST_CREATED`
- `ORDER_TEST_UPDATED`

## Frontend

Rutas SPA:

- `/app/pedidos`
- `/app/pedidos/pagos`
- `/app/pedidos/pruebas`
- `/app/pedidos/reportes`

Pantallas:

- `Pedidos`: tabla, filtros, Drawer de alta/edición, detalle dinámico por tipo, selector de moneda visual y acciones de estado.
- `Pagos`: historial, alta de pago con moneda, anulación con confirmación explícita y filtros ampliados.
- `Pruebas`: tabla y calendario propio con vistas día, semana y mes, además de agenda por horas.
- `Reportes`: saldos por cliente, pagos del periodo, agregados por método/moneda/usuario, pruebas próximas, pruebas pendientes, entregas próximas y reporte imprimible por cliente.

Comportamiento UX aplicado:

- formularios con normalización a MAYÚSCULAS;
- `extra` explicativo en código del pedido;
- selector guiado de país y ciudad para pedidos de viaje;
- bloqueo visual y backend de fechas inválidas;
- doble confirmación de cancelación si el pedido tiene pagos;
- detalle con `GET` fresco y presentación estructurada;
- resumen visual de importes convertido opcionalmente a otra moneda solo como consulta.

La vista imprimible usa HTML y `window.print()` para permitir imprimir o guardar como PDF desde el navegador.

## Flujo Principal

1. `MODISTA` o `ADMIN` registra un pedido activo con detalle especializado.
2. `MODISTA` agenda pruebas secuenciales.
3. `CAJA` registra pagos parciales o finales.
4. El backend recalcula `ped_total_pagado` y `ped_saldo`.
5. Cuando el saldo llega a `0`, un usuario con permiso marca el pedido como entregado.
6. Reportes muestran deuda consolidada, pagos, pruebas próximas y entregas.

## Validaciones Ejecutadas

- `pytest`
- `pnpm lint`
- `pnpm build`

## Nota Técnica Sobre Mayúsculas

No se rehizo la migración del módulo en esta mejora. Por eso, la normalización se aplicó sobre:

- datos de texto guardados por backend;
- captura y presentación en frontend;
- etiquetas visibles de enums para el usuario.

Si más adelante se decide cambiar físicamente los valores almacenados de enums en PostgreSQL a MAYÚSCULAS, eso requerirá una migración específica de base de datos.
