# SPEC-TC-01 — Implementación y evidencia

Fecha: 04/11/2026. Revisión Alembic: `20261104_0023`, posterior a `20261103_0022`.
Implementación directa en el repositorio Windows autorizado; pruebas PostgreSQL
en la instancia desechable `bab_vdos_testing:55432` del mismo proyecto.
El propietario autorizó aplicar esta revisión al ERP original después de las
verificaciones y del respaldo. **Desplegada en `bellaarte_db:5432` el 04/11/2026
a las 22:19 America/La_Paz**, con backend reiniciado y salud 200.

## Decisiones y diferencias aprobadas

1. `moneda` no cambia de estructura. Solo USD, identificado por código, admite
   persistencia automática. BOB permanece base y referencia 1.
2. Se reutiliza el historial `tipo_cambio_moneda`, conservando `NUMERIC(12,4)` y
   las siete columnas anteriores; se agregan únicamente origen, fuente y consulta.
3. La inspección encontró `usu_id NOT NULL`. Se aprobó hacerlo nullable sin
   cambiar su tipo ni FK: CHECK exige autor para MANUAL y NULL para AUTOMATICO.
   No se crea cuenta técnica ni se atribuyen operaciones automáticas a personas.
4. El índice parcial de activo y el CHECK positivo ya existían: se conservan.
   Se agrega protección contra `numeric NaN`, que PostgreSQL considera mayor
   que cero, además de CHECK de origen, autoría y fuente automática.
5. Se aprobó excluir las operaciones futuras de esta tabla de la auditoría
   general: se retira únicamente su trigger y llamadas `EXCHANGE_RATE_*`.
   No se elimina auditoría antigua, la función general ni otros triggers.
6. El downgrade se niega si perdería procedencia, autoría automática o registros
   técnicos. En una base desechable sin esos datos se comprobó downgrade/upgrade
   conservando las filas anteriores. No se ejecuta downgrade empresarial.

## Modelo e integridad

La nueva tabla tiene exactamente estas diez columnas:
`tcs_id`, `mon_id`, `tcm_id`, `tcs_fecha_objetivo`, `tcs_num_intento`,
`tcs_fec_intento`, `tcs_estado`, `tcs_codigo_http`, `tcs_proximo_intento`,
`tcs_proveedor`. PK bigint identity; FK moneda y FK compuesta cotización/moneda
con RESTRICT, para impedir asociar el resultado a una cotización de otra moneda.

Estados: INICIADO, EXITOSO, ERROR_CONEXION, ERROR_API, ERROR_DATOS,
ERROR_VIGENCIA, ERROR_EJECUCION y CARGA_HISTORICA. Un éxito/carga exige cotización;
los demás estados no la admiten. EXITOSO exige HTTP 2xx. Carga histórica usa 0;
los intentos automáticos usan 1–10 y solo los errores admiten próximo intento.

El índice único de expresión por moneda/proveedor/ordinal usa
`(tcs_fec_intento AT TIME ZONE 'America/La_Paz')::date`; su creación y rechazo
de duplicados se comprobaron en PostgreSQL 17. La fecha objetivo puede diferir
del día del intento. Existen unicidades independientes para EXITOSO y
CARGA_HISTORICA por fecha objetivo/moneda/proveedor. Tasas iguales en días
distintos se conservan. Índices: historial de tasas, historial técnico y próximos
intentos no nulos; no se agregan índices especulativos de origen/fuente.

## Servicios y fronteras transaccionales

`exchange_rate_history_service.insert_rate` bloquea la moneda con FOR UPDATE,
desactiva únicamente sus activos e inserta la nueva tasa; hace flush, sin commit.
El servicio coordinador confirma o revierte la operación completa. Manual y
automática usan la misma exclusión; el índice parcial refuerza la integridad.

`begin_attempt` confirma INICIADO antes de cualquier futura consulta.
`finish_success` confirma tasa y resultado asociados en una sola transacción;
validaciones fallidas no dejan tasa parcial. Una captura para fecha anterior al
día local actual siempre queda inactiva. `finish_failure` finaliza únicamente
intentos propios en estados permitidos, incluso si luego se deshabilitó USD.
La reconciliación y la consulta externa serán responsabilidad de TC-02.

Los contratos humanos y cambios mínimos de interfaz se documentan en
[módulo de tipos de cambio](MODULO_TIPO_CAMBIO_MONEDA.md). PATCH con valor
distinto devuelve nueva fila activa; los consumidores deben usar el ID devuelto.
Las respuestas Decimal son cadenas; la UI existente ya está adaptada.

Se corrigió además el reporte que intentaba obtener una sola fila de una
consulta ordenada sin LIMIT, fallando cuando existían varias cotizaciones.
Ahora distingue último registro de activo y mantiene el valor decimal textual.

## Importación histórica preparada, no ejecutada

`backend/scripts/import_exchange_rate_history.py` valida localmente un CSV con
cabeceras exactas `fecha_objetivo,valor_bob` y manifiesto JSON independiente.
Por defecto es dry-run, sin cargar configuración empresarial ni conectar a BD.

El manifiesto requiere `verified: true`, `official_source`, `verified_by`,
`verified_at` con zona, `period_start`, `period_end` y `dataset_sha256` coincidente
con los bytes del CSV. El período debe ser un mes calendario completo, con una
cotización verificada por cada día, sin huecos, duplicados ni fechas futuras.
Si faltan datos oficiales diarios, se detiene; no inventa ni arrastra valores.
La verificación humana y el dataset se conservan fuera de la BD. El programa
valida el manifiesto; no certifica por sí mismo que el contenido provenga del BCB.

Solo `--apply` permite escritura, con destino explícito y revisión 0023. El
destino empresarial requiere además `--approve-business-import` y autorización
específica del dataset. No lee .env como fallback ni migra automáticamente.
El lote se confirma completo: cada fila crea AUTO/BCB_CARGA_INICIAL inactiva,
usuario y consulta nulos, registro CARGA_HISTORICA/intento 0 y fecha oficial.
Repetir exactamente el lote omite filas; un conflicto no sobrescribe y revierte.

No existe un dataset oficial validado entregado en esta tarea; no se cargaron
cotizaciones reales. Las pruebas usan datos sintéticos identificados como tales.

## Verificaciones ejecutadas

- Suite base backend antes del último ajuste de mes completo: 1215 aprobadas,
  1 omitida; aviso preexistente de deprecación de pypdf.
- Suite de integración completa: 252 aprobadas, incluidos 18 casos TC-01.
- Después del ajuste: 41 pruebas de contratos/helpers TC-01 y 19 de integración
  TC-01 aprobadas, incluyendo concurrencia MANUAL/MANUAL y MANUAL/AUTOMATICO.
- Frontend completo: 193 pruebas aprobadas en 25 archivos; ESLint correcto.
- Build Vite correcto, salida temporal sin reemplazar dist; permanece el aviso
  previo de tamaño de bundle (aproximadamente 2,7 MB antes de gzip).
- Revisión independiente sin cambios ni conexiones a datos empresariales;
  observación sobre meses incompletos corregida y comprobada.

La integración comprueba columnas/tipos, FK de moneda, unicidad de activo y
ordinal, medianoche boliviana, fallos/rollback, permisos HTTP reales, bloqueo
AUTO, nuevo ID en edición, carga idempotente/inactiva y migración reversible
con guardas. Se registraron ventas, pagos y fletes sintéticos antes y después
de una nueva tasa: sus snapshots y comprobantes conservaron la tasa original.

## Despliegue y continuidad

`backend/scripts/deploy_exchange_rate_history.py` es read-only por defecto.
`--apply` exige 0022, ausencia de duplicados/valores inválidos, LENY inactivo y
PID verificado del backend original. Coordina bloqueo, detiene ese proceso,
genera respaldo privado PostgreSQL + originales documentales y verifica hash,
manifiesto y lectura offline; esta comprobación no equivale a restauración.

Después de migrar compara huellas de filas previas de todas las tablas public/leny,
estructura de moneda y columnas originales. Exige clasificación heredada MANUAL
y cero registros técnicos. Reinicia el backend y comprueba health. No ejecuta
seeds, importaciones, restauraciones ni correcciones silenciosas de datos.
Ejecución completada: revisión 0022 → 0023, respaldo privado conjunto de
5.099.429 bytes verificado, huellas de filas previas de 62 tablas sin cambios,
cuatro cotizaciones anteriores preservadas y cero registros técnicos/importados.
La estructura de moneda y los tipos físicos anteriores permanecen intactos;
la única modificación de nulabilidad es la autorizada para `usu_id`.

GET de salud respondió 200; GET de tasas/monedas y POST de tasas sin credenciales
respondieron 401. No se iniciaron sesiones ni se hicieron operaciones comerciales
en la base empresarial para esta verificación. La prueba autenticada de interfaz
con la cuenta del propietario queda a cargo de su sesión habitual; la API con
JWT/Casbin y el formulario Ant Design se probaron con datos sintéticos.

Evidencia sin secretos: [resultado del despliegue](evidencias/tc01_0023_deployment.json).
Respaldo y manifiesto completo permanecen en almacenamiento privado local fuera
de Git. No se practicó restauración empresarial. El script deja Uvicorn en segundo
plano sin autoreload; las siguientes ediciones de backend requieren reinicio
controlado para reflejarse en la instancia activa.

TC-02 queda pendiente: cliente proveedor y vigencia demostrable, fecha estable de
inicio autorizada, jobs, recuperación/reconciliación, reintentos, consulta técnica
ADMIN y notificaciones. La mera presencia de servicios no habilita automatización.
