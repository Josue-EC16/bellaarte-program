# Consolidación de Economía — reporte de implementación

Fecha de implementación: 18/10/2026. Despliegue empresarial autorizado y ejecutado el 19/10/2026, revisión 0016. [Procedimiento](DESPLIEGUE_ECONOMIA.md).

## Resultado

Implementados servicios, modelos/migraciones, API, interfaz, pruebas y documentación para separar ingresos comerciales, efectivo disponible, reembolsos, cancelaciones y garantías. Se conservan arquitectura, políticas y dependencias existentes.

Tras validar la copia aislada, se promovieron los archivos con API/Vite pausados y se aplicaron 0015/0016 a bellaarte_db:5432 con respaldo privado verificado. Las filas y valores previos de 40 tablas se conservaron. Se reanudaron API y frontend; los servicios económicos pasaron consultas reales en READ ONLY. La suite persistente se sigue ejecutando exclusivamente en bab_vdos_testing:55432.

## Problemas corregidos

- Filtro de método sobre enum PostgreSQL: comparación válida/cast explícito, eliminando upper(enum).
- Reembolso antes acoplado a anulación: coordinadores independientes, pagos netos, reembolsos parciales sucesivos y obligaciones pendientes.
- Propiedad de fuentes y corte: control servidor para CAJA, alcance ADMIN y rechazo de corte legado para movimientos nuevos.
- Egresos sin medio: medio real obligatorio y saldo BOB libre sin gastar QR, divisas o garantías reservadas.
- Cierre con estado abierto: contrato lo rechaza; conteo por moneda, explicación de diferencias y snapshot inmutable.
- Histórico cerrado antes oculto/recalculado: cifras propias visibles, cierres controlados congelados, legados no certificados.
- Cantidades monetarias: Decimal, escala explícita y HALF_UP; rechazo de valores no finitos/exceso de precisión.
- Doble envío/reintento: intención idempotente confirmada junto a la transacción; carrera concurrente con la misma clave produce una operación.
- Stock/pagos/reembolsos: bloqueos tempranos antes de decisiones y orden consistente entre recursos compartidos.
- Retiro/deshabilitación de flete repetidos: restitución de stock una sola vez. Numeración histórica no consume artificialmente el máximo de usos.
- Reportes parciales: no calculan un neto ficticio al filtrar solo ingresos; contexto de comparabilidad en JSON/CSV.
- Paginación/agregados: totales SQL del alcance completo y páginas acotadas; consultas obsoletas canceladas y filtros con debounce.
- Constancias: documento no fiscal separado, inmutable y recuperable para impresión, con texto escapado.

La revisión independiente detectó y se corrigieron además: agrupaciones de egresos ajustados distintas del total; reserva no liberada tras devolución ADMIN externa; reportes de pagos todavía brutos; devolución física bloqueada después de pagar garantía; otros escritores de stock que podían sobrescribir una venta concurrente.

## Pruebas ejecutadas

| Verificación | Resultado comprobado |
|---|---|
| Suite base backend, lanzador saneado sin acceso externo | 160 aprobadas |
| Integración PostgreSQL exclusiva, incluidas notificaciones | 70 aprobadas |
| Vitest, seis archivos de prueba | 30 aprobadas |
| ESLint sobre src completo de la copia | Sin errores ni advertencias |
| Vite para navegador, salida temporal | Compilación correcta; advertencia de bundle grande |
| Cadena Alembic de testing | 0014 → 0015 → 0016 aplicada correctamente |

Las 70 de integración incluyen 24 regresiones existentes de notificaciones y 46 casos económicos/contratos persistentes. No son un porcentaje de cobertura. El build usa las dependencias ya instaladas mediante un config temporal exclusivo de la copia; no instala paquetes ni reemplaza dist empresarial.

La primera ejecución encontró fixtures de cliente sin CI y contratos unitarios obsoletos; se completaron datos sintéticos y se actualizaron las pruebas a la separación aprobada, sin deshabilitar validaciones comerciales. Un mock de flete también se adaptó para comprobar bloqueo → notificación → commit. La batería económica utiliza `autoflush=False`, como la aplicación. Se corrigieron lecturas de fondo/ajustes pendientes antes de serializar respuestas idempotentes y se añadieron regresiones HTTP para comprobarlas.

## Matriz de cobertura

| Flujo | Evidencia automatizada actual | Límite / seguimiento |
|---|---|---|
| Venta y stock | Alta real con comprobante; carrera por última unidad; rollback observado externamente | Sin ensayo de carga masiva |
| Inventario compartido | Sesión con artículo obsoleto + venta separada + entrada; saldo final correcto | Medir contención con volumen realista en testing |
| Pagos/saldos | Crédito neto tras devolución; sobrepago concurrente rechazado | Optimizar consultas por lote en listados tradicionales |
| Reembolso | Parciales sucesivos, máximo histórico, origen cancelado, concurrencia y constancias | No mercancía parcial ni pedido entregado |
| Cancelación | Dinero/stock separados; repetición idempotente; pendiente de devolución | No crea devoluciones históricas ficticias |
| Pedido cancelado | Pagos/comprobantes conservados y deuda exigible cero | Liquidación real se registra explícitamente |
| Egresos/ajustes | Medio real, efectivo insuficiente, restitución, filas/agrupaciones/neto coherentes | Legado sin medio exige revisión manual |
| Garantías | Recepción, reserva, devolución, retención; ADMIN externo; devolución física posterior | Retención pendiente no liquidada como ingreso |
| Cortes | Fondo/QR/físico distintos, fondo cero, conteo, cierre legado, diferencias y congelación | Sin conciliación electrónica completa |
| Inmutabilidad | UPDATE/DELETE de ledger/constancia y cambios de cierre rechazados por PostgreSQL | No certifica frente a superusuario |
| Idempotencia | Reintento secuencial y simultáneo: un egreso/ledger/resultado; conflicto de payload | Intención UI en memoria, no sobrevive recarga completa |
| Autorización | JWT/Casbin reales ADMIN/CAJA; recurso ajeno 403; permiso revocado bloquea replay | No auditoría integral de permisos de todo el ERP |
| Reportes | Enum, fechas, paginación, bruto/devuelto/neto y no comparabilidad | Sin benchmark SQL de volumen productivo |
| Frontend | Página de egresos, filtros/paginación, refund sin anular, bloqueo, impresión sin XSS e intención | Sin recorrido E2E visual completo de todos los formularios |
| Notificaciones | 24 regresiones PostgreSQL y suites frontend/backend existentes | Preserva el trabajo previo, sin nueva certificación SMTP externa |

## Integridad del trabajo y archivos

Los archivos funcionales cambiados están enumerados en `../.economy-staging/cambios.json` con hashes de partida/preparados. El diff `../.economy-staging/ECONOMIA_CAMBIOS.patch` incluye exclusivamente diferencias económicas sobre la copia inicial; los cambios previos de notificaciones se preservan. Las modificaciones locales de Skills y RolesPage no se alteraron.

No se ejecutaron seeds, instalaciones, commits ni operaciones comerciales ficticias sobre datos reales. Las únicas migraciones empresariales ejecutadas fueron las autorizadas 0015 y 0016. No se usó WSL. Testing tiene directorio, puerto, usuarios y base exclusivos; el lanzador lo detuvo al finalizar cuando lo inició.

## Activación y límites

La implementación está activa en la API empresarial con el frontend emparejado. La documentación fue actualizada tras el despliegue. Se corrigió en el preflight la referencia del filtro de monedas para utilizar `/api/v1/monedas`, la ruta real existente.

Un corte legado sigue abierto y requiere actuación empresarial de ADMIN: cierre explícito con observación y nueva apertura controlada. El despliegue no decidió conteos, devoluciones ni importes históricos.

No se certifica contabilidad integral, utilidad, conciliación electrónica, rendimiento a escala productiva ni compatibilidad visual E2E completa. El bundle permanece grande. Las pruebas concurrentes dejan evidencia QA_ECON identificada únicamente en testing; no se eluden los triggers para borrarla.
