# Contratos de Economía — consolidación 18/10/2026

Base `/api/v1`. Cambios coordinados de backend y frontend, preparados en copia aislada. [Reglas del módulo](MODULO_INGRESOS_EGRESOS_CORTE_CAJA.md).

## Autenticación, recursos e idempotencia

JWT y Casbin existentes. Permiso de ruta no sustituye propiedad del recurso: CAJA consulta sus datos y cancela/reembolsa únicamente fuentes propias de su corte activo. ADMIN conserva alcance global. Un reintento vuelve a comprobar autenticación/permisos.

Todas las escrituras económicas actualizadas requieren `Idempotency-Key` no vacía, máximo 120 caracteres. Reutilizar la misma clave por intención ante respuesta incierta. Resultado confirmado idéntico para el mismo actor/operación/payload; 409 si cambia payload. Una operación nueva usa clave nueva. La clave no permite repetir una acción bajo otro actor ni ampliar permisos.

Escrituras incluidas: altas de venta/pago/salida de flete; cancelación/anulación de esas fuentes por rutas anteriores; egresos/correcciones, apertura/cierre de corte, devoluciones monetarias, cancelaciones operativas y movimientos de garantía. Las rutas operativas de entrega/devolución física conservan su contrato y bloqueo de recurso.

| HTTP | Ruta | Permiso |
|---|---|---|
| GET | `/economia/ingresos` | `economy_income:view` |
| GET | `/economia/ingresos/{tipo}/{id}/refund-context` | `economy_refunds:create` + propiedad |
| POST | `/economia/devoluciones` | `economy_refunds:create` + propiedad/corte |
| POST | `/economia/anulaciones-operativas` | `boutique_sales:cancel/annul`, `order_payments:annul` o `flete_outputs:annul`, según origen/acción |
| GET/POST | `/economia/garantias/{salida_id}` / `.../movimientos` | `economy_refunds:create` + propiedad; RETAIN solo ADMIN |
| GET | `/economia/constancias-devolucion/{id}` | `economy_expenses:view` + ADMIN o responsable propio |
| GET/POST | `/economia/egresos` | `economy_expenses:list/create` |
| GET/PATCH | `/economia/egresos/{id}` / `.../annul` | `economy_expenses:view/annul` + propiedad |
| GET/POST | `/economia/cortes-caja` | `cash_cuts:list/open` (ADMIN) |
| GET/PATCH | `/economia/cortes-caja/{id}` / `.../close` | `cash_cuts:view/close` (ADMIN) |
| GET | `/economia/cortes-caja/me`, `/me/history` | `cash_cuts:view_own` |
| GET | `/economia/reportes/estado-resultados`, `/flujo-efectivo`, `/cajeros/{id}` | `economy_reports:view_all` |
| GET | `/economia/reportes/mi-periodo`, `/mi-estado-resultados`, `/mi-historial` | `economy_reports:view` |

CSV requiere además `economy_reports:export`. No se agregan políticas nuevas ni permisos a cuentas empresariales.

## Listados y filtros

`GET ingresos`, `egresos`, `cortes-caja` y `cortes-caja/me/history` devuelven envelope:

```json
{"items": [], "total": 0, "page": 1, "page_size": 25}
```

Página positiva; tamaño 1–100. Ingresos añade `total_bob` y `refunded_total_bob` sobre el filtro completo. Egresos añade `total_bob` neto de egresos registrados y correcciones vinculadas. Cortes añade `open_count`, `closed_count`, `observed_count` sobre el alcance completo.

Ingresos: `search`, `source_type`, `user_id`, `currency_id`, `payment_method`, `date_from`, `date_to`. Fuentes: VENTA_BOUTIQUE/PAGO_PEDIDO/SALIDA_FLETE. Métodos: efectivo/qr/transaccion/tarjeta/ticket_o_vale. Fechas ISO, interpretación America/La_Paz, rango invertido 422. CAJA sin corte activo obtiene página vacía; no se le concede acceso global por omitir filtros.

Egresos: `search`, `type`, `state`, `cut_id`, fechas. Fila conserva `monto` original y añade `metodo_pago`, `adjusted_amount_bob`, `net_amount_bob`; detalle añade `constancia_id`. Anulado tiene salida neta cero. Corrección real conserva estado registrado y reduce su salida neta.

Ingresos mantiene bruto, devuelto y añade `monto_neto_bob`, `pendiente_devolucion_bob`, `corte_id`. El contexto de reembolso añade `can_refund`, `refund_block_reason`, `net_collected_bob`, `pending_refund_bob` y máximo disponible. El GET nunca realiza un reembolso.

## Reembolso y cancelación

`POST /economia/devoluciones`:

```json
{
  "origin_type": "VENTA_BOUTIQUE",
  "origin_id": 12,
  "refund_amount": 200.00,
  "payment_method": "efectivo",
  "reason": "DEVOLUCION ACORDADA CON EL CLIENTE",
  "concepto": "DEVOLUCION DE VENTA",
  "beneficiario": "CLIENTE",
  "observaciones": null
}
```

Importe BOB positivo, máximo dos decimales. Omitir `target_state`: ya no se permite solicitar una anulación junto al reembolso. Respuesta 201 con `expense_id`, `constancia_id`, importe, estado del origen sin cambio y saldo reembolsable restante. Superar máximo, usar corte legado o reembolsar pedido entregado: 409.

`POST /economia/anulaciones-operativas` recibe `origin_type`, `origin_id`, `target_state` y `reason`. Venta admite CANCELADA/ANULADA; pago/flete ANULADA. Respuesta identifica origen, estado y `pending_refund_bob`; `money_returned_bob=0`. Cancelación repetida con clave nueva: 409; reintento con clave original devuelve el resultado anterior.

La constancia GET devuelve `{id, fecha, snapshot, fiscal:false}`. Snapshot contiene origen, comprobante original, egreso, moneda BOB, importe, medio, responsable, motivo, beneficiario y saldos a la emisión. La impresión escapa el texto y no representa una factura fiscal.

## Egresos, garantías y cortes

Alta egreso conserva sus campos y exige `metodo_pago`; cantidad/precio con escala máxima dos. DEVOLUCION manual se rechaza: utilizar el coordinador de reembolso.

Corrección: `motivo`, `money_did_not_leave` (declaración explícita) y `adjustment_method` opcional. CAJA solo corrige propio/corte abierto sin salida real; ADMIN para restitución real/histórica debe declarar medio. No se vuelve a mover stock ni anular el origen por corregir un egreso.

Garantía GET devuelve `received_bob`, `returned_bob`, `retained_pending_bob`, `available_return_bob`. POST movimientos: `action` RECEIVE/RETURN/RETAIN, `amount` BOB positivo, `payment_method`, `reason`. Recepción única por garantía configurada. Devolución y retención no pueden superar custodia disponible. La devolución física omite `garantia_devuelta`; un intento explícito de modificarla por esa ruta se rechaza.

Apertura: cajero, fondo BOB no negativo y observaciones. Cierre: `estado` cerrado/cerrado_observado, `efectivo_recibido` (mapa código moneda → importe no negativo de dos decimales), `observaciones_cierre`, `cierre_legado`.

Un corte controlado exige conteo por todas las monedas esperadas; diferencias exigen observado con explicación. Un corte legado exige `cierre_legado:true`, observación y ningún conteo pretendidamente certificado. No se acepta abierto como estado de cierre.

Campos de corte: `control_version`, `certified`, `efectivo_esperado`, `efectivo_recibido`, `diferencias_efectivo`, `efectivo_libre_bob`, `garantias_reservadas_bob`. Abierto aún no está certificado; cerrado controlado lee snapshot inmutable. Historial propio conserva cifras sin notas internas de ADMIN.

## Reportes y consumidores

Reportes globales aceptan fechas, cajero, fuente, moneda y medio. Reporte por cajero ahora acepta fechas y preserva usuarios cuyo rol cambió. Filtros que solo limitan ingresos devuelven `comparable:false`, `comparison_note` y resultado/flujo neto null. Egresos se muestran como referencia del período, sin imputación ficticia. El CSV de flujo incluye una fila RESUMEN y la columna COMPARABILIDAD, incluso si no hay filas mensuales.

`mi-periodo` incluye fondo; `mi-estado-resultados` es ingreso menos egreso comercial, sin fondo. No equivalen a utilidad contable.

Pedidos: `total_cobrado_bruto_bob`, `total_devuelto_bob`, `total_pagado` neto, `saldo_exigible_bob`, `devolucion_pendiente_bob`. Pagos (también resumen dentro de pedido): `gross_amount_bob`, `refunded_amount_bob`, `effective_amount_bob`. Reporte de pagos: `gross_total_bob`, `refunded_total_bob`, `total_bob` neto y agrupaciones netas. `monto_bob` del pago original conserva el bruto histórico.

## Compatibilidad y errores

401 autenticación, 403 permiso/propiedad, 404 origen inexistente, 409 conflicto empresarial/idempotencia, 422 contrato/rango/método/escala. No se transforma un error en éxito. Frontend y backend deben promoverse juntos: consumidores anteriores que esperen arrays o devolución con cambio de estado son incompatibles.
