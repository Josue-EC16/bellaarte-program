# LENY Gemini — SPEC-02.1: diagnóstico y estabilización

> **Continuación autorizada05/11/2026:** se cambió expresamente a `gemini-3.1-flash-lite` y15RPM/250000TPM/500RPD. La generación y JSON reales funcionan y se completaron recorridos de chat/RAG previamente bloqueados; Gemini quedó habilitado como alternativa en el ERP. Véase [revalidación actual y pendientes](LENY_GEMINI_SPEC_02_REVALIDACION_31.md). Este informe conserva el diagnóstico histórico con3.8Flash y20RPD; no atribuye esos fallos a una causa interna resuelta ni convierte las pruebas actuales en aceptación semántica humana.

Fecha: 05/11/2026. Proyecto original: `C:\laragon\www\bellaarte-program`.

## 1. Causa identificada y conclusión

**SPEC-02 continúa pendiente de aceptación funcional.** Dos generaciones mínimas con el SDK oficial, fuera de GeminiProvider y de RAG, devolvieron respuestas HTTP reales de Google:504 `DEADLINE_EXCEEDED` y503 `UNAVAILABLE`. Las dos consultas de metadatos del mismo modelo respondieron200. La hipótesis mejor respaldada es **indisponibilidad/sobrecarga externa probable**; no se dispone de una traza interna del servicio Google que demuestre su causa definitiva.

Se identificó además un defecto independiente de configuración: LENY conservaba500RPD como límite declarado, mientras el propietario confirmó en AI Studio **20RPD**. Se corrigió el límite local y se probó su aplicación. No se presenta esta corrección como solución de los503/504: la segunda generación mínima también falló después de corregir la cuota.

No se atribuye el error a API Key inválida, a documentos, al ranking ni al validador. Tampoco se concluye que toda la integración esté validada porque fallen las peticiones externas: generación estructurada, chat y RAG Gemini siguen sin acreditación real.

## 2. Inspección, flujo y evidencia

Se revisaron `LENY_GEMINI_FASE_01_PREPARACION.md`, `LENY_GEMINI_SPEC_02_INTEGRACION.md`, `LENY_RAG_V11_IMPLEMENTACION.md`, evidencias anteriores y código efectivo. El árbol conserva cambios previos de LENY, sesiones, monedas y otros módulos; no se restauró desde HEAD. No se crearon ramas, worktrees ni otro ERP.

Flujo habitual inspeccionado:

```text
JWT/Casbin → conversación del propietario → proveedor/modelo persistido
→ LenyService.prepare → interpretación/RAG autorizado/selección
→ ManagedProvider → GeminiProvider._generate
→ measure_prompt → _sdk → _call
→ autorización → reserva durable → nueva autorización → SDK GenerateContent
→ formato/soporte/fuentes → revalidación → NDJSON → historial PostgreSQL
```

`GeminiProvider._sdk` construye el cliente de forma diferida. `_call` concentra cuota, autorización, timeout y manejo de errores. `GeminiUsage.reserve` conserva reservas en PostgreSQL y serializa admisión entre procesos. Los embeddings siguen locales y no pasan a Google. Esta SPEC no modificó esos servicios.

La evidencia anterior de SPEC-02 registraba consultas de modelo satisfactorias y generaciones fallidas503/504, incluso sin JSON. Esa evidencia se conserva como histórica, sin convertirla en una ejecución nueva. Las pruebas actuales añaden separación entre SDK directo y adaptador y registran método, host, ruta y estado HTTP; excluyen encabezados, query, credenciales y cuerpos de error.

## 3. SDK directo frente a LENY

SDK instalado y comprobado: **`google-genai==2.33.0`**, Python3.10.6, HTTPX0.28.1. `pip check` correcto. No se actualizaron paquetes.

| Aspecto | Adaptador LENY inspeccionado | Prueba A directa |
|---|---|---|
| Transporte efectivo | SDK con HTTPX | SDK con HTTPX |
| Servicio | Gemini Developer API | El mismo |
| Host | `generativelanguage.googleapis.com` | El mismo, observado en HTTP |
| API | Default efectivo `v1beta` | `v1beta` explícito |
| Generación | `POST /v1beta/models/gemini-3.8-flash:generateContent` | La misma ruta observada |
| SDK intentos |1|1|
| Reintentos propios | Máximo1, solo ante503 |0|
| Timeout HTTP |60s|60s|
| Deadline exterior |60s por llamada;300s por turno |65s para distinguir el timeout HTTP del envoltorio diagnóstico |
| Salida máxima |8192|1024, únicamente dentro del proceso diagnóstico |
| Pensamiento |`medium`, sin incluir pensamiento en respuesta | Parámetro omitido para aislar configuración mínima; no se afirma una medición de su nivel efectivo |
| Esquema | Opcional, según fase | Ninguno |
| Herramientas | Deshabilitadas | Deshabilitadas |
| Contexto | Pipeline autorizado | Una instrucción ficticia mínima, sin historial ni documentos |

No se encontró endpoint alternativo, configuración de Vertex AI ni proxy de entorno. El adaptador pasa `trust_env=False`, `vertexai=False` y `enterprise=False`. La clave se envía por el mecanismo de autenticación del SDK, no se registra en la URL ni en la evidencia.

Los tipos `HttpOptions`, `HttpRetryOptions`, `GenerateContentConfig`, `ThinkingConfig` y las operaciones utilizadas existen en2.33.0. Las pruebas con dobles comprueban sus parámetros; las respuestas HTTP observadas comprueban que la petición llegó al servicio. **No certifican inferencia satisfactoria ni JSON nativo correcto en esta cuenta.** Los hashes de los archivos SDK instalados se guardaron en la evidencia de estado.

## 4. Configuración efectiva y proyecto

El propietario confirmó localmente:

| Dato | Valor |
|---|---|
| Nombre | `Default Gemini Project` |
| Recurso | `projects/520466165333` |
| ID | `gen-lang-client-0646047379` |
| Modalidad | Free Tier |
| RPM / TPM / RPD |5 /250000 /20|

Estos datos proceden de la revisión del propietario en AI Studio. El SDK de generación no proporciona aquí una consulta que permita verificar de forma independiente la pertenencia de la clave a ese proyecto ni sus cuotas efectivas. No se intentó deducirlo del texto de la clave, ni se llamaron APIs administrativas que requieran credenciales IAM adicionales. Las respuestas200 de metadatos demuestran acceso a esa operación; no demuestran identidad de proyecto ni estado de facturación.

Configuración final cargada tras reinicio controlado:

```dotenv
LENY_LLM_PROVIDER=ollama
LENY_GEMINI_ENABLED=false
LENY_GEMINI_MODEL=gemini-3.8-flash
LENY_GEMINI_THINKING_LEVEL=medium
LENY_GEMINI_INPUT_TOKEN_BUDGET=32678
LENY_GEMINI_OUTPUT_TOKENS=8192
LENY_GEMINI_TIMEOUT_SECONDS=60
LENY_GEMINI_TOTAL_TIMEOUT_SECONDS=300
LENY_GEMINI_RPM=5
LENY_GEMINI_TPM=250000
LENY_GEMINI_RPD=20
```

El bloque refleja valores efectivos; no significa que todas esas variables se añadieran al archivo privado. Solo se añadió `LENY_GEMINI_RPD=20` con un comentario. Todos los bytes anteriores de `.env`, incluida la clave, se conservaron y se comprobaron mediante huella del prefijo original. `LENY_GEMINI_FREE_TIER_CONFIRMED` permanecefalse para operación habitual. No se habilitó Gemini para usuarios.

La configuración objetivo conserva32678/8192 y `medium`. La salida1024 y la omisión temporal del parámetro de pensamiento fueron diferencias expresas de la prueba A, no cambios del ERP.

## 5. Pruebas progresivas y resultados

Se realizaron **dos ejecuciones manuales acotadas de A**, cada una con una consulta de modelo y una única generación; no hubo bucles de sondeo ni reintentos automáticos. La segunda comenzó varios minutos después de la primera y ya utilizó20RPD. Se conservaron ambos resultados, incluido el primero con el valor anterior500RPD.

| Ejecución | Metadatos | Generación mínima | Duración generación | Duración total |
|---|---|---|---:|---:|
| `initial` |200;1,328s |504; `ServerError`; `DEADLINE_EXCEEDED` |58,765s|60,156s|
| `confirm` |200;1,297s |503; `ServerError`; `UNAVAILABLE` |18,469s|19,859s|

El primer504 fue una respuesta HTTP observada y una excepción `ServerError`, **no un `asyncio.TimeoutError` local**. Llegó antes del límite HTTP60s y del envoltorio65s. En el segundo error se detectó vocabulario de sobrecarga/indisponibilidad temporal, registrando solo un indicador booleano; no se guardó el mensaje original.

Los metadatos devueltos anunciaron el recurso solicitado, entrada1048576, salida65536 y operación `generateContent`, entre otras. Son capacidades declaradas por el catálogo, no pruebas de que la generación funcione. El campo de versión observado fue`3.0`; se conserva tal cual, sin inferir una versión efectiva de generación que no se obtuvo.

| Etapa | Estado actual | Motivo |
|---|---|---|
| A — SDK mínimo | Fallida, dos intentos separados | Google504 y503 |
| B — JSON mínimo | **No ejecutada** | A no produjo respuesta utilizable |
| C — GeminiProvider | **No ejecutada en SPEC-02.1** | No se cumplen A/B |
| D — conversación ERP | **No ejecutada en SPEC-02.1** | No se cumplen A/B/C |
| E — RAG Gemini | **No ejecutada en SPEC-02.1** | Falló la condición previa |

El script incorpora compuertas locales que impiden B/C si faltan resultados previos satisfactorios en la misma ejecución. Sus tests incluyen casos fallidos y ausentes. No se utilizó el éxito de metadatos como permiso para saltarse esas compuertas. No hubo nueva transmisión documental, personal ni sensible en esta SPEC.

Comandos de pruebas reales ejecutados desde la raíz:

```powershell
& backend\venv\Scripts\python.exe -B backend\scripts\diagnose_leny_gemini_spec021.py --run leny_gemini_spec021_20261105_initial --step A
& backend\venv\Scripts\python.exe -B backend\scripts\diagnose_leny_gemini_spec021.py --run leny_gemini_spec021_20261105_confirm --step A
```

Evidencias individuales: `evidencias/leny_gemini_spec021_20261105_initial/A.json` y `evidencias/leny_gemini_spec021_20261105_confirm/A.json`. Se contabilizaron4peticiones nuevas:2GET y2POST. No hubo texto generado utilizable ni contadores reales de tokens de generación; se informan desconocidos, no cero.

## 6. Reintentos y correcciones aplicadas

En el SDK instalado, `HttpRetryOptions(attempts=1)` permite un intento. El adaptador implementa un máximo de dos intentos totales y reintenta solo503, con pausa1–2s y nueva reserva. No reintenta504 ni timeout local. La espera de cuota —hasta61s acotados— es distinta del backoff. No se encontró multiplicación de reintentos entre SDK y aplicación.

No se aumentaron timeouts: el504 directo fue remoto y el503 también apareció con una instrucción mínima. No se alteraron arquitectura, prompts, validadores, parámetros objetivo, modelos ni ranking para ocultar el bloqueo.

**Corrección conservada:**20RPD por defecto y como máximo configurable para este proyecto. Un valor21 o500 es rechazado por Settings en vez de permitir una activación con una cuota mayor a la declarada. La admisión continúa contabilizando intentos fallidos y todas las fases; no se borraron reservas ni consumo para poder probar de nuevo. Las operaciones realizadas fuera de LENY con el mismo proyecto no son visibles para su ledger, y Google puede contabilizar ciertas operaciones de otra manera; este límite local es conservador y no sustituye AI Studio.

| Archivo | Cambio |
|---|---|
| `backend/app/core/config.py` | Default/máximo diario de500a20 |
| `backend/.env.example` | Ejemplo corregido a20RPD |
| `backend/.env` | Solo comentario y nueva línea no secreta `LENY_GEMINI_RPD=20` |
| `backend/scripts/diagnose_leny_gemini_spec021.py` | Nuevo diagnóstico A/B/C secuencial, cuota/lease comunes y evidencia HTTP permitida |
| `backend/scripts/test_leny_gemini_schema.py` | Límite20 y prueba real del rechazo diario21, solo en clúster sintético |
| `backend/scripts/test_leny_gemini_schema.ps1` | Evidencia de esta fase en archivo separado de SPEC-02 |
| `backend/tests/test_leny_gemini_diagnostics.py` | Nuevos tests de compuertas, límite y salida sin pensamiento |

No se modificó `leny_gemini.py` ni su manejo de errores durante esta fase. El diagnóstico registró origen HTTP y tipo de excepción sin hacer cambios funcionales innecesarios.

## 7. Pruebas automatizadas y SQL

Resultados actuales:

- **74pruebas específicas aprobadas**,4,55s; GeminiProvider, preparación, persistencia y nuevo diagnóstico.
- **1027pruebas LENY aprobadas,1omitida**,26,86s. La omisión existente remite el caso Job Object al comprobador nativo; no es una prueba Gemini omitida para aprobar. Un aviso de deprecación pypdf.
- **9comprobaciones PostgreSQL reales aprobadas** en el clúster existente55432, identificado por manifiesto, instancia y directorio. Incluyen la denegación del intento diario21, aun siendo fallidos los20anteriores. Todo el esquema/datos temporales se revirtió; no se usó la base comercial.
- `pip check`: sin dependencias rotas. No se instalaron ni actualizaron paquetes.

La suite unitaria se ejecutó con variables exclusivas del proceso: URL PostgreSQL ficticia en puerto1, `LENY_RAG_ENABLED=false`; cada prueba inyecta la configuración y dobles que necesita. Esas variables no modificaron el backend activo. No se realizaron peticiones Google mediante mocks.

```powershell
Set-Location C:\laragon\www\bellaarte-program\backend
$env:DATABASE_URL='postgresql+psycopg2://unit_only@127.0.0.1:1/unit_only'
$env:LENY_RAG_ENABLED='false'
& .\venv\Scripts\python.exe -B -m pytest tests/test_leny_gemini_diagnostics.py tests/test_leny_gemini_provider.py tests/test_leny_gemini_preparation.py tests/test_leny_gemini_persistence.py -q -p no:cacheprovider --junitxml=../documentacion/evidencias/leny_gemini_spec021_tests.xml
$lenyTests=Get-ChildItem tests -Filter 'test_leny*.py' | ForEach-Object { $_.FullName }
& .\venv\Scripts\python.exe -B -m pytest @lenyTests -q -p no:cacheprovider --junitxml=../documentacion/evidencias/leny_gemini_spec021_regression.xml
& .\venv\Scripts\python.exe -B -m pip check
```

Desde la raíz también se ejecutó `powershell.exe -NoProfile -ExecutionPolicy Bypass -File backend/scripts/test_leny_gemini_schema.ps1`. Su clúster se inició para la prueba y se detuvo al terminar. Evidencia nueva: `evidencias/leny_gemini_spec021_schema.json`; se conserva separadamente la evidencia anterior de ocho comprobaciones de SPEC-02.

## 8. RAG y compatibilidad con Qwen

No se ejecutó RAG con Gemini en SPEC-02.1 porque A falló. No hay nuevos resultados documentales externos ni aprobación de citas, seguimiento, selección o JSON real. Los resultados RAG descritos en SPEC-02 siguen siendo históricos, con sus limitaciones.

El cambio funcional se limita a configuración Gemini. Qwen conserva modelo local`qwen3.5:4b-q4_K_M`, contexto4096, salida768, temperatura0 y `keep_alive=0`. Se mantienen embeddings CPU, dimensiones, ACL, publicaciones, `rag4_v1`, ranking híbrido, vecinos apagados y `controlled-synthesis-v1`. No se rediseñaron metadatos ni se reindexó.

Después del reinicio, Ollama respondió a `/api/tags` y `/api/show`; el modelo Qwen está instalado y no declara un destino remoto. La regresión backend pasó. **No se repitió una generación Qwen autenticada en esta fase:** la prueba documental satisfactoria con tres fuentes pertenece a SPEC-02. Estas comprobaciones actuales acreditan disponibilidad de servicio/configuración y contratos, no una nueva aceptación humana de respuestas.

No se cambiaron archivos frontend. Las pruebas anteriores del selector no se vuelven a presentar como ejecutadas en SPEC-02.1. Gemini continúa deshabilitado en el selector según estado del servidor; no se probó una conversación externa nueva para saltarse la condición A.

## 9. Seguridad y estado de producción

Backend original reiniciado controladamente mediante `restart_leny_review_backend.py`, después de preparar reversión y pasar regresión. El helper comprueba identidad del proceso, lease de LENY, trabajos documentales y operaciones PostgreSQL activas antes de detener el árbol identificado. Se mantiene sin `--reload` para impedir aplicar cambios parciales en caliente. No se detuvo Ollama ni se interrumpieron otras instancias por nombre.

Estado final comprobado: `/health`200, `/api/v1/leny/status` sin credenciales401, coordinación de inferencia`idle`, Gemini desactivado, Qwen predeterminado. La base conserva revisión0024; no se aplicó ninguna nueva migración en producción. Los únicos nuevos registros de diagnóstico en la base habitual son reservas/finalizaciones técnicas de las4peticiones autorizadas. No se alteraron documentos, índices, datos comerciales, roles ni ACL.

No se imprimió, sustituyó ni copió la clave. El diagnóstico no guarda prompts, respuestas generadas, headers, querystrings o cuerpos de error. Las copias privadas contienen únicamente fuentes y registro no secreto del cambio de cuota; no incluyen `.env`. No se habilitaron pagos, otro modelo, cuenta, proyecto ni Vertex AI.

Evidencia de estado y hashes: `evidencias/leny_gemini_spec021_state.json`. El ledger final conserva14intentos técnicos acumulados entre SPEC-02 y SPEC-02.1; no equivale a un contador exacto del proyecto Google, ni incluye usos externos a LENY. El proyecto y su Free Tier se registran como confirmados por el propietario, no como verificados mediante una API administrativa.

## 10. Reversión

Ubicación privada de las versiones previas y registros:

`%LOCALAPPDATA%\BAB_VDOS\leny-gemini-spec021\leny_gemini_spec021_20261105_initial`.

`source-change-manifest.json` identifica SHA antes/después de cuatro archivos y `spec021-source.patch` contiene exclusivamente sus diferencias. Las versiones previas se contrastaron contra el manifiesto congelado de SPEC-02. La comprobación inversa pasó, sin aplicar la reversión:

```powershell
git apply --reverse --check --ignore-space-change "$env:LOCALAPPDATA\BAB_VDOS\leny-gemini-spec021\leny_gemini_spec021_20261105_initial\spec021-source.patch"
```

Antes de aplicar ese parche, comprobar que cada SHA actual coincide con el SHA posterior del manifiesto. Si difiere, revisar el archivo y no sobrescribir trabajo posterior. La reversión de código sería el mismo comando sin `--check`, seguida de recarga controlada. Los scripts/pruebas nuevos pueden permanecer archivados: no se ejecutan en el arranque. No usar reset/clean ni restauraciones generales.

**Reversión operacional recomendada:** conservar Gemini apagado y mantener el límite real20. Revertir el código al default anterior500 no justifica retirar el límite explícito20 del `.env`. No hay cambios de esquema que deshacer ni reservas que borrar.

Para retirar exclusivamente la adición de `.env`, si se decide hacerlo expresamente, `env-quota-change.json` contiene longitud/huella del prefijo original y el texto agregado, sin clave. Verificar que la huella actual coincide con `expected_sha256`, que el prefijo conserva `original_sha256` y que el sufijo es exactamente `added_text`; solo entonces truncar a `original_bytes`. Si cualquiera difiere, detener esa operación y revisar cambios posteriores. Este procedimiento no se ejecutó, pues retiraría una protección válida.

## 11. Pendientes y decisión recomendada

**Mantener Gemini desactivado y SPEC-02 no aceptada.** La evidencia nueva sitúa el bloqueo antes del adaptador/RAG. No ampliar timeouts, relajar validación, cambiar modelo o activar facturación como respuesta automática.

La próxima comprobación debe ser un único A mínimo en otra ventana, con el mismo modelo/proyecto y el consumo conservado. Si A funciona, continuar B y después C, registrando todos los fallos. Solo tras A/B/C satisfactorios se debe abrir una sesión ERP normal para D/E con contenido apto para transmisión externa y completar historial, NDJSON, cancelación, fuentes, ACL/revocación y control de datos sensibles. Su aprobación no se puede deducir de estas pruebas de transporte.

Para contrastar externamente el bloqueo, el propietario puede consultar AI Studio/estado de Google o remitir los horarios, modelo, rutas y estados HTTP, sin compartir clave ni documentos. No se enviaron mensajes a soporte ni a terceros en esta tarea. La asociación exacta de la clave al proyecto y las cuotas permanecen sustentadas por la revisión local del propietario; no se falsea una verificación administrativa.

No se inició SPEC-03 ni una comparación semántica entre modelos.

### Referencias oficiales y alcance de las fuentes

- [SDK oficial2.33.0, cliente HTTP y reintentos](https://github.com/googleapis/python-genai/blob/v2.33.0/google/genai/_api_client.py): contrastado con el código instalado; default Developer API`v1beta` y configuración de intentos.
- [Diagnóstico oficial Gemini API](https://ai.google.dev/gemini-api/docs/troubleshooting): diferencia indisponibilidad/deadline y aconseja reintentos acotados. La consulta web de su contenido completo devolvió un error de formato; no se afirma haber leído una página completa que el visor no pudo recuperar.
- [Respuesta de Google sobre503 en Gemini3.8Flash](https://discuss.ai.google.dev/t/free-tier-interactions-api-getmodel-succeeds-but-generation-returns-503-on-gemini-3-8-flash-and-429-on-gemini-3-6-flash/189550/2): Google describe sobrecarga temporal y remite a cuotas de AI Studio. El caso enlazado menciona Interactions; esta implementación usa GenerateContent, por lo que es contexto corroborante y **no una prueba de que ambos incidentes tengan exactamente la misma causa**.
