# SPEC-TC-02 — Sincronización automática USD/BOB

Fecha: 04/11/2026. Implementación sobre TC-01/revisión `20261104_0023`, sin
migraciones ni tablas/columnas nuevas. Desarrollo directo en el ERP Windows
autorizado. **Desplegada y activa desde el 04/11/2026 a las 23:26 Bolivia**, con
fecha inicial fija `2026-11-04` y primera consulta oficial exitosa.

## Decisiones confirmadas

- Solo USD/BOB, identificado por código USD. BOB y las demás monedas conservan
  su operación actual; los snapshots comerciales no se recotizan.
- Inicio fijo el día de activación, respaldado en configuración; no se cambia
  con reinicios. No hay carga inicial real del mes anterior en esta etapa.
- Hoy tiene prioridad. Recuperación cronológica desde el inicio: inactiva y con
  una fila por fecha verificada, aunque los valores coincidan.
- Una fecha histórica fallida se omite hasta el día siguiente. Tras la espera
  correspondiente pueden continuar otras fechas, dentro del presupuesto diario.
- Alerta reforzada por tres fechas calendario cerradas consecutivas sin
  resultado oficial; un éxito de hoy cierra el episodio operativo, aunque quede
  recuperación pendiente. El contador de fechas pendientes se muestra separado.
- Autorización explícita recibida para registrar y activar la tarea empresarial
  después de superar las pruebas. Funciona con la sesión Windows iniciada,
  también bloqueada, sin navegador y sin guardar contraseñas Windows.

## Contrato del proveedor comprobado

Se realizaron tres GET públicos de solo lectura desde el venv Windows, sin BD:
principal, histórico 2026-11-04 e histórico 2026-11-03. Todos respondieron 200 JSON.
El principal y el histórico del 04/11 entregaron `usd_bob: "12.06"`, BOB y
`vigencia_usd: "VIGENCIA: MIÉRCOLES 4 DE NOVIEMBRE DE 2026"`. El 03/11 entregó
`"12.09"` con intervalo oficial del sábado 31/10 al martes 03/11.

Campos observados: `ok`, `datos`, `error`, `timestamp`; dentro de datos,
`usd_bob`, `moneda_base`, `fuente`, `fuente_usd`, `url_fuente`, `vigencia_usd`,
`fecha_corte_usd`, `fecha_actualizacion` y campos UFV no utilizados.
La consulta primaria única es `/ExchangeRate/history/YYYY-MM-DD`; no se llama al
principal para corroborar cada intento. Referencia pública:
[factura.bo](https://api.factura.bo/tipo-de-cambio).

Se exige `ok=true`, BOB, fuente Banco Central de Bolivia, `fuente_usd=tco_publico`
y URL HTTPS BCB observada. Se interpreta la vigencia española, se comprueba el
día de semana y que la fecha objetivo esté dentro de su intervalo. No se toma
fecha de actualización, corte, UFV, respuesta HTTP o ruta como prueba de vigencia.
Un cambio de formato no reconocido falla de forma conservadora.

El valor se parsea con Decimal y conserva NUMERIC(12,4), positivo/finito, sin
redondeo implícito ni umbral porcentual. Una variación grande verificada es válida.
La atribución es BCB vía factura.bo; la aplicación no establece conexión directa
al BCB ni certifica criptográficamente la autenticidad del contenido republicado.

HTTPS verificado, sin redirecciones, sin reintentos HTTP internos, máximo 64 KiB,
plazo total configurable de hasta 30 segundos. HTTP 429/5xx/3xx → ERROR_API;
DNS/TLS/timeout/conexión → ERROR_CONEXION; JSON/valor/contrato inválido →
ERROR_DATOS; fecha ausente/incompatible → ERROR_VIGENCIA. No se guardan cuerpos
HTTP ni diagnósticos sensibles, ni se afirma «no hay internet» por un timeout.

## Calendario, concurrencia y recuperación

El entrypoint `backend/scripts/run_exchange_rate_sync.py` ejecuta un ciclo
acotado. Un bloqueo asesor PostgreSQL de sesión mantiene un único trabajador
lógico, con verificación de conexión/PID. La transacción de moneda de TC-01 se
usa únicamente al reservar/finalizar; no se mantiene durante la llamada HTTP.

Calendario fijo America/La_Paz: primera consulta a las 05:00; siguiente consulta
tras un fallo no antes de una hora. Antes de las 05:00 no se consulta. El
presupuesto diario es diez reservas/solicitudes para hoy y recuperación juntas.
Al agotarse, se espera al siguiente día desde las 05:00. Las horas apagadas no
generan intentos. Un reinicio después de las 05:00 ejecuta lo elegible sin
simular las horas perdidas. Las reservas se cuentan por día real de ejecución,
no por fecha objetivo, y los errores históricos no provocan bucles ilimitados.

INICIADO se confirma antes de salir a la red. Si el proceso cae, la reserva
conserva su ordinal: tras 120 segundos se reconcilia ERROR_EJECUCION y se espera
una hora antes de consultar. Si no se puede saber si la llamada salió, no se
devuelve presupuesto. Una reserva que cruza medianoche antes del envío termina
sin emitir la llamada. La garantía es a lo sumo diez HTTP; puede haber menos
HTTP que reservas conservadoras ante interrupciones.

Cada éxito confirma cotización y resultado asociados de forma atómica. Los días
anteriores siempre quedan inactivos. Un valor MANUAL posterior al éxito diario
permanece activo hasta la siguiente consulta diaria válida; no se repite la de
hoy para desplazarlo. Fallas mantienen el último activo; sin activo USD se exige
intervención ADMIN para operaciones USD mientras la consulta intenta repararlo.
Los bloqueos de backup suspenden nuevas consultas y la tarea no depende de Uvicorn.

## API y autorización

Todas las rutas son GET bajo `/api/v1/monedas/tipos-cambio/sincronizacion`:

| Ruta | Permiso | Contenido |
|---|---|---|
| `/estado` | `exchange_rates:list` | Estado funcional, activo/fuente, última fecha oficial, presupuesto, próxima ejecución y recuperación |
| `/registros` | ADMIN + `exchange_rates_sync:list` | Lista paginada, por defecto 25, máximo 100 |
| `/registros/{id}` | ADMIN + `exchange_rates_sync:view` | Detalle de solo lectura con mensaje derivado |

Filtros de registros: `date_from`, `date_to` (objetivo), `execution_from`,
`execution_to` (día de ejecución Bolivia), `estado`, `proveedor`, `page`,
`page_size`. Orden ejecución e ID descendente. Rangos invertidos producen 422.
Los valores se devuelven como cadenas decimales. No hay endpoint que fuerce
sincronización, edición/borrado de registros técnicos ni cuerpo HTTP expuesto.

La UI conserva los contratos manuales TC-01 y agrega estado USD y pantalla
`/app/monedas/tipos-cambio/registros` exclusiva ADMIN. El polling de estado cada
60 segundos ocurre con pantalla visible, al enfocar y después de guardar una
manual. Los GET nunca llaman al proveedor. Detalles por `record_id` y `rate_id`
permiten navegar desde notificaciones. La serie oficial separada en reportes
usa fecha objetivo y diferencia procedencia; la serie operativa conserva registro ERP.

## Notificaciones propias de la función

Tipos TC_SYNC_PRIMER_ERROR, TC_SYNC_AGOTADO, TC_SYNC_PROLONGADO y TC_SYNC_EXITOSO
en el módulo MONEDAS, por medio del sistema de Notificaciones existente.
Solo destinatarios ADMIN activos con los permisos específicos. Se filtran
también las lecturas de avisos antiguos/resueltos al cambiar a un rol inferior,
incluidos listado, detalle, resumen y escritorio. No se añaden correos.

Deduplicación por destinatario/tipo/referencia estable, considerando filas
resueltas. Primer error/día referencia el primer intento fallido; agotamiento,
el décimo; episodio, su primer registro; éxito, su cotización. Un éxito de
recuperación no se anuncia como cotización actual. La recuperación operativa
se integra en el aviso de éxito, evitando mensajes equivalentes duplicados.
Los avisos faltantes se reconstruyen de resultados durables tras reinicio.

Los cierres son automáticos y no generan auditoría funcional TC. Se conserva
la protección transversal existente que audita accesos HTTP denegados; eso no
es una integración de cotizaciones o intentos con Logs/Auditoría.

## Configuración y operación Windows

Variables: `EXCHANGE_RATE_SYNC_ENABLED` (false por defecto),
`EXCHANGE_RATE_SYNC_START_DATE` (fecha ISO estable),
`EXCHANGE_RATE_SYNC_HTTP_TIMEOUT_SECONDS=30`,
`EXCHANGE_RATE_SYNC_RECONCILE_SECONDS=120`. La zona, hora inicial, hora de espera
y límite diez no se amplían mediante configuración accidental. La fecha inicial
debe incluirse en respaldos de configuración y mantenerse al trasladar el ERP.

La tarea `BAB_VDOS_USD_BOB_SYNC` usa pythonw.exe del venv, `-B`, directorio backend,
usuario Windows actual/InteractiveToken y privilegio Limited. Se dispara al
iniciar sesión y comprueba elegibilidad cada minuto indefinidamente; IgnoreNew
evita instancias simultáneas en Windows y PostgreSQL refuerza la exclusión.
El PC apagado o la sesión cerrada posponen ejecución hasta el siguiente inicio;
bloquear pantalla no cierra sesión. No se instala servicio ni se guardan claves.

Comandos desde raíz con PowerShell nativo:

```powershell
# Solo lectura, sin HTTP externo ni notificaciones nuevas
.\backend\venv\Scripts\python.exe -B .\backend\scripts\run_exchange_rate_sync.py --inspect

# Inspección de definición; no registra ni activa
.\backend\scripts\install_exchange_rate_sync_task.ps1

# Soporte: detener próximos disparos de esta tarea identificada
.\backend\scripts\install_exchange_rate_sync_task.ps1 -Disable
```

El comando sin `--inspect` usa BD configurada y puede consultar/escribir: no es
un chequeo inocuo. Logs técnicos rotativos, sin secretos, quedan en el directorio
privado `%LOCALAPPDATA%\BAB_VDOS\tc02-runtime`. El calendario de la función
siempre usa Bolivia aun si cambia la zona Windows. No borrar INICIADO ni
reiniciar ordinales manualmente para forzar consultas.

Despliegue: `deploy_exchange_rate_sync.py` inspecciona sin cambios por defecto;
`--apply --backend-pid <PID_VERIFICADO>` comprueba 0023, USD habilitado, LENY
inactivo y exclusión, pausa solo el backend original, verifica respaldo privado
de BD+originales y copia protegida de configuración, fija fecha/activa configuración,
comprueba conservación de filas/esquema, reinicia y valida salud/protección HTTP.
Registra entonces la tarea autorizada; no ejecuta migraciones, seeds o restauraciones.

Reversión operativa: deshabilitar la tarea y poner enabled=false, conservando
fecha inicial; reiniciar el backend para reflejar configuración. Conservar tasas,
registros y avisos como evidencia. No ejecutar downgrade ni eliminar historial;
las tasas manuales pueden continuar por los endpoints existentes.

## Pruebas y evidencia

- Suite backend completa: 1273 aprobadas, 1 omitida; aviso preexistente pypdf.
- Regresión PostgreSQL completa: 275 aprobadas, con proveedor/reloj simulados y
  guardas de conexión que rechazan la base empresarial.
- Frontend completo: 208 aprobadas en 26 archivos; lint correcto.
- Build Vite correcto hacia directorio temporal; permanece el aviso previo de
  bundle grande (aproximadamente 2,72 MB antes de gzip).
- Pruebas focales posteriores de cliente/calendario/notificaciones: 60 aprobadas.
- Casos finales de cruce de medianoche y pérdida de coordinación, junto con
  integración de sincronización/notificaciones: 24 pruebas PostgreSQL aprobadas.

Cobertura funcional: respuesta fechada, intervalos, JSON/valor inválido,
timeout/HTTP/redirect/tamaño, máximo diez, espera/reinicio/medianoche, prioridad
hoy, recuperación acotada/inactiva, manual posterior, idempotencia, ADMIN,
deduplicación/resolución/exADMIN, pérdida de lease y preservación de snapshots
comerciales mediante regresión TC-01. No se usaron cuentas empresariales para tests.

## Resultado empresarial verificado

La tarea se registró con InteractiveToken/Limited/IgnoreNew. Primera ejecución
real a las 23:26:48; resultado de tarea 0. El intento 1 terminó EXITOSO/HTTP200,
con cotización ID5 **12.0600 BOB por USD**, fuente BCB_VIA_FACTURA_BO y fecha
oficial 04/11/2026. El registro anterior USD quedó inactivo sin cambiar su valor.
Los siguientes disparos mantuvieron un solo intento del día. Próxima consulta
externa elegible: 05/11/2026 a las 05:00 Bolivia.

Se generaron dos copias del aviso de éxito, ambas para ADMIN; no para otros
roles. Backend y frontend original responden 200. El frontend estaba detenido
y se inició su Vite existente en segundo plano en `http://localhost:5173`, sin
instalar dependencias. El backend sigue sin autoreload; futuros cambios Python
requieren reinicio controlado. No se iniciaron sesiones empresariales para pruebas.

Respaldo privado previo: BD + originales documentales, 5.107.076 bytes, hash y
lectura offline verificados. No se restauró. Se compararon las filas anteriores
de 62 tablas antes de activar. Después de la consulta real, se comparó contenido
COPY del respaldo con la base en solo lectura: ventas17, pagos7, fletes4,
comprobantes25, monedas3, usuarios6, cuentas6 y roles6 permanecieron idénticos.
Las cuatro tasas anteriores conservan contenido, excluyendo únicamente el
cambio esperado de activo al entrar la nueva tasa. No hay duplicados activos.

La comparación se hace sin restaurar y sin mostrar filas sensibles; usa la zona
del servidor original para comparar representaciones de timestamps.
Evidencia: [despliegue TC-02](evidencias/tc02_deployment.json).
`verify_exchange_rate_sync.py` permite repetir esa verificación de primera
ejecución con manifiesto privado explícito; no es un monitor permanente y sus
expectativas dejan de aplicar después de nuevos días u operaciones empresariales.
