# LENY Gemini — revalidación de SPEC-02 / SPEC-02.1 con3.1Flash-Lite

Fecha:05/11/2026. Proyecto original `C:\laragon\www\bellaarte-program`. Alcance: únicamente las partes de integración y validación que quedaron bloqueadas/fallaron, con cambio de modelo y cuotas expresamente solicitado. No se inició SPEC-03.

## Resultado y estado efectivo

**Gemini3.1Flash-Lite quedó habilitado en el ERP original**, seleccionable en nuevas conversaciones de LENY. Qwen sigue predeterminado. Se completaron generación real, JSON, adaptador, conversación/seguimiento, recuperación autorizada, síntesis validada, fuentes accesibles, persistencia/historial mediante API normal y cancelación por desconexión. La última consulta se ejecutó **después de la activación persistente y recarga**, con respuesta documental y dos fuentes abiertas con HTTP200.

Esto acredita disponibilidad del recorrido funcional inspeccionado. **No equivale a aceptación humana de calidad, cumplimiento estadístico SPEC-04 ni certificación integral de todos los escenarios negativos.** Las limitaciones de datos sensibles y los casos de ACL/publicaciones no ejercitados con Google se detallan abajo; no se declaran aprobados por inferencia.

| Configuración | Valor final |
|---|---:|
| Modelo | `gemini-3.1-flash-lite` |
| RPM / TPM / RPD |15 /250000 /500|
| Pensamiento |`medium`|
| Entrada / salida |32678 /8192|
| Timeout HTTP / turno |60s /300s|
| `LENY_GEMINI_ENABLED` |`true`|
| `LENY_GEMINI_FREE_TIER_CONFIRMED` |`true`|
| Proveedor predeterminado |`ollama`|

Cuotas y Free Tier se basan en la confirmación del propietario para este modelo/proyecto. No se verificaron mediante una API administrativa ni se activó facturación. No hubo cambio de clave, proyecto, cuenta, SDK o infraestructura. El modelo anterior no se selecciona como fallback. Conversaciones históricas conservan su proveedor/modelo: comenzar una nueva para usar3.1Flash-Lite.

## Inspección, respaldo y cambios mínimos

Se conservaron el árbol de trabajo del propietario, `.env`, la migración0024 aplicada anteriormente y la arquitectura multiproveedor. Sin ramas, worktrees, proyecto paralelo, nueva migración ni reindexación.

Antes de editar se respaldaron las fuentes afectadas con SHA256 en `%LOCALAPPDATA%\BAB_VDOS\leny-gemini-resume31`, subdirectorio indicado por `active.txt`. El archivo privado `.env` no se copió: se registraron huellas y valores **no secretos** anteriores/posteriores de las variables modificadas. La clave no se imprimió ni se sustituyó.

| Archivos | Cambio |
|---|---|
| `backend/app/core/config.py`, `backend/.env.example`, `backend/.env` | Modelo3.1, límites15/250000/500; activación explícita tras validación |
| `backend/app/services/leny_gemini.py` | Esquema nativo de selección coherente y medición del esquema realmente enviado |
| `backend/app/services/leny_rag_synthesis.py` | Reutilizar variantes existentes por fuente para Gemini, preservando soporte del mismo índice |
| `backend/app/services/leny_service.py` | Diagnóstico por categorías fijas del rechazo de selección, sin payload |
| `backend/scripts/diagnose_leny_gemini_spec021.py` | Admitir los modelos expresamente autorizados en la secuencia A/B/C |
| `backend/scripts/test_leny_gemini_schema.py`, `.ps1` | Verificar RPM15, TPM250000, RPD500 en SQL aislado; evidencia separada |
| `backend/scripts/run_leny_gemini_authenticated_review.py` | Comprobación fija de creación, inmutabilidad, historial y cancelación con login normal |
| `backend/scripts/verify_leny_gemini_resume31.py` | Lectura de correspondencia NDJSON/PostgreSQL y manifiesto sin textos privados |
| Pruebas `test_leny_gemini_provider.py`, `test_leny_gemini_diagnostics.py` | Cuotas, esquema nativo, conteo y soportes combinados |
| Informes SPEC-02/02.1 | Nota de actualización enlazada; resultados históricos conservados |

El servicio de síntesis se respaldó antes de tocarlo. El parche inverso de fuentes está preparado y su comprobación pasó; no se aplicó. No se usó reset/clean ni restauración general desde HEAD.

## Secuencia A/B/C: anteriores bloqueos externos

Se ejecutó la secuencia progresiva con controles durables de cuota y lease común. No se avanzó a JSON/adaptador antes del éxito previo de esta ejecución.

```powershell
& backend\venv\Scripts\python.exe -B backend\scripts\diagnose_leny_gemini_spec021.py --run leny_gemini_spec021_resume31 --step A
& backend\venv\Scripts\python.exe -B backend\scripts\diagnose_leny_gemini_spec021.py --run leny_gemini_spec021_resume31 --step B
& backend\venv\Scripts\python.exe -B backend\scripts\diagnose_leny_gemini_spec021.py --run leny_gemini_spec021_resume31 --step C
```

| Prueba | Resultado | Tiempo total |
|---|---|---:|
| A: metadatos + SDK mínimo directo | Generación útil;2HTTP |2,109s|
| B: JSON mínimo SDK directo | JSON válido;1HTTP |5,031s|
| C: JSON mediante GeminiProvider | JSON válido, parámetros objetivo;1HTTP |2,187s|

A/B utilizaron salida temporal1024 y omitieron el parámetro de pensamiento para aislar SDK; C y el ERP utilizaron `medium` y8192. No se trasladó ese ajuste diagnóstico a la configuración habitual. Se mantuvo Developer API`v1beta`, SDK2.33.0 y un intento del SDK. Solo el adaptador admite un reintento503; no hay cambio automático de modelo.

Los503/504 históricos de3.8/3.5no se reetiquetan como una falla RAG corregida:3.1sí atendió estas solicitudes. No se certifica la disponibilidad futura de Google ni una causa interna del proveedor anterior.

## Diagnóstico y correcciones del contrato nativo

El primer seguimiento autenticado falló con `LENY_RAG_REVIEW_INVALID`. Una reproducción posterior terminó en `rag_synthesis_unverified`, categoría de referencia. Se añadió diagnóstico limitado a mensajes de error del servidor mapeados a categorías fijas; nunca se imprimieron JSON, preguntas, pasajes o errores externos completos.

Se confirmó el caso **`scope_references`**: el modelo devolvía ámbito distinto de`matched` o evidencia ausente junto con referencias, combinación que el servidor rechaza correctamente. Se corrigió **el esquema enviado a Gemini**, expresando mediante`anyOf` las mismas combinaciones que ya admite el validador. No se borran referencias de una salida incoherente ni se la transforma en una afirmación aceptada.

Para síntesis se reutilizaron las ramas por fuente que `schema_for` ya construía. Solo Gemini las utiliza también en modo de soporte vinculado; Qwen conserva el esquema compacto. Las ramas admiten encabezado/cuerpo y varios pasajes del **mismo índice publicado**, y excluyen pasajes de otro índice. El validador Python continúa siendo obligatorio. No se relajaron ACL, referencias, soporte, cifras, condiciones, prompts ni validadores semánticos.

La revisión independiente detectó dos límites en un intento intermedio: contar el esquema original antes de expandirlo y restringir soportes solo por prefijo de fuente. Ambos se corrigieron antes de la activación: la medición/reserva usa el esquema nativo transformado y los soportes se derivan del contrato original de índices, conservando contexto de sección. Hay pruebas específicas de ambas propiedades. Las variantes intermedias fallidas se conservaron en la evidencia.

No hubo nuevos jueces LLM, bucles de reparación, librerías de orquestación ni estrategia de ranking. Un JSON nativamente coherente reduce errores de contrato; no demuestra respaldo semántico por sí solo.

## Chat D: comparación antes/después

Se usaron los mismos dos turnos en conversaciones nuevas: explicación general de procedimiento y resumen de lo anterior. Cada seguimiento compartió la conversación del primer turno. No se reintentaron mensajes hasta ocultar resultados: cada intento quedó identificado por su variante y request.

| Variante | Primer turno | Seguimiento | Interpretación |
|---|---|---|---|
| D inicial |`answered`,11,937s|Error de selección,9,891s| Falla conservada |
| D diagnóstico |`answered`,10,047s|Aclaración por síntesis no verificada,15,656s| No se contó como éxito documental |
| D enlace inicial |`answered`,11,281s|Error de selección,9,750s| Confirmó `scope_references` |
| D esquema nativo final |`answered`,8,937s|`answered`,14,047s| Dos fuentes accesibles en cada turno |

Solo después de los dos turnos finales completados sin rechazo de estructura/soporte se avanzó a la tanda E. La conversación no se considera comprendida semánticamente solo por`answered`: los textos están disponibles para revisión humana.

## RAG E: resultados individuales actuales

Se utilizó autenticación normal del propietario mediante consola local. Contraseña y token permanecieron en memoria; el evaluador consumió todos los eventos NDJSON y verificó accesos a fuentes con GET normales. Las respuestas/documentos no se incorporaron al informe compartible.

| Caso | Resultado | Alcance emitido | Fuentes abiertas200 | Tiempo |
|---|---|---|---:|---:|
| Título explícito del manual autorizado |`answered`|Documentado|2|7,500s|
| Procedimiento can-can |`answered`|Parcial|2|11,156s|
| Seguimiento «¿Y después?» |`answered`|Parcial|1|9,422s|
| Responsabilidades de encargada |`answered`|Parcial|4|9,234s|
| Especialidad sin evidencia suficiente |`answered`|General|0|9,922s|
| Ejemplo adaptable para iniciar manual |`answered`|Documentado|1|8,750s|
| Correo personal ficticio en pregunta |HTTP422|Bloqueado|0|0,016s|
| Cambio de inventario/registro de venta |`refused`|Capacidad no disponible|0|0,094s|

Los dos bloqueos realizaron **cero llamadas Google**. Una respuesta general no se contabiliza como éxito documental. El ejemplo adaptable utilizó documentación y así lo indicó el servidor; su valor editorial/normativo requiere revisión del texto, no se presume por la publicación.

La especialidad ausente emitió alcance`general` sin fuentes; no se presenta como una política interna. Procedimiento, responsabilidades y seguimiento quedaron marcados parciales: no se certifica completitud del manual o del cargo. Los pasajes y condiciones deben ser revisados por el propietario.

## Persistencia, selector, cancelación y Qwen

El comprobador F, con sesión ERP normal, pasó **12comprobaciones**: estado/modelo disponible, creación Gemini, rechazo422 de proveedor por mensaje, cancelación real, proveedor persistido tras desconexión, seis recuperaciones de historial y creación Qwen predeterminada.

La cancelación cerró el flujo tras`start` y4s de espera: el asistente quedó **`interrupted`**,4,172s totales, sin una generación huérfana. Esto prueba la desconexión ASGI y persistencia; no demuestra que Google pueda anular cómputo remoto ya enviado. Los reintentos nunca convierten el turno a Qwen.

Los historiales se recuperaron por GET normales y se compararon localmente con los textos recibidos por NDJSON, sin imprimirlos. Coincidieron las respuestas y las fuentes guardadas. Las conversaciones conservan`gemini`/`gemini-3.1-flash-lite` en PostgreSQL; la selección no se envía por mensaje.

La compatibilidad Qwen se comprobó con una consulta documental normal: **`answered / partial`**,54,062s, tres fuentes abiertas200. Conserva modelo local,4096/768, temperatura0, embeddings CPU y proveedor predeterminado. No se declara que Gemini sea más rápido o mejor a partir de esta única comparación no emparejada.

Tras activar los flags persistentes y recargar se envió H: consulta por título, **`answered / documented`**,11,516s y dos fuentes200. La respuesta emitida coincidió con el historial PostgreSQL. Se registraron4423tokens de entrada,312de salida y388de pensamiento; no se guardó ni mostró pensamiento interno. Esta última prueba acredita la configuración persistente del backend original, no solo una sonda aislada.

## Pruebas automáticas, SQL y recursos

- **1034backend aprobadas,1omitida**,21,30s. Aviso pypdf deprecado preexistente. La prueba omitida corresponde al Job Object nativo, no a Gemini. Evidencia `leny_gemini_resume31_regression.xml`.
- **130pruebas de esquema/síntesis/proveedor aprobadas**,5,01s; `leny_gemini_resume31_binding.xml`.
- **76contratos finales aprobados**,2,77s; `leny_gemini_resume31_final_contracts.xml`.
- **40frontend aprobadas**: selector, transporte, historial, fuentes y cancelación simulados; `leny_gemini_resume31_frontend.json`. La primera invocación elevada no respetó el directorio y no encontró Vitest; se repitió con `Set-Location` explícito, sin instalación de dependencias.
- **9comprobaciones SQL reales** en55432, con identidad/manifiesto verificados: rechazo del intento16/minuto y501/día, TPM y agotamiento durable, entre otras. Transacción exterior revertida y clúster detenido al terminar; no se aplicó una migración nueva en producción. Evidencia `leny_gemini_resume31_schema.json`.
- `pip check` sin dependencias rotas. No se instalaron paquetes.

Comandos principales de regresión desde backend, con configuración exclusiva del proceso y URL ficticia puerto1:

```powershell
$env:DATABASE_URL='postgresql+psycopg2://unit_only@127.0.0.1:1/unit_only'
$env:LENY_RAG_ENABLED='false'
$lenyTests=Get-ChildItem tests -Filter 'test_leny*.py' | ForEach-Object { $_.FullName }
& .\venv\Scripts\python.exe -B -m pytest @lenyTests -q -p no:cacheprovider --junitxml=../documentacion/evidencias/leny_gemini_resume31_regression.xml
& .\venv\Scripts\python.exe -B -m pip check
```

SQL: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File backend/scripts/test_leny_gemini_schema.ps1`. Frontend: `pnpm.cmd exec vitest run src/pages/leny/LenyPage.test.jsx src/pages/leny/lenyTransport.test.js --no-cache --reporter=json --outputFile=../documentacion/evidencias/leny_gemini_resume31_frontend.json`, desde su directorio explícito.

En D final+E, ocho respuestas útiles tuvieron mediana9,328s y rango7,500–14,047s; se excluyen de esa medida los dos bloqueos, **sin excluirlos de los resultados de casos**. H se informa separado por ser posterior a recarga. No hay30muestras comparables: no se calcula p95, tasas SPEC-04 ni aceleración general. Contadores de llamadas/tokens por request, incluidos intentos fallidos, están en `leny_gemini_resume31_final.json`; valores no reportados permanecen identificados como incompletos, no se certifican como cero.

Instantánea global durante la comprobación Qwen: RAM libre3131576KiB sobre16006572KiB y VRAM3743/6141MiB. No representa pico ni consumo atribuible a un proceso; no hay perfil certificado de RAM/VRAM por turno. No se ampliaron límites para conseguir éxito.

## Seguridad, evidencias privadas y límites pendientes

JWT/Casbin, propietario, ACL SQL antes del ranking, publicación/versiones, revalidación antes de Google y de emitir fuentes, coordinación, cuotas y restricciones de herramientas permanecen en el backend. El ledger técnico anterior se conserva; no se borraron reservas para habilitar pruebas. Las nuevas cuotas corresponden a la instrucción del propietario, no a un resultado descubierto por el SDK.

La biblioteca sigue en PostgreSQL/pgvector con embeddings locales. No se modificaron originales, publicaciones, ACL, roles, índices ni datos comerciales. No se transmitieron los datos personales ficticios bloqueados. Los documentos empleados pertenecen al corpus previamente autorizado expresamente por el propietario para transmisión externa y al acceso del actor.

**Límites que no se convierten en aprobación:** las pruebas de documentos restringidos/revocados, aislamiento entre roles y revocación durante una llamada se cubren en regresiones con dobles/contratos de los mecanismos existentes; no se provocaron nuevas revocaciones de documentos empresariales ni se repitió una integración externa completa con varios roles reales en esta reanudación. Las9comprobaciones SQL nuevas verifican cuota/persistencia estructural, no todos esos casos de ACL. Falta una matriz negativa completa con corpus sintético aislado si se requiere certificar todos los criterios de aceptación originales de SPEC-02.

La detección determinista de información personal es parcial y no certifica detectar todo nombre/dato sensible implícito. Se conserva la decisión previa del propietario sobre el corpus apto para envío; publicación interna no equivale automáticamente a permiso externo en otros despliegues. Esta reanudación no implementa un clasificador integral de datos ni declara garantía universal de anonimización.

La revisión automática de herramientas rechazó imprimir respuestas privadas completas. Se continuó con métricas, integridad local y un paquete HTML protegido para revisión humana, sin intentar eludir el rechazo. **No se asignaron calificaciones humanas ni fidelidad semántica automática.** Fuentes accesibles y referencias válidas no prueban que cada afirmación esté sustentada correctamente.

Paquete privado: `%LOCALAPPDATA%\BAB_VDOS\leny-gemini-spec02\review\REVISION_HUMANA_GEMINI31.html`, con18turnos incluidos los fallidos/intermedios, preguntas, respuestas y fuentes. No subir al remoto. Rubrica: respuesta directa, soporte de cada afirmación, cargo/cifras/condiciones, completitud, citas y continuidad útil. La aceptación humana queda pendiente.

Evidencia compartible: `documentacion/evidencias/leny_gemini_resume31_*` y `leny_gemini_spec021_resume31/{A,B,C}.json`. El manifiesto final identifica el árbol real con hashes, no solo HEAD. El evaluador autenticado se cerró al terminar; no guarda usuario, contraseña ni token en su paquete.

## Activación y reversión

La activación persistente se realizó tras A/B/C, D final, E, cancelación/historial y Qwen. Hubo un error de ruta del manifiesto privado en la primera precomprobación: falló **antes de editar flags**; el backend volvió a su configuración desactivada. Se corrigió la ruta, se exigieron salidas exitosas antes de reiniciar y se activaron únicamente los dos flags autorizados. La consulta H confirmó el estado final operativo. No se oculta ese intento fallido ni se lo cuenta como despliegue satisfactorio.

Estado final: backend original sin recarga automática, salud200, protección sin credenciales401, coordinación`idle`, modelo3.1 y cuotas15/250000/500 cargados. Qwen predeterminado. No se aplicó otra migración: revisión0024 conservada.

Reversión operacional inmediata, sin borrar conversaciones ni consumo:

1. Cambiar únicamente `LENY_GEMINI_ENABLED=false` y `LENY_GEMINI_FREE_TIER_CONFIRMED=false`; conservar `LENY_LLM_PROVIDER=ollama` y la clave.
2. Recargar con `backend/scripts/restart_leny_review_backend.py`, que comprueba identidad, lease y operaciones activas antes de detener el proceso identificado.
3. Confirmar salud y nueva conversación Qwen. Los historiales Gemini conservan su identidad; no convertirlos silenciosamente.

Para revertir fuentes de esta reanudación existe `resume31-source.patch` en el subdirectorio privado apuntado por `active.txt`; `manifest-final.json` conserva SHA antes/después. Verificar hashes actuales y después comprobar:

```powershell
$resumeRoot=Get-Content "$env:LOCALAPPDATA\BAB_VDOS\leny-gemini-resume31\active.txt"
git apply --reverse --check --ignore-space-change (Join-Path $resumeRoot 'resume31-source.patch')
```

Solo si los hashes siguen coincidiendo y se decide retirar el código, aplicar el mismo comando sin `--check`, respetando cambios posteriores. El parche no contiene `.env`, no borra datos ni archivos nuevos. `manifest.json` y `activation.json` registran las variables no secretas anteriores; restaurar únicamente esas variables si fuera necesario, sin reemplazar el archivo privado completo. No retirar0024 tras uso ni restaurar un dump sobre producción para este rollback. No se ejecutó reversión.

## Decisión de cierre

Las partes antes bloqueadas por el proveedor **ya recorren el ERP original con3.1Flash-Lite**. Se mantiene habilitado para la revisión funcional del propietario, con Qwen disponible. No se presenta SPEC-02 como certificación integral de seguridad/semántica: permanecen los límites y la matriz negativa indicada. El siguiente paso inmediato del propietario es revisar el paquete privado y probar nuevas conversaciones con ambos proveedores; la optimización profunda y comparación formal siguen reservadas para SPEC-03.
