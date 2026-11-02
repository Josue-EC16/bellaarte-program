# Economía: ingresos, egresos y cortes de caja

Referencia de implementación: 18/10/2026. Desplegado con autorización el 19/10/2026 en bellaarte_db:5432, revisión Alembic `20261018_0016`, con backend y frontend coordinados. Ver [contratos](CONTRATOS_API_ECONOMIA.md), [despliegue](DESPLIEGUE_ECONOMIA.md) y [resultados](REPORTE_IMPLEMENTACION_ECONOMIA.md).

## Alcance

Se consolida Economía y sus consumidores actuales. No se añade una pantalla general nueva de ingresos ni contabilidad integral. El resultado operativo no representa utilidad: no incorpora imputación completa de costos ni obligaciones contables.

## Definiciones y fórmulas

| Concepto | Fuente / cálculo | Interpretación |
|---|---|---|
| Ingreso comercial bruto | Venta Boutique, pago de pedido, servicio de flete | Cobro histórico, incluso después de anular el origen |
| Devolución efectiva | Egreso DEVOLUCION menos correcciones vinculadas | Salida de dinero, sin borrar ingreso bruto |
| Cobrado neto | Bruto menos devoluciones efectivas | Se conservan ambos componentes |
| Fondo asignado | Anticipo inicial ADMIN → CAJA en BOB | Capital operativo; no venta, ingreso comercial ni deuda automática del empleado |
| Resultado operativo del corte | Fondo + ingresos atribuidos − egresos netos atribuidos | Incluye medios electrónicos; no equivale a billetes entregables |
| Efectivo físico | Movimientos en efectivo por moneda original | BOB y monedas extranjeras se cuentan separadamente |
| Efectivo BOB libre | Físico BOB menos garantías reservadas | Único saldo que puede financiar egresos en efectivo del cajero |
| Garantía | Custodia recibida, devolución y retención pendiente | Fuera del ingreso comercial; efectivo recibido queda reservado |
| Devolución pendiente | Cobrado neto de origen/pedido cancelado | Obligación informativa; no inventa egreso ni retención |

Ejemplo: fondo Bs 500 + cobro QR Bs 1.000 − gasto efectivo Bs 100 = resultado operativo Bs 1.400, efectivo físico BOB 400. El cierre compara el conteo con 400. Una garantía en efectivo aumenta el físico y la reserva, sin aumentar el efectivo libre.

El estado comercial y `mi-estado-resultados` excluyen fondo. `mi-periodo` y cortes incluyen fondo. No deben llamarse utilidad contable.

## Estructura y persistencia

Se conserva FastAPI → contratos Pydantic → servicios → SQLAlchemy/PostgreSQL.

| Servicio | Responsabilidad |
|---|---|
| income_service / economy_query_service | Unión SQL de las tres fuentes, filtros, paginación, agregados y contexto autorizado |
| financial_source_service | Bloqueos, devoluciones efectivas, crédito neto y deuda exigible |
| refund_flow_service | Coordinadores separados de devolución, cancelación operativa y custodia |
| expense_service | Egresos, correcciones y consultas históricas |
| cash_cut_service | Apertura, cierre con conteo, snapshot e historial |
| economic_ledger_service | Atribución, efectivo, reservas y movimientos sin commit propio |
| economic_idempotency_service / economic_write_service | Intención única y límite transaccional HTTP |
| economy_report_service | Agregados SQL y reportes por período/cajero |

Las fuentes nuevas tienen `corte_id` explícito. `egreso.metodo_pago` es obligatorio en nuevas altas; su nulabilidad preserva datos legados. Nuevas tablas: `movimiento_economico`, `constancia_devolucion`, `solicitud_economica`. Los movimientos atribuyen dinero/custodia; no se vuelven a sumar como ingresos comerciales globales.

Triggers impiden UPDATE/DELETE de movimientos y constancias, reemplazar resultados idempotentes y modificar cierres controlados. Titular, fondo y apertura del corte controlado son inmutables. Estas protecciones no certifican inviolabilidad frente al propietario del esquema o superusuario.

## Flujos empresariales

1. CAJA necesita corte propio, abierto y controlado para todos los cobros, incluidos electrónicos. ADMIN opera globalmente sin atribuirse un corte ajeno.
2. Se bloquean corte y recursos antes de consultar disponibilidad o escribir. Fuente, ledger, comprobante, auditoría, notificación e idempotencia se confirman conjuntamente; un fallo revierte todo.
3. Reembolso y cancelación son independientes. El reembolso no cambia estado, inventario ni comprobante original. La cancelación revierte la operación y su comprobante una sola vez; no devuelve dinero automáticamente.
4. Se permiten reembolsos parciales sucesivos, incluso tras cancelar, hasta el máximo histórico menos devoluciones efectivas. No se implementa devolución parcial de unidades físicas.
5. CAJA solo cancela/reembolsa fuentes propias de su corte activo. ADMIN puede operar sobre históricos y otros usuarios.
6. Pago Bs 500 y devolución Bs 200 acreditan Bs 300; pedido Bs 1.000 queda con deuda Bs 700. Cobro bruto permanece Bs 500.
7. Cancelar pedido conserva pagos y comprobantes, deja deuda exigible cero y expone cobrado neto como devolución pendiente. No crea egreso automático.
8. Se bloquea reembolso de pedido entregado; no se reabre deuda por atajos.
9. Cada reembolso emite constancia interna NO FISCAL inmutable, enlazada a egreso y comprobante original. Una corrección posterior no altera ese documento histórico.

Listados, detalles, reportes e impresión de pedidos/pagos distinguen bruto, devuelto, neto, saldo exigible y obligación pendiente. Los snapshots de comprobantes originales conservan la situación de su emisión.

## Garantías y devolución física

La reserva declara garantía BOB comprometida. Su recepción monetaria es explícita con medio real, única por salida y por el importe configurado; no se presume cobrada al reservar.

Devolver el vestido conserva los roles operativos y no paga dinero. La devolución de garantía es otra acción, antes o después de la devolución física, con medio real y saldo verificado. Retención exige ADMIN y motivo: permanece identificada/reservada y pendiente de liquidación, sin ingreso comercial automático.

Una devolución financiada externamente por ADMIN libera la obligación/reserva del corte abierto de origen sin retirar ficticiamente sus billetes. Si está cerrado, el snapshot no cambia.

La numeración de salidas es histórica, positiva y monotónica. El máximo empresarial se controla con usos válidos; una salida anulada no consume artificialmente el cupo por su número histórico.

## Egresos y correcciones

Nuevos fondos, egresos, reembolsos y garantías utilizan BOB. CAJA no puede financiar salida de efectivo BOB con QR, otra moneda o garantías reservadas. Cada egreso declara medio real.

CAJA solo corrige egresos propios del corte abierto declarando que el dinero nunca salió; se registra compensación atribuida y el egreso queda anulado. Restitución real o corrección histórica exige ADMIN y medio real: ajuste vinculado en fecha actual, sin reescribir egreso original ni cierre previo y sin reversión automática de stock/estado.

Las filas exponen importe original, ajuste y salida neta. El reporte por fechas ubica el ajuste en su fecha efectiva; el listado histórico muestra el saldo corregido actual del egreso. Son alcances temporales distintos. Un egreso legado sin método verificable requiere revisión manual; no se infiere su medio.

## Cortes y cierres

ADMIN abre para cajero habilitado; fondo cero permitido. No se añaden anticipos dentro del corte en esta versión. PostgreSQL garantiza un corte abierto por cajero.

Cierre bloquea corte, calcula cifras y exige efectivo recibido para cada moneda física esperada, incluido BOB cero. Diferencias requieren `cerrado_observado` y explicación. No hay conciliación electrónica completa.

El snapshot conserva cifras, agrupaciones, egresos, efectivo esperado/recibido y diferencias. Consultas posteriores lo leen sin recálculo histórico. CAJA ve sus cifras cerradas sin notas internas de ADMIN ni otros cajeros. ADMIN puede consultar historial de un usuario que cambió de rol.

## Consultas, fechas, precisión y UI

- Decimal y HALF_UP, dinero de dos decimales, tasa histórica de cuatro; nuevas capturas rechazan exceso de escala, NaN e infinito.
- Cobros extranjeros conservan original y tasa; reembolsos BOB contra máximo histórico, sin recotización.
- Fechas calendario America/La_Paz → límites UTC; fin exclusivo del día siguiente. Rango invertido: 422.
- Enums comparados con valor válido; funciones de texto usan cast explícito. Origen desconocido: 422.
- Ingresos, egresos, cortes e historial propio: páginas por defecto 25, máximo 100. Agregados oficiales corresponden al filtro completo, no a la página.
- Filtro exclusivo de ingresos (fuente/moneda/medio): resultado o flujo neto `null`, `comparable=false` y explicación. No se resta gasto global para inventar rentabilidad de una selección.
- Exportaciones conservan alcance, autorización y explicación. UI muestra NO COMPARABLE en lugar de Bs 0.
- UI cancela consultas obsoletas, espera 300 ms al filtrar y bloquea doble envío. Claves de intención en memoria ante respuesta incierta; sin credenciales en storage.

## Concurrencia e idempotencia

Orden: idempotencia → corte → padre/artículo → origen → auxiliares. Pedido antes de pago; artículo antes de configuración/salida de flete. Entradas y otros escritores de stock compartido también bloquean/refrescan artículo antes de escribir.

Idempotency-Key obligatoria en escrituras económicas actualizadas. Misma cuenta/operación/clave/payload devuelve resultado confirmado. Misma clave con otro payload: 409. Resultado y efectos se confirman en una transacción; fallo no deja éxito registrado. Autenticación/permisos se comprueban antes de reintentar.

## Históricos y límites

Cortes existentes quedan `control_version=0`; no se certifican métodos ni cierres retroactivamente. Corte legado abierto requiere cierre explícito con observación antes de movimientos nuevos. No se atribuyen automáticamente ingresos antiguos a cortes controlados ni se reparan anulaciones sin devoluciones reales.

Pendientes fuera de alcance: utilidad contable integral, conciliación electrónica, anticipos adicionales, liquidación final de garantías retenidas, devolución de pedidos entregados y mercancía parcial. Los listados tradicionales de pedidos/pagos conservan consultas financieras por registro; medir volumen y optimizar por lotes en una tarea posterior. No se acredita prueba de carga ni E2E visual completo.

Pruebas persistentes solo en bab_vdos_testing:55432 con directorio/usuarios propios. La promoción y migración empresarial de esta entrega se ejecutaron con autorización el 19/10/2026; ver evidencia en el procedimiento enlazado. Futuras operaciones sensibles conservan sus requisitos de autorización.
