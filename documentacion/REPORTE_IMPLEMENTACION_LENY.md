# Entrega LENY — Etapa 01

**Estado vigente 21/10/2026:** [piloto supervisado activado con autorización expresa](#activación-real-autorizada-del-piloto-en-el-erp-habitual-21102026), `rag4_v1/rag4-v4`, en `bellaarte_db:5432`. Configuración efectiva, conversación real y conservación del historial/datos comprobadas. **Aceptación formal pendiente.** El predespliegue y las rondas anteriores conservan su fecha y sus resultados históricos.

**19/10/2026.** Núcleo conversacional integrado al ERP existente, con Qwen/Ollama local, historial privado PostgreSQL, streaming NDJSON, JWT/Casbin y diagnóstico ADMIN. Validación real realizada en el ERP con base aislada. **Actualización 16:14 America/La_Paz: migración0017 aplicada con autorización posterior a `bellaarte_db:5432`; historial y disponibilidad comprobados desde el ERP habitual.**

Guía operativa, contratos, configuración, arquitectura y comandos: [MODULO_LENY.md](MODULO_LENY.md).

## Archivos creados

| Área | Archivos |
|---|---|
| API y contratos | `backend/app/api/routers/leny.py`, `backend/app/schemas/leny.py` |
| Servicios | `backend/app/services/leny_service.py`, `leny_ollama.py`, `leny_store.py`, `leny_coordination.py` |
| Persistencia | `backend/app/models/leny.py`, `backend/alembic/versions/20261019_0017_leny.py` |
| Operación y prueba real | `backend/scripts/leny_retention.py`, `run_leny_smoke.py`, `start_leny_smoke.ps1` |
| Pruebas backend | `backend/tests/test_leny.py`, `backend/tests/integration/test_leny_persistence.py` |
| Componentes React | `frontend/src/pages/leny/LenyPage.jsx`, `LenyMarkdown.jsx`, `useLenyChat.js`, `lenyTransport.js`, `leny.css` |
| Pruebas frontend | `frontend/src/pages/leny/LenyPage.test.jsx`, `lenyTransport.test.js`, `lenyAxios.test.js` |
| Documentación | `documentacion/MODULO_LENY.md`, este reporte |

Los nombres abreviados de cada fila permanecen dentro del directorio indicado en su primer archivo.

## Archivos modificados por esta integración

- Backend: `app/api/router.py`, `app/core/config.py`, `app/core/permissions.py`, `app/security/policy.csv`, `app/main.py`, `app/models/__init__.py`, `alembic/env.py`, `.env.example`.
- Pruebas aisladas: `backend/scripts/run_notification_integration.py`, `backend/tests/integration/conftest.py` para revisión0017, permisos del esquema y limpieza limitada a identidades sintéticas.
- Frontend: `src/routes/AppRoutes.jsx`, `src/layout/AuthenticatedLayout.jsx`, `src/api/client.js`, `package.json`, `pnpm-lock.yaml`.
- Contexto del proyecto: actualización puntual de `AGENTS.md` para distinguir el núcleo implementado de las capacidades analíticas futuras.
- `.gitignore`: exclusión de la caché local `.pnpm-store/`, que contiene una junction creada por pnpm hacia el frontend; no se eliminó recursivamente ese directorio.

Se preservaron los cambios previos presentes en los mismos archivos y en otros módulos; este inventario no atribuye a LENY todo el diff general del workspace.

## Dependencia, API y permisos

Única dependencia directa nueva: **react-markdown 10.1.0**. Sin dependencias backend nuevas, instalaciones Redis, frameworks adicionales ni cambios del stack.

Rutas `/api/v1/leny`: `GET /status`, `POST /chat`, `POST /conversations`, `GET /conversations`, `GET /conversations/{id}`, `DELETE /conversations/{id}`, `GET /admin/config`.

`leny:chat` está configurado para ADMIN, CAJA, INV_BOUTIQUE, INV_TALLER y MODISTA. `leny:admin` solo para ADMIN. No se crearon roles del ERP. El propietario es el usuario individual enlazado de forma única a la cuenta, no un rol; ADMIN tampoco consulta conversaciones ajenas.

## Evidencia automatizada

| Verificación ejecutada | Resultado |
|---|---|
| Backend, launcher sin DB/SMTP/procesos externos | **203 aprobadas**, suite completa; 43 casos LENY |
| PostgreSQL aislado, launcher con badge de instancia | **80 aprobadas**, suite completa; 10 casos LENY contando parametrización |
| Vitest frontend completo | **50 aprobadas**, 20 casos LENY |
| ESLint frontend completo | Sin errores |
| Build frontend final con API aislada explícita | Correcto; advertencia heredada de bundle grande |
| `pip check` | Sin dependencias incompatibles |
| AST Python, sintaxis PowerShell y `git diff --check` | Correctos |

Las pruebas simulan respuestas Ollama para error/conexión/timeout/validación y verifican los plazos independientes de conexión, primer contenido, inactividad y duración total. Incluyen UTF-8 fragmentado, respuestas vacías, exceso de tamaño, HTML/URLs peligrosas, interrupciones, cierre HTTPX/generadores/leases, socket ASGI desconectado y cliente lento.

Autenticación usa JWT real de prueba y políticas Casbin reales con persistencia reemplazada; el rol efectivo procede de la cuenta en servidor. Axios fetch se ejecuta realmente sobre una respuesta HTTP simulada para comprobar renovación JWT, cierre de un 401 abierto y conservación del mismo UUID/payload.

PostgreSQL prueba DDL upgrade/downgrade/rollback dentro de transacciones aisladas y compara definiciones y datos `public`. También comprueba propietarios diferentes, eliminación física, secuencias/estados/roles, solicitudes completed/failed/interrupted, recuperación de generaciones abandonadas, contención entre conexiones y pérdida real de una conexión sintética mediante pg_terminate_backend. No se reinició ni terminó una conexión empresarial.

## Evidencia real desde el ERP

Se ejecutó la aplicación FastAPI real en `localhost:8001`, frontend React compilado en `localhost:5174` y el Qwen instalado en `127.0.0.1:11434`, con PostgreSQL dedicado `bab_vdos_testing:55432` y cuenta sintética individual. No se empleó un mock de chat en este recorrido.

1. Inicio de sesión mediante formulario existente y entrada LENY desde el menú del ERP.
2. Disponibilidad del modelo exacto `qwen3.5:4b-q4_K_M`.
3. Mensaje: “Hola LENY. Preséntate en una frase y aclara si puedes consultar las ventas del ERP en esta etapa.”
4. Respuesta visible real: “¡Hola! Soy LENY, tu asistente inteligente de BELLAARTE BOUTIQUE, diseñado para conversar sobre tendencias y estrategias de moda, pero en esta etapa no tengo acceso a consultar datos del ERP ni ejecutar acciones empresariales.”
5. Recarga completa de la página: sesión recuperada mediante refresh y conversación recuperada desde PostgreSQL.
6. Respuesta extensa con fragmentos y listas Markdown visibles progresivamente.
7. Cancelación real de un ensayo: contenido parcial conservado y confirmado como `interrupted`; un envío posterior respondió “sesión recuperada.”, demostrando disponibilidad posterior del recurso.
8. Revisión a tamaño móvil y corrección del header únicamente para la ruta LENY; comprobación posterior sobre el frontend corregido.
9. En la compilación final, una segunda identidad sintética recibió “Funciono como un modelo de lenguaje local sin acceso a bases de datos, sistemas ERP ni documentos internos.” Se verificó el 422 junto al mensaje, la recuperación del historial tras volver a iniciar sesión y la cancelación con reconciliación automática hasta `interrupted`.

Antes de limpiar la primera identidad sintética se verificaron **1 conversación, 8 mensajes, 9 eventos de auditoría LENY, 0 payloads de auditoría inesperados y 0 bloqueos de generación**. La limpieza comprobó firma e identificadores de esa identidad y no alcanzó otros usuarios. Las capturas del navegador durante el recorrido muestran la interfaz y las respuestas; los mensajes son exclusivamente de prueba.

La primera salida por Ctrl+C mostró que PostgreSQL de prueba heredaba la consola y podía detenerse antes de limpiar el usuario. Se corrigió el launcher para iniciar pg_ctl en consola oculta y esperar únicamente a ese proceso. La limpieza específica del intento anterior se ejecutó y luego se repitió la suite PostgreSQL: **80 aprobadas en 12,41 s**.

El cierre final del launcher corregido confirmó **1 conversación, 4 mensajes, 5 auditorías LENY, 0 payloads inesperados y 0 bloqueos** antes de eliminar exclusivamente la segunda identidad sintética. La limpieza terminó y PostgreSQL de pruebas se detuvo correctamente; se comprobó ausencia del archivo `postmaster.pid` y de listeners en los puertos de prueba 5174/8001/55432. El viewport del navegador se restauró y la pestaña de prueba se cerró.

## Habilitación autorizada en el ERP habitual

Tras el reporte del error503 y autorización explícita del propietario, `scripts/deploy_leny_storage.py` comprobó la conexión efectiva: `bellaarte_db:5432`, revisión0016 y esquema LENY ausente. Creó un respaldo custom de 249470 bytes, verificó índice/lectura completa offline/SHA256 y aplicó exclusivamente `20261019_0017`.

La verificación posterior confirmó revisión0017, estructura `public` intacta y permisos USAGE/SELECT/INSERT/UPDATE/DELETE efectivos sobre las nuevas tablas. No se ejecutaron seeds, cambios de roles/usuarios ni operaciones comerciales. El respaldo y manifiesto privados están en `backend/storage/backups/leny-deployment-20261019-161445/`, excluido de Git. La lectura offline no sustituye un ensayo de restauración.

En la sesión existente del usuario en `http://localhost:5173/app/leny` se actualizaron conversaciones y disponibilidad: el historial cargó sin error y apareció **Modelo local disponible**. No fue necesario reiniciar el backend del puerto8000, que ya tenía el código LENY cargado. No se agregó una conversación de prueba a la cuenta empresarial.

## Límites

- La habilitación local quedó aplicada y verificada; el ERP habitual no fue usado para operaciones comerciales de prueba. No equivale a certificación de despliegue remoto/productivo.
- Historial en texto por usuario, sin papelera; advertencia de no compartir secretos. La retención automática está deshabilitada; el script manual requiere ejecución explícita.
- Una generación concurrente por base de datos para LENY; no hay cola ni coordinación con otras aplicaciones que utilicen Ollama.
- El contexto es acotado y puede omitir turnos antiguos completos. Respuestas truncadas o canceladas no alimentan el contexto siguiente.
- Los límites iniciales se comprobaron en conversaciones reales y simulaciones, sin benchmark de carga sostenida o garantía de calidad analítica.
- No se detuvo el Ollama del usuario: caída, interrupción y timeouts se cubrieron mediante transporte simulado. Roles sin permiso y propietarios distintos se verificaron automatizadamente, sin usar credenciales empresariales.
- No se implementaron Redis, RAG, embeddings, consultas SQL del agente, BI, simulación, ML, AutoML, subida de documentos ni herramientas de escritura.
- La deuda global de cookies/secretos, revocación y bundle preexistente no se presenta como corregida por esta etapa.

La validación acredita el núcleo conversacional **en entorno aislado**, con una conversación real desde el ERP. No certifica un despliegue productivo ni las capacidades analíticas futuras.

## Etapa 01.1 — fortalecimiento del núcleo existente

Se preservaron el monolito FastAPI, PostgreSQL, Axios/React, streaming NDJSON, JWT, Casbin, propiedad individual, auditoría y lease global de la Etapa 01. La inspección detectó cuatro brechas específicas: ámbito general del prompt, falta de cuota compartida, salida sin revisión preventiva y contexto sin marca de evaluación. Las limitaciones globales de cookies, secretos de configuración y revocación del ERP permanecen fuera de esta modificación.

### Archivos y cambios de esta etapa

| Tipo | Archivos | Propósito |
|---|---|---|
| Nuevos | `backend/app/services/leny_policy.py`, `leny_guard.py`, `leny_rate_limit.py` | Política empresarial, entradas/salida y admisión PostgreSQL |
| Nuevo | `backend/alembic/versions/20261019_0018_leny_policy_rate.py` | Sólo metadatos y tablas del esquema LENY |
| Nuevos | `backend/tests/test_leny_security.py`, `tests/fixtures/leny_security_cases.json`, `tests/integration/test_leny_rate_limit.py` | Pruebas adversariales, corpus y concurrencia real |
| Nuevos | `backend/scripts/evaluate_leny_security.py`, `check_leny_smoke_api.py` | Evaluación Qwen sin BD y ensayo HTTP sintético |
| Modificados | `backend/app/models/leny.py`, `schemas/leny.py`, `services/leny_service.py`, `leny_store.py`, `leny_ollama.py`, `api/routers/leny.py` | Metadatos, contexto, clasificación, revisión y códigos seguros |
| Modificados | `backend/app/core/config.py`, `backend/.env.example`, `backend/app/main.py` | Variables de límites y exposición CORS de Retry-After |
| Modificados | `backend/tests/integration/conftest.py`, `test_leny_persistence.py`, `backend/scripts/run_notification_integration.py` | Revisión0018, permisos de prueba, contexto y rollback |
| Modificados | `backend/scripts/run_leny_smoke.py`, `start_leny_smoke.ps1`, `deploy_leny_storage.py` | Ensayo aislado, limpieza propia y despliegue revisable hasta 0018 |
| Modificados | `frontend/src/pages/leny/LenyPage.jsx`, `useLenyChat.js`, `lenyTransport.js` y sus tres pruebas | Mensaje empresarial, cuota visual, duplicados y errores seguros |
| Actualizados | `documentacion/MODULO_LENY.md`, este reporte y JSON en `documentacion/evidencias/` | Operación, evidencias y riesgos |
| Actualizado | `AGENTS.md` | Estado de 0018 aislada y separación de despliegue empresarial |

**Dependencias nuevas: ninguna. Endpoints y permisos nuevos: ninguno.** Se mantienen `leny:chat` para los cinco códigos existentes y `leny:admin` exclusivamente ADMIN; no se modificaron las definiciones de roles en esta etapa.

### Controles incorporados

- Cuota configurable de **5 admisiones por persona en 60 s**, atómica entre workers mediante bloqueo de fila. Los intentos admitidos ocupados, rechazados, caídos, interrumpidos o fallidos consumen cuota; un duplicado no vuelve a cobrar ni generar. Ventana y Retry-After usan el reloj de PostgreSQL.
- Ledger con UUID/huella/fecha/resultado, sin texto. Persiste tras borrar conversaciones y mantiene retención oportunista acotada de al menos una hora. Los duplicados sin turno visible reciben un conflicto explícito; no aparecen respuestas ficticias en React.
- Política backend de seis categorías. Reglas prioritarias y clasificación local con el mismo Qwen, JSON cerrado, sin razonamientos ni permisos generados. Revisiones contextuales con plazo conjunto de 20 s; ninguna consulta incorpora herramientas o privilegios.
- Consultas mixtas: sólo cláusulas originales aprobadas llegan al modelo; si la separación es incierta, aclaración. Se excluyen del siguiente contexto. Las menciones negadas del negocio no son aprobación automática.
- Entrada Unicode y secretos reconocibles validados antes de guardar; los 422 no devuelven el texto sensible. Se conservan los límites de entrada/contexto/generación y los plazos de la Etapa 01.
- Salida acumulada revisada antes de emitir, con sufijo retenido de 256 caracteres. Formatos de secretos, fragmentos protegidos, roles simulados y ciertas afirmaciones de operaciones se bloquean. Sólo texto revisado llega al historial; se cierra el HTTP de Ollama y el lease también al cancelar.
- Contexto heredado y de versiones anteriores visible pero excluido. Sólo turnos empresariales terminados y aprobados con política vigente se reutilizan.
- Auditoría por códigos, sin prompts ni respuestas; cuota agregada por persona/ventana. Rechazos heurísticos son sospechas, no confirmación de ataque. Errores de preparación y cancelaciones conservan un resultado terminal explícito.
- React conserva Markdown sin HTML crudo, imágenes ni enlaces activos. Distingue 401/403/429 y muestra espera sin reenvío automático; se verificó 401→refresh→429 manteniendo UUID y payload.

### Pruebas automatizadas y HTTP

La última ejecución base aprobó **332 pruebas en 4,72 s**, con bloqueo previo de PostgreSQL/SMTP/procesos; `pip check` no detectó dependencias rotas. La suite PostgreSQL final aprobó **93 pruebas en 19,22 s** contra `bab_vdos_testing:55432`, incluida 0018 upgrade/downgrade/rollback y preservación de `public`. El clúster se detuvo al finalizar. La ampliación incluye ocho hilos con cinco admisiones/tres 429, duplicado concurrente, propietarios distintos, retención y exclusión de contexto de políticas anteriores.

Frontend final: **61 pruebas aprobadas**, ESLint sin errores y build temporal correcto en 30,48 s (`%TEMP%\bab-leny-011-final-review`). Incluye renovación JWT seguida de cuota, cancelaciones, rechazos/clarificaciones, XSS, reconciliación de duplicados y errores de seguridad/indisponibilidad sin eco de detalles internos. El aviso preexistente de bundle grande permanece; no se cambió el stack para corregirlo incidentalmente.

`evidencias/leny_011_api_smoke.json` documenta HTTP real contra el ERP aislado: 422 sin eco de JWT sintético, rechazo de campos privilegiados, cinco respuestas seguras, sexto intento 429, Retry-After 60 y visible por CORS, duplicado 409 después de cuota, rechazos persistidos sin contexto y recuperación con refresh JWT. El navegador mostró la cuenta regresiva y Enviar deshabilitado al agotar cuota. Estos ensayos no realizaron inferencia para los rechazos deterministas ni operaciones comerciales.

### Evaluación real y transparencia

Se conservaron `leny_011_evaluation_initial.json` y `leny_011_evaluation_v2.json`: 100 % empresarial, 90 % fuera de ámbito y 100 % de reconocimiento de capacidades ausentes mediante respuestas deterministas. Los 16 probes directos de Qwen no mostraron patrones de exposición reconocidos; esto no prueba ausencia de cualquier forma de filtración. El sobrecoste caliente p95 observado fue 1,484 s inicialmente y 1,235 s en v2, con generaciones diferentes y medición ruidosa.

Tras inspeccionar fallos, la política `01.1-v4` corrige el falso pase por contexto negado y la separación de preguntas mixtas. La evaluación final usa el mismo corpus y los mismos umbrales; es regresión adaptada, no validación no vista ni garantía de invulnerabilidad. La evidencia final se guarda en `evidencias/leny_011_evaluation.json`. Los tiempos fríos no se certifican: no se descargó el modelo del usuario para forzar una carga desde cero.

| Métrica final, dos pasadas | Resultado |
|---|---:|
| Clasificación exacta de los 64 casos por pasada | 128/128 |
| Empresariales aceptadas | 40/40 |
| Fuera del ámbito rechazadas | 20/20 |
| Ataques clasificados | 32/32 |
| Ambiguas aclaradas | 12/12 |
| Mixtas separadas | 12/12 |
| Capacidades ausentes reconocidas | 12/12, respuesta determinista |
| Probes directos con Qwen completados | 16 |
| Exposiciones de patrones reconocidos en probes | 0 |
| Sobrecoste caliente del primer contenido, p95 | 1,563 s |
| Intentos de BD, SMTP o red externa del evaluador | 0 |

En las 128 solicitudes, 74 se resolvieron sin inferencia y 54 utilizaron el proveedor real; los 16 probes directos y seis referencias calientes son adicionales. No se presenta el rechazo determinista como resistencia semántica del modelo. El JSON marca `accepted=true` para los criterios del corpus evaluado, sin certificar generalización. Las salidas/prompts no se guardaron en ese reporte.

`evidencias/leny_011_validation_summary.json` registra las huellas y el alcance: política, guardia y adaptador evaluados coinciden con los archivos finales. Durante el ensayo se reforzó además el cierre seguro del servicio ante fallo de persistencia/cancelación; ese código de orquestación no forma parte del evaluador de inferencia y se comprobó con las pruebas automatizadas finales. Se conserva explícita esa diferencia de huellas, sin atribuir al evaluador pruebas de API o persistencia.

### Recorrido final real desde el ERP

Se usaron orígenes 127.0.0.1:5174/8001 y una identidad sintética individual en PostgreSQL aislado, separados de las cookies del `localhost` habitual:

1. Inicio de sesión normal y acceso a LENY desde el menú.
2. Rechazo visible del caso con contexto empresarial negado, sin contestar su parte ajena.
3. Cinco solicitudes admitidas por HTTP y sexta 429; el navegador conservó el borrador, explicó la cuota y mostró Enviar deshabilitado con cuenta regresiva, sin reintento automático.
4. Consulta mixta sobre margen de un vestido y una pregunta histórica: se avisó del límite y Qwen respondió únicamente el cálculo empresarial en Bs, con margen del 20 %.
5. Generación de una guía de inventarios, interrumpida con Detener: se conservó el texto parcial revisado y apareció `Respuesta interrumpida`.
6. Solicitud posterior sobre descuento del 10 % de Bs 200: respuesta real de 180 Bs, comprobando liberación y recuperación del recurso.
7. Recarga completa: refresh de sesión y recuperación del historial, incluido el estado interrumpido y la respuesta posterior.

El ensayo terminó con **1 conversación, 8 mensajes, 33 auditorías LENY, 0 payloads de auditoría inesperados y 0 leases de generación**. Se detuvieron sólo los procesos propios de prueba y se limpió exclusivamente la identidad/historial/cuota sintéticos mediante comprobación de firma. No se detuvo Ollama ni el ERP habitual. La limpieza y la ausencia final de listeners de prueba se verifican en el resumen de validación.

### Ejecución y límites de despliegue

Configuración adicional: `LENY_RATE_LIMIT=5`, `LENY_RATE_WINDOW_SECONDS=60`, `LENY_OUTPUT_HOLDBACK_CHARS=256`, `LENY_CLASSIFIER_TIMEOUT=20`. Modelo exacto local `qwen3.5:4b-q4_K_M`, 4096 de contexto, 768 de generación y una sola generación global. No se incorporaron Redis, SQL del agente, RAG, BI, ML ni accesos automáticos a datos.

```powershell
Set-Location C:\laragon\www\bellaarte-program\backend
.\venv\Scripts\python.exe -B scripts/run_base_tests.py
.\venv\Scripts\python.exe -B scripts/evaluate_leny_security.py
# Sólo inspección del destino empresarial; no migra:
.\venv\Scripts\python.exe -B scripts/deploy_leny_storage.py
```

Al terminar las pruebas aisladas, la migración 0018 todavía no se había aplicado a `bellaarte_db`. El despliegue empresarial posterior, autorizado expresamente por el propietario, se detalla a continuación. El código nuevo necesita 0018 para funcionar y devuelve 503 seguro si faltan sus objetos. No se crearon tablas al arrancar ni se deshabilitaron controles para mantener compatibilidad artificial.

Riesgos residuales: clasificador y heurísticas pueden fallar ante nuevas paráfrasis/codificaciones; el contenido ya emitido no puede retirarse. La retención de 256 caracteres reduce exposición de patrones conocidos, no asegura toda semántica ni secretos arbitrarios. Las respuestas cortas esperan al final; las largas mantienen streaming. Falta validación independiente con nuevos casos no vistos y carga sostenida multiusuario. Las futuras herramientas deberán verificar permisos por herramienta/recurso y tratar documentos/resultados como datos no confiables; no se implementaron en esta etapa.

### Habilitación empresarial autorizada de 0018

El 19/10/2026, tras la instrucción explícita «REALIZA LA MIGRACIÓN Y LOS CAMBIOS TIENES MI PERMISO», se verificó el destino efectivo `bellaarte_db:5432` y la revisión 0017. Se ejecutó el procedimiento preparado `scripts/deploy_leny_storage.py --apply`:

- Respaldo custom privado de **255636 bytes**, índice, lectura offline completa y SHA-256 `5167dc5aec6517475a4ea2c55472b920a19357111e3a44935cf79421a1c32dcb` verificados antes del DDL. La lectura offline no equivale a un ensayo de restauración.
- Aplicación transaccional `20261019_0017 → 20261019_0018`, exclusivamente metadatos y tablas LENY.
- Comparación posterior de columnas, restricciones e índices de `public`: estructura intacta. Permisos USAGE y SELECT/INSERT/UPDATE/DELETE comprobados para las cuatro tablas LENY.
- Validación adicional de sólo lectura: revisión 0018, columnas de política, servicio `LENY_READY`, modelo exacto `qwen3.5:4b-q4_K_M` y cuota efectiva de cinco solicitudes por 60 s.
- Archivo Casbin sin cambios: SHA-256 anterior/posterior `7a1d700cb64cf5c910aa067ddb6a75dcdda02d581553ab03b9a8781de4047053`. La API habitual mantuvo 401 sin autenticación.

**Hallazgo preexistente de roles:** la base empresarial contiene los cinco códigos base y además `DOC`. Se comprobó que `DOC` ya figura en los datos del respaldo anterior a 0018. Los códigos antes/después coinciden; no se creó, eliminó ni renombró ningún rol durante esta operación. Las políticas reales deniegan `leny:chat` y `leny:admin` a `DOC`; corregir la cantidad histórica de roles sería una decisión de seguridad separada y no se borraron registros ajenos como parte de LENY.

El respaldo y los informes privados están en `backend/storage/backups/leny-deployment-20261019-184242/`, excluidos de Git. La evidencia publicable sin credenciales se guarda en `documentacion/evidencias/leny_011_business_deployment.json`.

Después de que el propietario iniciara sesión, se comprobó el ERP habitual en `http://localhost:5173/app/leny`: historial cargado sin503, indicador «Modelo local disponible» y respuesta real de Qwen a una consulta de funcionamiento sin datos privados. Una recarga completa renovó la sesión y permitió abrir la conversación persistida. Se dejó esa conversación de prueba visible; no se borró historial del usuario. El backend y frontend habituales siguieron ejecutándose, sin necesitar reinicio.

**Estado:** implementación de Etapa 01.1 y migración empresarial 0018 realizadas, con verificación real posterior desde la sesión del ERP. Se mantienen los límites de la evaluación adaptada y no se afirma seguridad absoluta ni certificación de producción remota.

## RAG-SPEC-01 — Implementación documental (19/10/2026)

Estado: IMPLEMENTADO Y HABILITADO en el ERP habitual, con validación técnica aislada y aceptación E2E de la carga desde navegador pendiente. La migración0019 se aplicó en bellaarte_db:5432 con autorización expresa posterior; el procedimiento y la comprobación empresarial se detallan al final de esta sección. El valor predeterminado del código permanece deshabilitado.

### Diagnóstico y decisiones

Se reutilizaron JWT/Casbin, identidad individual, auditoría, SQLAlchemy/Alembic y el cliente/tema Ant Design. El chat y su lease Ollama no se reconstruyeron. No existía biblioteca ni parsers documentales; el router del chat leía cuerpos de16KiB antes de autenticar y no era adecuado para multipart. El respaldo existente solo contenía PostgreSQL.

El responsable confirmó conservar DOC excluido, ampliar el respaldo completo y mantener estrictamente todas las versiones actuales. Se descartó cambiar Python para incorporar Pillow13. La alternativa pyvips/binario trabaja con Python3.10.6/CFFI2.0.0. Se verificó e instaló únicamente pypdf6.21.1, defusedxml0.7.1, pyvips3.2.0 y pyvips-binary8.18.7; cero distribuciones anteriores modificadas.

### Archivos de esta entrega

| Grupo | Archivos nuevos |
|---|---|
| Persistencia | backend/app/models/leny_documents.py; backend/alembic/versions/20261019_0019_leny_documents.py |
| HTTP/contratos | backend/app/api/routers/leny_documents.py; backend/app/schemas/leny_documents.py |
| Servicios | backend/app/services/leny_document_service.py; leny_document_storage.py; leny_document_validation.py; leny_document_maintenance.py; leny_document_backup.py |
| Parsers/operación | backend/scripts/validate_leny_document.py; leny_documents_maintenance.py; verify_leny_document_backup.py |
| Pruebas ejecutables | backend/scripts/check_leny_document_parsers.py; check_leny_documents_http.py; check_leny_documents_recovery.py; check_leny_documents_recovery.ps1 |
| Pruebas backend | backend/tests/test_leny_document_api.py; test_leny_document_backup.py; test_leny_document_parsers.py; backend/tests/integration/test_leny_document_schema.py; test_leny_document_service.py |
| Dependencias | backend/requirements-leny-documents.txt |
| Cliente React | frontend/src/api/lenyDocuments.js |
| Pantallas/estilos | frontend/src/pages/leny/documents/DocumentAdminRoute.jsx; LenyDocumentsPage.jsx; DocumentUploadModal.jsx; DocumentDetailDrawer.jsx; documentUtils.js; documents.css |
| Pruebas React | En la misma carpeta: documentApi.test.js; documentAxios.test.js; DocumentsPage.test.jsx; DocumentUploadModal.test.jsx; DocumentPreview.test.jsx; documentUtils.test.js |

Modificados para integrar esta entrega: backend/app/api/router.py, core/config.py, app/main.py, models/__init__.py, schemas/backup.py, services/backup_service.py, scripts/backup_manager.py, scripts/run_leny_smoke.py, scripts/start_leny_smoke.ps1, tests/integration/conftest.py y test_leny_persistence.py; backend/.env.example; .gitignore; frontend/src/routes/AppRoutes.jsx, layout/AuthenticatedLayout.jsx, pages/backups/BackupsPage.jsx y backupUtils.js; documentacion/MODULO_LENY.md y este reporte. AGENTS.md y la SPEC reciben una nota de estado. Se preservó el trabajo previo ajeno a esta entrega, incluido el que ya aparecía modificado en Git.

### Resultado implementado

- Biblioteca /app/leny/documents, ADMIN + leny:admin en UI y servidor. Otros cuatro roles y DOC rechazados incluso con permiso manipulado; sin alterar sus políticas.
- Carpetas, defaults/ACL por documento, filtros/paginación, originales privados, versiones inmutables, previews JPG/PNG y DOCX con texto/tablas. PDF mediante descarga autenticada.
- Carga incremental autorizada antes del multipart, límites reales, SHA-256 e idempotencia durable; Axios XHR conserva FormData/request_id al renovar JWT y cancela sin reintento automático.
- Separación de recursos PostgreSQL/Ollama, detección de pérdida de lease y compuerta transaccional. Cierre físico garantizado aun si falla la limpieza.
- Papelera10 días, confirmaciones ligadas a revisiones/ACL, purgas idempotentes recuperables, mantenimiento entre workers y recuperación tras reinicio.
- Publicación bloqueada en API y BD; ningún archivo entra a Ollama ni al historial conversacional.
- ZIP privado verificado con dump, originales, previews y manifiesto; descarga de respaldos antiguos compatible y contenido señalado en UI.

Los contratos, parámetros, endpoints y comandos operativos se documentan en MODULO_LENY.md, sección RAG-SPEC-01, evitando repetirlos aquí.

### Evidencias ejecutadas

| Verificación | Resultado real |
|---|---|
| Suite base backend sanitizada |430 aprobadas;1 omitida deliberadamente: prueba nativa que exige lanzador separado |
| PostgreSQL aislado55432 |119 aprobadas, incluidos26 casos nuevos de esquema/servicio y upgrade/downgrade sin alteración de public |
| Parsers reales y Job Object Windows |15 aprobadas; PDF activo/cifrado, DOCX/ZIP/XML/relaciones, JPG/PNG, truncamiento y rutas |
| Frontend completo |85 aprobadas en15 archivos;24 pruebas documentales nuevas |
| ESLint/build temporal |Correctos; persiste advertencia de bundle grande (~2.66MB JS, ~796kB gzip) |
| pip check y comparación de metadatos |Correctos; cero versiones existentes cambiadas |
| HTTP real8001 |Cuatro formatos, hashes/headers privados, versión2 conserva1, duplicados tras cuota,429, previews,404, publicación409, papelera/restauración y refresh JWT |
| Recuperación real |pg_dump y pg_restore en una base nueva aleatoria del clúster55432; cuatro originales, tres previews, metadata y papelera coinciden; ZIP corrupto rechazado |
| Navegador ERP5174 |Inicio ADMIN sintético, creación de carpeta, listado, detalle y preview DOCX, envío a papelera y restauración confirmada; vista390px sin desbordamiento del documento |
| Regresión Qwen desde ERP |Respuesta real y streaming terminados; reconoció no tener acceso a archivos ni BD |
| Latencia aislada pequeña |10 listados calientes de4 documentos/5 versiones: mediana10.565ms y máximo/p95 observado14.37ms; umbral1000ms para este escenario, no SLA de volumen |

Evidencias persistidas en documentacion/evidencias/: leny_rag01_dependencies.json, leny_rag01_http.json, leny_rag01_recovery.json, leny_rag01_latency.json, leny_rag01_validation.json, leny_rag01_biblioteca.jpg y leny_rag01_movil.jpg. No contienen credenciales, tokens, dumps ni originales empresariales.

Durante la integración se detectaron y corrigieron: error de descarga por exigir lease de escritura a una lectura autorizada; cierre omitido del lease si fallaba fail_upload; respuesta de archivo sin cierre garantizado antes del primer fragmento; nombre Windows normalizado por el parser antes de validar; límite de memoria Job Object configurado incorrectamente; encabezado móvil comprimido; previews DOCX con demasiados párrafos vacíos y consultas N+1 del listado. Los casos relevantes quedaron cubiertos por pruebas o recorrido real.

### Pendientes y límites

1. Antecedente al cierre inicial: la extensión bloqueó la selección local y el agente verificó multipart por HTTP real, además de Axios XHR/refresh/cancelación. Seguimiento: el propietario confirmó después que ya probó la carga mediante selector y funciona correctamente. Se acepta esa evidencia aportada por el usuario; no se atribuye al agente una prueba de selección que no ejecutó.
2. Despliegue sobre la base habitual realizado tras autorización expresa posterior: respaldo verificado,0019, permisos y raíz privada comprobados, ENABLED=true y recarga del backend. Listado vacío y Actualizar verificados con la sesión ADMIN existente. Los rechazos de los otros roles se probaron en el entorno aislado; no se crearon usuarios empresariales para repetirlos.
3. Antivirus/CDR y aislamiento OS completo no están implementados. Job Objects y parsers reducen riesgo y consumo, sin certificar archivos inocuos ni bloquear todos los exploits nativos.
4. La revocación persistente de JWT no existe en la autenticación actual; se conservan los mecanismos existentes y no se presenta como validada.
5. El modelo puede cometer errores semánticos: en el recorrido real denominó incorrectamente la moneda Bs. No se cambió ese comportamiento ajeno a la gestión documental ni se atribuyó exactitud financiera al chat.
6. Falta ensayo de volumen sostenido y monitorización productiva. El bundle/frontend grande y el aviso de compatibilidad Passlib/Bcrypt anterior siguen presentes; no se actualizaron paquetes para ocultarlos.
7. La purga no elimina archivos de respaldos históricos. Los respaldos se guardan privados sin cifrado propio y requieren retención/protección operativas.

Se retiraron las identidades y registros sintéticos del smoke al cerrar el servidor8001; el almacenamiento privado temporal se eliminó con su directorio de prueba. Las pruebas de migración/restauración no tocaron bellaarte_db:5432. No hay commits, seeds empresariales ni herramientas RAG/SQL/BI añadidas.

### Despliegue empresarial autorizado de0019

El 19/10/2026 el propietario autorizó «APLICA TIENES MI PERMISO PARA PROSEGUIR». Se creó y ejecutó backend/scripts/deploy_leny_documents.py --apply, independiente del procedimiento anterior de0018:

- Destino comprobado bellaarte_db:5432,0018, biblioteca deshabilitada y seis tablas documentales ausentes. Se conservan los cinco roles base y DOC preexistente excluido.
- Respaldo custom anterior al DDL, privado fuera del webroot; índice, lectura offline completa y SHA-256 verificados. No se restauró ni se ensayó rollback sobre la base habitual.
- Migración transaccional0018→0019 aplicada. Columnas, restricciones e índices de public idénticos; códigos de roles conservados; USAGE y SELECT/INSERT/UPDATE/DELETE de las seis tablas comprobados para la identidad de ejecución.
- Solo LENY_DOCUMENTS_ROOT y LENY_DOCUMENTS_ENABLED se configuraron en backend/.env; raíz privada LOCALAPPDATA/BAB_VDOS/leny-documents con DACL restringida. No se copiaron credenciales a informes ni se cambiaron versiones de paquetes.
- Recarga del Uvicorn habitual, sin modificar contenido de main.py. /health200 y GET /api/v1/leny/documents sin credenciales401. La sesión ADMIN ya abierta cargó la biblioteca vacía y pudo actualizarla sin errores; se conservó el borrador del chat en su pestaña original.
- Respaldo conjunto adicional verificado: ZIP284161bytes, SHA-256 53A043707229DBD8C6F7C494B44C8FC017481E6E0E2EF525756535FFACD9EC50, manifest0019, dump283647bytes y cero originales/previews. No crea una entrada de historial administrativo: es una comprobación operativa directa del generador.
- Reinspección confirmó0019 y ENABLED=true. pip check correcto. Las comprobaciones del actualizador .env con LF/CRLF preservaron los otros valores y rechazaron cambios concurrentes; no se repitieron las suites completas anteriores por esta operación de despliegue.

El informe privado de migración y before-0019.dump están en LOCALAPPDATA/BAB_VDOS/leny-documents/backups/deployment-0019-d4cd5efb1dd7422a88a9a5be27cda797/. El ZIP conjunto está bajo la misma raíz privada de respaldos. La evidencia sin credenciales está en evidencias/leny_rag01_business_deployment.json y leny_rag01_business_library.jpg. leny_rag01_validation.json conserva el estado histórico del cierre aislado anterior a esta autorización.

**Estado final de este despliegue:** biblioteca habilitada en http://localhost:5173/app/leny/documents, acceso ADMIN/listado verificados, sin registros documentales sintéticos empresariales. La carga por selector fue aceptada posteriormente por el propietario. Los resultados técnicos del agente y la aceptación manual del usuario son evidencias distintas. No se habilitó lectura de documentos por Qwen.

## RAG-SPEC-02 — Implementación y despliegue de contextualización

Fecha local de comprobación:19/10/2026; los archivos de evidencia registran UTC del20/10. Plan implementado tras aprobación del propietario y autorización expresa para pgvector/migración, preservando las versiones actuales. La aclaración del usuario sobre la carga mediante selector se registra como prueba manual aceptada. Se reutilizó qwen3-embedding:0.6b ya instalado; no se descargó otro modelo.

### Diagnóstico y decisiones aplicadas

La biblioteca SPEC-01 aportaba originales/versiones inmutables, ACL, almacenamiento privado, parsers limitados, lease documental, compuerta de transacciones y respaldo conjunto. El núcleo conversacional ya aportaba JWT/Casbin, streaming y coordinador PostgreSQL de inferencia. No había OCR, persistencia vectorial ni trabajos de contextualización activos; pgvector y Tesseract no estaban disponibles. Se conservaron esos mecanismos y se añadieron las responsabilidades faltantes, sin sustituir autenticación ni reconstruir la biblioteca.

Riesgos principales: contenido nativo no confiable; inferencias que sobrevivan a un worker caído; activación de índices parciales; pérdida de índices anteriores; competencia por RAM con otros programas; metadatos sensibles en errores; compatibilidad de respaldos y del esquema existente. Se decidió worker manual único, embeddings CPU obligatorios, almacenamiento PostgreSQL, límites de extracción, publicación bloqueada y no incorporar recuperación al chat hasta SPEC-03.

### Archivos creados

Rutas relativas al repositorio; esta lista corresponde a SPEC-02 y no atribuye a esta entrega los archivos de etapas anteriores ni cambios ajenos del workspace:

| Grupo | Archivos |
|---|---|
| Persistencia y contratos | backend/app/models/leny_rag.py; backend/app/schemas/leny_rag.py; backend/alembic/versions/20261019_0020_leny_contextualization.py |
| API | backend/app/api/routers/leny_contextualizations.py |
| Procesamiento | backend/app/services/leny_rag_common.py, leny_rag_extraction.py, leny_rag_chunking.py, leny_rag_embeddings.py, leny_rag_service.py y leny_rag_worker.py |
| Operación | backend/scripts/prepare_leny_rag_runtime.py, deploy_leny_rag.py, extract_leny_document.py, run_leny_rag_worker.py, leny_rag_worker.ps1 y reconcile_leny_rag_provider.py |
| Comprobación | backend/scripts/check_leny_rag.py y check_leny_rag.ps1; backend/tests/test_leny_rag.py y test_leny_rag_worker_control.py; backend/tests/integration/test_leny_rag_schema.py y test_leny_rag_service.py |
| Dependencias | backend/requirements-leny-rag.txt |
| React | frontend/src/pages/leny/documents/ContextualizationPanel.jsx, ContextualizationPanel.test.jsx y contextualizationUtils.js; los helpers también se comprueban en ContextualizationPanel.test.jsx |
| Evidencias | documentacion/evidencias/leny_rag02_*.json y tres capturas .jpg |

### Archivos existentes modificados

- Backend: app/api/router.py; app/core/config.py; app/models/__init__.py y leny_documents.py; app/schemas/leny_documents.py; services/leny_coordination.py, leny_document_service.py, leny_document_validation.py, leny_document_maintenance.py y leny_document_backup.py. Se registran modelos/router, configura el pipeline, comparte inferencia, invalida derivados y extiende respaldos.
- Pruebas/infraestructura aislada: backend/tests/integration/conftest.py, test_leny_schema.py y test_leny_document_schema.py; backend/scripts/provision_notification_test_postgres.ps1. Compatibilidad de la nueva revisión y extensión; rollback exclusivamente aislado.
- Frontend: src/api/lenyDocuments.js, pages/leny/documents/DocumentDetailDrawer.jsx y LenyDocumentsPage.jsx; integra acciones, estados e historial con la sesión/Axios existentes.
- Configuración/documentación: backend/.env.example y configuración privada local; AGENTS.md; MODULO_LENY.md; este reporte; notas de seguimiento en ambas specs RAG. Ningún secreto se incorpora a la documentación.

### Dependencias y compatibilidad

Python: pgvector0.5.1 y pypdfium2 5.14.0. Instalación con constraints del ERP, --no-deps y ruedas binarias; comparación de metadatos previa/posterior: ninguna distribución existente cambió. pip check correcto. Frontend no incorpora paquetes nuevos.

Nativas: pgvector0.8.7 compilado con MSVC2022 contra los headers/librerías de PostgreSQL17.9 ya instalado; copia privada aislada, ensayo vectorial1024 y pg_dump/pg_restore antes de agregar archivos nuevos a esa distribución. No se sustituyeron binarios PostgreSQL. Tesseract5.5.3 se extrajo al runtime privado con7-Zip existente, sin elevar el instalador, modificar registro ni registrar servicios. Datos spa/eng/osd fijados por commit/hash. Manifiesto de procedencia y hashes en LOCALAPPDATA/BAB_VDOS/leny-rag-runtime/runtime.json, protegido fuera del webroot.

Se conservan Python3.10.6, PostgreSQL17.9, Ollama0.40.6, Qwen generativo y dependencias previas. El modelo de embeddings mantiene nombre/digest exactos;1024 dimensiones, num_gpu=0,4 hilos, contexto4096, lote2, truncate=false. /api/ps confirmó cero bytes de VRAM en las inferencias reales.

### Controles, API y comportamiento

Se añaden cinco tablas leny.rag_* y un puntero de índice validado por versión. El proceso durable tiene UUID idempotente, revisión de actor/versión/hash/pipeline, token de propietario, heartbeat, checkpoints y recuperación de abandonados. La correspondencia fragmentos/vectores y la activación final se comprueban transaccionalmente. Fallar o cancelar una recontextualización conserva el índice válido previo; borrar/restringir un documento invalida el trabajo.

Los cinco endpoints nuevos son POST/GET /api/v1/leny/documents/{id}/versions/{version}/contextualizations, GET /api/v1/leny/contextualizations/{job}, POST /api/v1/leny/contextualizations/{job}/cancel y GET /api/v1/leny/admin/rag/status. Detalle de payload, errores y comandos en [MODULO_LENY.md](MODULO_LENY.md), sección RAG-SPEC-02.

Todas las operaciones exigen ADMIN individual habilitado y permiso leny:admin/use; se mantienen cinco roles oficiales y DOC preexistente excluido. No se conceden nuevos permisos de datos ni acceso documental al chat. Las solicitudes no controlan modelo, opciones, identidad ni rutas. Auditoría conserva eventos/códigos de trabajo, validación, cancelación, fallo y exceso de cuota, sin almacenar textos ni vectores en esos eventos.

Tasa de admisión5/minuto/cuenta, atómica en PostgreSQL; replay equivalente no recarga cuota. Trabajos que después fallan/cancelan siguen contando. Cola100, un worker, una inferencia LENY compartida con chat. Cuerpo JSON16KiB; texto1MiB,1000fragmentos/trabajo y2GiB derivados globales. Conexión5s, lectura120s, lote150s y trabajo1800s. Campos completos en .env.example. Un marcador de inferencia incierta bloquea nuevas generaciones hasta reconciliación explícita segura, en lugar de asumir que Ollama se detuvo al perder HTTP.

La interfaz conserva el diseño y cliente HTTP del ERP. Hay Contextualizar, confirmación para recontextualizar, reintento explícito, cancelación, historial paginado y progreso por etapa/contadores reales. La consulta periódica solo se ejecuta mientras corresponde y se cancela al ocultarse el panel. La versión final muestra pendiente de publicación, con publicación deshabilitada.

### Pruebas ejecutadas

| Verificación | Resultado y alcance |
|---|---|
| Backend base completo, sin conexiones externas |547 aprobadas,1 omitida deliberadamente por requerir lanzador de parser nativo; un aviso de deprecación pypdf en prueba existente |
| Archivo RAG después de agregar caso de cuerpo fragmentado |113 aprobadas; incluye un caso adicional al recorrido base anterior. JWT/Casbin reales en TestClient con servicio simulado, roles/identidad, contratos, errores, tamaño y429 |
| PostgreSQL aislado55432 |161 aprobadas; esquema, upgrade/downgrade, FK/CHECK, idempotencia, tasas, recuperación, aislamiento, cancelación, purga, índices y nueva retención. Clúster detenido al finalizar |
| Control de metadatos del worker |5 casos incluidos en las547 base: exclusión heartbeat/hilo principal, reintento de bloqueo/backup, propietario perdido y parada activa |
| Frontend completo |101 aprobadas en16 archivos; acciones, estados, polling/cancelación e historial |
| ESLint y build temporal |Correctos para los archivos RAG; build correcto. Permanece aviso anterior de bundle grande (~2.68MB JS/~802kB gzip) |
| Dependencias |pip check correcto, cero distribuciones previas cambiadas |
| Pipeline nativo real |PDF, DOCX, PNG y JPG; OCR PDF escaneado y PNG rotado conservan cifra conocida; rechazo por límite OCR y ausencia de texto; cancelación del proceso nativo comprobada |
| Ollama real CPU |Vectores1024 y size_vram=0 verificados por lote; modelo/digest exactos |
| Respaldo/restauración aislados |Dump/restore en BD nueva aleatoria: originales,5vectores/5fragmentos,4índices y5trabajos coherentes; solo ese destino sintético se retiró |
| ERP habitual, navegador |Contextualización completa:4páginas,4fragmentos,4vectores; reintento explícito y recuperación de checkpoint tras reiniciar worker; puntero válido y publicación deshabilitada |
| Regresión de chat real |Qwen respondió desde el ERP habitual sobre margen de utilidad después de contextualizar; streaming terminado. No fue una respuesta documental RAG |
| Vista reducida |Viewport solicitado390px; ancho efectivo de layout434px igual a scrollWidth del documento, sin desbordamiento global. Viewport restaurado; no certificar390px efectivos |
| Carga por selector |Aceptada por el propietario; no atribuida a una ejecución del selector por el agente |

Los escenarios nativos usan modelos y herramientas reales, no respuestas simuladas. Las pruebas de API unitarias simulan el servicio; la comprobación real aislada usa TestClient con JWT, PostgreSQL y pipeline reales. El navegador habitual verifica además la integración React/HTTP real. No se ensayaron operaciones comerciales sintéticas sobre datos empresariales existentes.

### Incidencias corregidas durante la comprobación real

1. libvips con lectura secuencial no permitía reutilizar el mismo raster para medidas y PNG: copia explícita en memoria antes de OCR.
2. Tesseract privado no tenía el archivo de configuración denominado tsv: opción explícita tessedit_create_tsv=1.
3. El umbral fijo de RAM2GiB bloqueaba el siguiente lote después de cargar el propio modelo. Medición real:3146276864bytes disponibles antes,2013380608 tras carga y3173175296 tras liberación; modelo1237875425bytes, VRAM0. Se conserva2GiB en frío y1GiB residente, configurables; no se aumentó contexto ni se habilitó GPU. Primer intento fallido preservado en historial.
4. Heartbeat y hilo principal competían por su propio lease documental; se serializaron sus mutaciones y se añadió reintento acotado de30s ante bloqueo documental/respaldo. Si no puede persistirse el fallo, el worker se detiene para reconciliar al reiniciar. Se comprobó recuperación real del mismo trabajo/checkpoint, con finalización en el segundo intento de ejecución.
5. Cancelación HTTP ahora limita también cuerpos fragmentados sin Content-Length. La liberación de un modelo propio contempla respuestas completas malformadas; incertidumbre de transporte sigue requiriendo cuarentena.

### Despliegue y evidencia empresarial

Se aplicó0019→0020 únicamente tras ensayos aislados y autorización expresa, con respaldo privado previo al DDL, pgvector en leny y verificación posterior de columnas/restricciones/índices public, códigos de roles y permisos DML. No se ejecutó restore ni downgrade sobre bellaarte_db. No se editaron migraciones aplicadas para introducir cambios posteriores.

El worker quedó iniciado manualmente con heartbeat vigente y sin inferencia incierta al comprobar el cierre. Documento real ya aportado por el propietario: índice validado de4fragmentos/4vectores, versión pendiente de publicación. El intento anterior fallido y sus derivados temporales se conservan por política de retención; por ello el respaldo posterior tiene8fragmentos pero4embeddings, sin inconsistencia en el índice validado.

Respaldo conjunto posterior:4440507bytes, SHA-256 A59F9AB5D987ABB863B3A3A594560758888F162B47A70F93152BBE1DF78F966E, manifiesto v2 verificado; contiene1original,2índices,2trabajos,8fragmentos y4embeddings. Como en SPEC-01, esta comprobación directa del generador no inserta una entrada de historial administrativo. Informe privado de despliegue en LOCALAPPDATA/BAB_VDOS/leny-documents/backups/deployment-0020-70f5a7dfcf924f2598a714bc4e768d43.json; ZIP/dump fuera de Git y webroot.

Evidencias públicas sin originales, texto extraído, vectores, credenciales ni tokens: [despliegue](evidencias/leny_rag02_business_deployment.json), [ensayo real aislado](evidencias/leny_rag02_real_check.json), [memoria CPU](evidencias/leny_rag02_cpu_memory.json), [contextualización habitual](evidencias/leny_rag02_business_contextualization.jpg), [vista reducida](evidencias/leny_rag02_mobile.jpg) y [regresión Qwen](evidencias/leny_rag02_chat_regression.jpg). El manifiesto leny_rag02_validation.json reúne alcance, resultados y hashes de estas evidencias.

### Rendimiento, riesgos residuales y estado final

Cuatro documentos sintéticos reales tardaron entre4.703 y6.985s;131 muestras del sistema cada0.25s mostraron RAM disponible mínima1817980928bytes y CPU ocupada29.81%. Incluyen otras aplicaciones y no acreditan pico atribuible al worker, volumen sostenido ni SLA. Se verificó CPU sin VRAM; el parser limita su Job Object a1536MiB.

OCR puede equivocar cifras y estructura; no hay OCR de imágenes DOCX ni reconstrucción perfecta de tablas/múltiples columnas. Job Objects limitan procesos/recursos y no son sandbox OS completo ni antivirus. Otros clientes de Ollama no comparten el coordinador del ERP. Un cierre incierto puede bloquear temporalmente chat/procesamiento hasta reconciliación; esto conserva la seguridad del límite de concurrencia. No se añadieron servicios automáticos, y después de reiniciar Windows hay que iniciar el worker manualmente.

Riesgos previos conservados: sin revocación JWT persistente, identidad de BD con privilegios amplios; la autenticación global presupone la relación usuario de una cuenta y puede fallar500 ante datos corruptos sin esa relación. LENY comprueba además propiedad individual; no se modificó autenticación ajena a este alcance. Los respaldos no se cifran por la aplicación y precisan protección/retención operativas. No se certifica ausencia de regresiones en todos los procesos empresariales por las pruebas ejecutadas.

**Estado:** SPEC-02 implementada y desplegada, con pruebas técnicas y recorrido real de contextualización aprobados en los escenarios descritos. No se declara evaluación integral de RAG ni invulnerabilidad. SPEC-03 deberá añadir publicación, recuperación autorizada y citas; SPEC-04 evaluará exactitud, Recall@K, fidelidad, ataques documentales y carga. No se implementaron búsqueda documental en chat, SQL generado, BI, ML ni escritura autónoma.

## RAG-SPEC-03 — Implementación de publicación y chat con fuentes

Entrega inicial20/10/2026: se implementó el plan aprobado conservando versiones, arquitectura y trabajo previo, y se ensayó0021 en PostgreSQL aislado55432. En ese momento no se migró ni habilitó RAG-chat en bellaarte_db, pendiente de autorización separada. El despliegue autorizado posterior y su comprobación habitual constan al final de esta sección; el valor predeterminado LENY_RAG_CHAT_ENABLED del código sigue false.

### Diagnóstico y controles incorporados

El código anterior prohibía publicar mediante CHECK, contrato None y endpoint deliberadamente bloqueado. El puntero técnico de contextualización era mutable y el parser NDJSON rechazaba eventos desconocidos. Las fuentes requerían rutas de lectura distintas de la biblioteca ADMIN; la recuperación no podía depender de OCR/worker ni reutilizar respuestas históricas privadas como evidencia actual. La cuarentena cubría al worker, no las inferencias del chat.

La nueva migración fija publicación por documento/versión/índice validado mediante FK compuestas, metadatos conjuntos y documento activo. Una columna generada protege el estado aprobado; la aplicación no la escribe. Publicar/despublicar reutilizan revisión, lease documental, compuerta transaccional y tombstones idempotentes. Recontextualizar conserva el índice publicado. Papelera retira publicación y restaurar no republica. No se alteraron migraciones0017–0020.

La búsqueda exacta aplica identidad, rol, ACL, publicación y compatibilidad dentro de SQL parametrizado, antes de exponer fragmentos. Usa coseno calificado en esquema leny; no índices aproximados ni filtrado de contenido prohibido en Python. La política empresarial mantiene capacidades transaccionales/Internet/escritura no disponibles. Evidencia delimitada como datos, presupuesto conservador, revisión estructurada y guardia de salida con referencias autorizadas. Ninguna respuesta concede permisos.

Las fuentes se guardan por mensaje sin duplicar texto o títulos; la purga deja referencias sin contenido. Cada lectura/descarga revalida propietario y autorización actual. Por decisión confirmada del usuario, la ACL permite descargar el original completo y el texto histórico se conserva tras revocación. Los turnos RAG se excluyen del contexto reutilizable. La UI muestra Fuentes consultadas, sin atribuir verificación semántica por frase.

La inferencia mantiene el advisory lock existente. Un singleton durable independiente del historial registra fase/modelo y conserva incertidumbre tras caídas. Cancelar corta la emisión y drena la petición propia hasta terminación/plazo; cerrar TCP no se considera prueba de parada. La reconciliación manual comprueba ausencia de modelos sin reiniciar Ollama ni descargar modelos ajenos. La autorización se revisa antes del contexto y en fronteras de emisión; no se promete retirar bytes ya entregados.

### Inventario de cambios de esta SPEC

| Grupo | Archivos creados o modificados |
|---|---|
| Nuevos datos/contratos | backend/alembic/versions/20261020_0021_leny_publication_sources.py; app/models/leny_rag_chat.py; app/schemas/leny_rag_chat.py |
| Nuevos servicios | backend/app/services/leny_rag_publication.py, leny_rag_retrieval.py, leny_rag_sources.py y leny_inference_state.py |
| Nueva API | backend/app/api/routers/leny_sources.py |
| Nuevos componentes/helpers | frontend/src/pages/leny/LenySources.jsx, lenySourceUtils.js; documents/PublicationPanel.jsx; frontend/src/api/lenySources.js; pruebas correspondientes |
| Backend adaptado | config, registro de router/modelos, modelos leny_documents/leny_rag, schemas leny/leny_documents, routers leny/leny_documents/leny_contextualizations, servicios leny_service/store/policy/guard/ollama/coordination, document_service, rag_service/worker/embeddings |
| Operación/pruebas | Nuevo deploy_leny_rag_chat.py; ampliados check_leny_rag.py/.ps1 y reconcile_leny_rag_provider.py; pruebas test_leny_rag_chat_contracts.py e integration/test_leny_rag_chat.py; fixtures y pruebas de rollback anteriores adaptadas al head0021 |
| React existente | LenyPage, useLenyChat, transporte NDJSON, cliente documental, detalle/listado y pruebas afectadas; Markdown/guard/rutas administrativos conservados |
| Respaldo/documentación | backup_manager.py tolera stderr nativo no UTF-8; .env.example, MODULO_LENY.md, AGENTS, reporte y seguimiento de la SPEC |

No se añadieron dependencias ni se cambiaron versiones de Python, PostgreSQL, Ollama, modelos o frontend. Los archivos de etapas anteriores siguen separados conceptualmente de este inventario, aunque el workspace ya contenía cambios sin commit.

### API y configuración

Se mantienen chat e historial. Publicar recibe request_id, versión, índice, revisión y confirmación; Despublicar recibe UUID/revisión/confirmación. Las respuestas documentales incorporan done.sources opcional, compatible con clientes anteriores. Dos rutas nuevas de lectura: GET /api/v1/leny/rag/sources/{id} y /download, con acceso por propietario+leny:chat+ACL actual. Fuentes ajenas/revocadas/inexistentes usan404 equivalente, sin títulos ni localizadores restringidos.

Límites:5generaciones/60s/persona ya existente; máximo20candidatos y5fuentes, SQL2s, embedding de consulta20s, pregunta1536bytes y evidencia2048bytes, con contexto4096/generación768 y presupuesto completo de framing. Se mantiene CPU4hilos/1024dimensiones/digest exacto y comprobación VRAM0. Margen frío2GiB y residente1GiB; el adaptador de consulta comprueba también el margen tras inferir. Variables y comandos completos en MODULO_LENY.md, sección RAG-SPEC-03.

### Verificación y hallazgos

Resultados ejecutados y alcance detallado en evidencias/leny_rag03_validation.json; no confundir pruebas simuladas con inferencias reales. La suite frontend tiene115casos/18archivos y el lint del alcance está correcto. Build temporal correcto (~2.69MB JS/~805kB gzip), con advertencia previa de bundle grande. pip check correcto; no paquetes existentes actualizados.

La comprobación real aislada registrada en leny_rag03_real_check.json completó PDF, DOCX, PNG y JPG: publicación ADMIN, consulta CAJA con Qwen/Ollama reales, cifra conocida en respuesta, fuente de origen correcta y descarga original con SHA-256 coincidente. Se restauraron originales, publicaciones, fuentes y vectores en una BD aleatoria aislada, retirada posteriormente. Esa ejecución completa precede las ampliaciones adversariales y de instrumentación posteriores; no acredita por sí sola todos los escenarios de la versión final.

Hallazgos corregidos durante la integración:

1. Los imports sin extensión confundían LenySources.jsx con lenySources.js en Windows; el helper pasó a lenySourceUtils.js.
2. Las nuevas columnas ORM podían introducir referencias anticipadas durante inserciones sobre0020: carga diferida y eager_defaults=false, con prueba específica de compatibilidad.
3. El entero PK del singleton producía una secuencia automática innecesaria que impedía respaldar con la identidad de pruebas. Se configuró autoincrement=false y se reaplicó0021 solamente en el clúster aislado, pasando por downgrade protegido. No se alteró una migración empresarial aplicada.
4. stderr de PostgreSQL podía usar codificación no UTF-8: lectura tolerante, sin éxito ficticio del respaldo.
5. La configuración CORS de la demostración apuntaba al frontend habitual: el lanzador aislado fija5174, sin cambiar la configuración empresarial.
6. Consultas mixtas documentales no deben rehabilitar Internet o datos transaccionales: prioridad explícita y pruebas de regresión.

La repetición adversarial completa con ambas residencias y aplicaciones abiertas encontró falta de RAM:812208128bytes disponibles frente al mínimo1GiB. El trabajo falló de forma segura; su estado se persistió, las conexiones/bloqueos se liberaron y el clúster se detuvo. No se desactivó el guard residente para obtener verde. La evaluación de esa presión de memoria y del perfil de residencia debe cerrarse antes de habilitar el entorno habitual.

Los lanzadores separan tres evidencias: recorrido real de cuatro formatos, demostración UI acotada de un PDF y benchmark opcional ReleaseTestModel. Este último usa keep_alive=0 solo en peticiones sintéticas y conserva márgenes2GiB/1GiB; no llama a una descarga forzada de modelos ajenos ni modifica .env. Es una opción de evaluación, no una política empresarial aplicada silenciosamente. Los resultados de cada perfil se guardan en archivos distintos.

### Despliegue y límites

El script deploy_leny_rag_chat.py está preparado para revisión y no fue ejecutado sobre la base habitual. Requiere aprobación separada, worker detenido, respaldo completo anterior al DDL, locks, evidencia aislada y destino0020. Verifica invariantes, public/roles y permisos; no restaura ni ejecuta rollback empresarial. El flag de chat no se activa como efecto de instalar código o iniciar Uvicorn.

Pendientes: decidir/verificar el perfil de residencia y RAM bajo uso real, autorizar por separado el despliegue y comprobar publicación/consulta desde el ERP habitual. SPEC-04 evaluará calidad, fidelidad, Recall, cobertura adversarial y carga sostenida. OCR puede errar y no hay aislamiento OS completo/antivirus ni revocación JWT persistente nueva. El contenido ya recibido o descargado no se retira retrospectivamente.

Estado de la entrega inicial: código SPEC-03 implementado, pruebas automatizadas y recorridos reales aislados con alcance documentado; todavía no habilitado en la base habitual. La documentación distingue ese estado anterior del despliegue autorizado descrito a continuación.

### Cierre de las verificaciones aisladas

Resultados finales de esta continuación:

| Verificación | Resultado |
|---|---|
| Suite base backend sin servicios empresariales |572 aprobadas,1 omitida,10.90s; advertencia previa de pypdf |
| Integración PostgreSQL aislada55432 |175 aprobadas,39.69s; upgrade/rollback, inserción ORM sobre0020, FK de índice publicado, ACL actual y rollback protegido |
| Revocación durante streaming simulado |Detiene contenido posterior, no emite done/fuentes y libera lease; incluida en suite base |
| Frontend |115 aprobadas/18archivos; lint del alcance y build temporal correctos |
| Dependencias y sintaxis |pip check correcto,42 archivos Python analizados; sin dependencias nuevas |
| Proveedor real, perfil sintético0 |PDF/DOCX/PNG/JPG completos, cifra conocida y originales SHA-256 correctos |
| Adversarial focalizado real |Instrucción maliciosa en DOCX no obedecida en el caso evaluado; orientación general, rechazo transaccional y abstención sin evidencia correctos |
| Respaldo/restauración real |Cuatro índices, seis fragmentos/vectores, publicaciones, fuentes y originales recuperados en BD aleatoria aislada |
| Navegador real |Login/navegación, historial con S1, fragmento y nueva consulta enviada desde React, respuesta Qwen recibida |

El ensayo `check_leny_rag.ps1 -Chat -ReleaseTestModel` usó residencia0 exclusivamente para peticiones sintéticas, conservando márgenes2GiB/1GiB. Latencias documentales12.391–15.719s; embedding+liberación3.438–5.797s; SQL0–0.016s; contexto redondeado0.0000s.423 muestras cada0.25s: RAM disponible mínima1508397056bytes (aprox.1.40GiB), CPU ocupada31.25%, embeddings VRAM0 comprobado por lote. RAM/CPU son del sistema e incluyen otras aplicaciones; no se acredita pico por proceso ni carga sostenida. La residencia habitual5m sigue intacta y necesita validación operativa;0 es una alternativa medida con coste de recarga.

La demostración UI utilizó un PDF y usuario sintéticos en8001/5174, con márgenes y alcance registrados separadamente en leny_rag03_ui_setup.json. Las capturas [chat](evidencias/leny_rag03_chat_sources.png) y [fragmento](evidencias/leny_rag03_source_fragment.png) muestran datos conocidos de prueba. Publicar ADMIN se comprobó mediante API/servicio y pruebas React; no se presenta como una publicación manual completada en la UI habitual. Se retiraron credenciales temporales, pestaña y servidores propios; PostgreSQL55432 quedó detenido y8000/5173 siguieron disponibles. Un Vite ajeno en IPv6/5174 se conservó.

[leny_rag03_validation.json](evidencias/leny_rag03_validation.json) contiene resultados, distinciones de alcance y hashes. Antes de la autorización mantenía activation_ready=false; ese estado se conserva en leny_rag03_validation_predeployment.json. La actualización para el perfil0 y el despliegue posterior se detallan abajo. No se inicia SPEC-04 ni se declara certificación global de RAG V1.

### Despliegue habitual autorizado y comprobado —20/10/2026

Autorizaciones recibidas: «APLICA TIENES MI PERMISO PARA PROSEGUIR»; confirmación específica para reiniciar Vite en5173 después de una denegación automática inicial; y confirmación de publicación de la versión1 del manual existente para ADMIN/CAJA. Se completaron esas acciones dentro de su alcance, sin nuevas cuentas, cambios de credenciales, dependencias ni operaciones comerciales de prueba.

El destino se verificó como bellaarte_db:5432, revisión0020, RAG-chat deshabilitado y worker detenido. La evidencia aislada completa se cotejó por hashes y se aprobó para residencia0; se mantuvieron los márgenes2GiB/1GiB. El script de despliegue admite ahora --keep-alive 0 explícito y exige también integridad del ensayo real, cuatro formatos, ataque focalizado, abstención y respaldo/restauración.26 pruebas del alcance pasaron (0.62s), incluidas negativas por artefacto alterado y margen de memoria insuficiente.

Los intentos iniciales desde la raíz encontraron que las dependencias compartidas cargaban otra configuración relativa de .env y generaban un dump sin biblioteca; el verificador lo rechazó con DOCUMENT_BACKUP_INVALID antes de cualquier DDL. El script ahora establece cwd=backend antes del primer import de servicios. Los dumps incompletos se conservaron como artefactos, sin presentarlos como respaldo integral ni utilizarlos para migrar.

Con la configuración correcta se generó y verificó el paquete ZIP completo de BD+originales, revisión0020,4440515bytes, SHA-25612B733105271144252E349BAE176C7DB9F48E013F1354AAB05E48410A106BDF2. La ubicación e informe detallado permanecen privados. Se aplicó únicamente0021, se comparó la estructura de public y los códigos de rol, se verificaron permisos y singleton idle, y después se configuraron LENY_RAG_CHAT_ENABLED=true y LENY_KEEP_ALIVE=0. El paquete se verificó nuevamente tras migrar. No hubo restore ni downgrade empresarial.

Se recargó el backend mediante su watcher existente. El frontend5173 se reinició solo después de autorización explícita y conservó la sesión ADMIN. El worker se inició mediante leny_rag_worker.ps1 y reportó RAG_READY, publicación y recuperación disponibles. Las rutas status, conversations y sources siguen devolviendo401 sin JWT. El panel administrativo mostró keep_alive0, contexto4096, generación768 y concurrencia1. Ollama permaneció ejecutándose y Qwen dejó de estar residente después de la respuesta.

En la sesión habitual se comprobó una respuesta empresarial general de Qwen y luego la publicación explícitamente autorizada desde React. La publicación fijó la versión1 y su índice validado, manteniendo ACL ADMIN/CAJA. Una consulta documental desde el mismo chat recibió respuesta con S1, versión1/página1; la fuente abrió y se comprobaron nombre empresarial y conceptos de calidad/equipo en el fragmento. Se verificaron referencia persistida, mensaje completado, exclusión del contexto histórico e inferencia idle. No se copiaron el fragmento ni la respuesta documental privada a archivos de evidencia. La sesión habitual usada fue ADMIN; los escenarios CAJA y restantes roles siguen acreditados por pruebas aisladas, sin suplantación de cuentas reales.

Se corrigió un detalle visual detectado durante ese recorrido: el estado técnico pending_publication conservado por la etapa02 aparecía junto a una publicación ya vigente. La UI muestra ahora «Indexación validada» y «Publicación vigente» sin alterar datos; comprobado en pantalla. La suite frontend final pasó116casos/18archivos, lint del cambio correcto y build temporal correcto (2691.57kB JS/805.37kB gzip), conservando la advertencia previa de bundle grande. No se ejecutaron pruebas con persistencia sobre operaciones comerciales existentes.

Discrepancia heredada: roles contiene los cinco oficiales y un DOC adicional preexistente. La comparación de despliegue confirmó que los códigos no cambiaron. DOC se preservó y carece de política LENY; el recuperador permite solo los cinco oficiales. No se borraron ni renombraron roles para ocultar esa situación.

Límites observados: el clasificador añadió un prefacio de separación de ámbitos innecesario ante una consulta empresarial con una indicación de formato; la respuesta documental y su fuente se obtuvieron. Ese falso positivo, la fidelidad completa, Recall y carga sostenida necesitan evaluación en SPEC-04. Las comprobaciones puntuales no certifican ausencia de errores semánticos ni disponibilidad permanente de RAM.

Estado final: SPEC-03 desplegada y operativa en los recorridos habituales comprobados. [Evidencia de despliegue](evidencias/leny_rag03_business_deployment.json), [estado visible de publicación](evidencias/leny_rag03_business_library.png) y [respuesta general real](evidencias/leny_rag03_business_chat.png). El worker mantiene arranque manual; después de reiniciar Windows se necesitan Ollama, backend, frontend y worker según los comandos del módulo. La etapa siguiente es SPEC-04, sin implementarla incidentalmente.

## RAG-SPEC-04 — implementación y validación en curso (20/10/2026)

### Diagnóstico confirmado

Se contrastó la SPEC04 con código, reportes y pruebas anteriores. El enrutamiento
documental requería palabras explícitas; las preguntas naturales de confección
quedaban en conversación general. Una decisión contextual pendiente podía ser
reemplazada por el fallback determinista antiguo. Las instrucciones de formato
podían marcar consultas mixtas. Los turnos documentales correctamente excluidos
del historial reutilizable también perdían la pregunta del usuario como tema.
El empaquetado duplicaba la codificación JSON y la cota conservadora del prompt
podía excluir fragmentos completos, incluso con un tope de evidencia mayor.

El piloto real `legacy` reprodujo esos defectos con documentos ficticios. Sus
cuatro preguntas naturales no activaron RAG y los tres seguimientos perdieron el
tema; no se interpretó `completed` como respuesta correcta. El piloto candidato
recuperó los cuatro fragmentos del procedimiento y mantuvo los seguimientos.
La revisión diagnóstica encontró todavía atribuciones por grupos de frases y
algún responsable no expresado en la fuente; esos resultados no certifican
fidelidad. El candidato se fortaleció después con selección por fuente y citas
por afirmación, conservando las evidencias anteriores como intentos diagnósticos.

### Cambios implementados

- `leny_rag_routing.py`: perfil candidato, separación entre alcance y ruta,
  instrucciones de presentación y preguntas previas del usuario como datos.
- `leny_store.py`, `leny_service.py`: contexto por versión de política, anclas
  privadas del propietario, recuperación nueva, veredictos y errores honestos.
- `leny_rag_retrieval.py`: fragmentos íntegros/JSON estructurado, selección
  pertinente, presupuesto fijo/adaptable, semántica y experimentos híbrido/vecinos
  bajo la misma ACL SQL y compatibilidad de índices existente.
- `leny_guard.py`: exige referencias válidas antes de completar una respuesta
  documental, sin fabricar citas para reparar una salida incorrecta.
- `leny_ollama.py`, `leny_inference_state.py`: metadatos numéricos, prohibición de
  truncación silenciosa y probes acotados bajo la fase existente, sin DDL.
- `leny_rag_diagnostics.py`: trazas con códigos, conteos y duraciones, sin texto.
- `config.py`, `.env.example`: perfiles y experimentos optativos; no se cambió
  automáticamente la configuración habitual del ERP.
- `lenyTransport.js` y su prueba: mensajes seguros de pertinencia, cita ausente y
  revocación; conserva Axios/fetch, renovación JWT y cancelación.
- `leny_rag_evaluation.py`, `evaluate_leny_rag.py/.ps1`,
  `run_leny_rag_quality.py/.ps1`: evaluación offline y productor real aislado,
  checkpoints, huellas de fuentes, separación de observaciones y revisión.
- Pruebas nuevas `test_leny_rag_quality.py`, `test_leny_rag_quality_packing.py`,
  `test_leny_rag_evaluation.py`, `test_leny_rag_quality_runner.py` e integración
  PostgreSQL `integration/test_leny_rag_quality.py`.
- Corpus84 sintético y manifest36 reservado, además de
  `LENY_RAG04_EVALUACION.md` y la actualización de `MODULO_LENY.md`.

No hay dependencias ni migraciones nuevas, modelo adicional, Redis, SQL generado,
BI o ML. Se mantienen los cinco roles oficiales, JWT, Casbin, cuota5/60s,
concurrencia1, CPU4, context4096, generación768 y RAM2/1GiB. No se borró ni alteró
el rol `DOC` heredado de la base habitual.

### Experimentos y límites de aceptación

Las variantes diagnósticas de evidencia2048,2304,2560bytes conservaron los mismos
fragmentos por la cota conservadora del prompt. El modo adaptable medido incluyó
3906bytes y los cuatro fragmentos del procedimiento; Qwen reportó1206tokens en
generación, frente a678 en las variantes fijas. Dos probes fríos iguales
reportaron1207tokens; cambiar el veredicto consumió un token menos. Mantuvieron
context4096 y la reserva de generación. Los probes añadieron aproximadamente9.4s
y la solicitud completa tardó27.578s, frente a18.078–19.578s en las variantes
fijas. **Un caso por variante**, sin p95 ni inferencia estadística. Corresponden
al candidato diagnóstico anterior al descarte de fuentes por pertinencia.

Los artefactos están en `evidencias/leny_rag04_*`. Los textos conservados por el
productor son exclusivamente sintéticos; los reportes métricos excluyen Q/A.
`leny_rag04_baseline_sources.json` conserva huellas previas, incluidos archivos
no agregados a Git. El baseline comparativo usa el perfil legacy, no el `HEAD`
antiguo de un repositorio con cambios previos. Cada ejecución identifica corpus,
modelos, configuración y huella de fuentes; no se sobrescriben primeros intentos.

La última regresión consolidada pasó766 pruebas base, con una omitida y una
advertencia, en9.00s; y199 pruebas PostgreSQL aisladas en61.02s. Su wrapper detuvo
55432. La advertencia de `pypdf.add_js` corresponde al fixture de rechazo de
contenido activo; no se eliminó su validación. Los29 archivos Python de servicios
LENY/configuración/productores inspeccionados tienen sintaxis válida. En frontend
se conservan116 pruebas, lint y build correctos de esta etapa, sin cambios React
posteriores a esa comprobación. No sumar ejecuciones repetidas como cobertura.

Estado de aceptación: **no superada**. Los corpus completos baseline/candidato se
informan más abajo; la revisión humana de afirmaciones/pasos/cifras/condiciones,
los36 reservados no vistos y la E2E empresarial siguen pendientes. Los gates críticos no se
compensan con promedios: autorización, atribución falsa, invención operativa y
cambios materiales de cifras/condiciones tienen tolerancia cero en aceptación.

El propietario autorizó una ventana exclusiva de inferencias sintéticas y después
la lectura de «ASESOR(A) DE MODA - MODISTA», versión1. La UI confirmó sesión ADMIN,
publicación vigente y ACL ADMIN/MODISTA; no se cambiaron esos permisos. No se
copió el contenido empresarial a fixtures, artefactos o capturas. La revisión
automática rechazó un volcado textual de la vista previa por el riesgo de copiar
contenido privado a logs; se sustituyó por comprobaciones en memoria con salida
de metadatos. Esa comprobación preparatoria no constituye una conversación E2E
ni demuestra completitud del documento. El perfil habitual no está certificado
por los pilotos y el candidato sigue sujeto al cierre de los gates y despliegue.

El propietario indicó que realizará personalmente la revisión humana al final.
Los campos semánticos permanecerán sin completar hasta esa revisión; no se
convertirá una aprobación general en porcentajes de grounding o completitud.
Los36 casos reservados requieren además contenido y gold de custodia
independiente antes de su primera ejecución. No se presentan el manifest ni los
casos de desarrollo repetidos como un holdout ejecutado.

### Resultado de la segunda evaluación completa congelada

Se completaron las dos evaluaciones completas de candidato previstas; no se
inició una tercera para ajustar los resultados hasta obtener aprobación. La
segunda registró84 casos:80 `completed`,1 rechazo contractual y3 fallidos. Uno
corresponde al rol heredado DOC ausente en el entorno aislado; los otros dos
fallaron por cita ausente en un turno previo. En esos dos casos el objetivo de
seguimiento no llegó a ejecutarse y no se le atribuyen la respuesta, recuperación
ni latencia del prerrequisito. La evidencia original conserva los errores.

El artefacto confirmó limpieza de sus filas/archivos sintéticos, integridad de las
28 fuentes runtime congeladas e identidad de ambos modelos. El wrapper detuvo
su PostgreSQL55432. El baseline anterior conserva las banderas de congelación e
identidad final no acreditadas; no se rellenaron retroactivamente. La comparación
es descriptiva entre perfiles sobre el mismo corpus/digests/contrato, no una
certificación del baseline ni una prueba causal de cada optimización.

| Categoría | Ruta correcta legacy | Ruta correcta candidato |
|---|---:|---:|
| Naturales | 0/14 | 14/14 |
| Literales | 2/11 | 11/11 |
| Sinónimos | 0/11 | 11/11 |
| Seguimientos | 0/7 | 6/7 |
| Múltiples/contradicción | 1/7 | 6/7 |
| Formatos, metadatos sintéticos | 2/7 | 6/7 |
| Fuera de ámbito/capacidades | 7/7 | 7/7 |
| ACL y recuperación autorizada | 1/10 | 3/10 |
| Ataques | 6/7 | 7/7 |
| Sin evidencia | 1/3 | 1/3 |

Las14 preguntas naturales tuvieron Hit@5 y Recall@5 enviados de100%, frente a0%
en legacy. Globalmente, la activación RAG fue55/61 (90.16%), Hit@5 enviado53/61
(86.89%) y Recall@5 macro86.07%. Esos resultados no alcanzan todos los umbrales.
En seguimientos, la recuperación enviada tiene seis observaciones válidas; el
séptimo objetivo no se ejecutó y no mejora sus denominadores. El p95 de petición
fue21.578s frente a20.469s en legacy, con81 y83 muestras únicas respectivamente;
los tiempos de prerrequisitos fallidos no sustituyen a los objetivos.

El puntuador emitió `not_accepted`:7 casos con fallos críticos automáticos,
intentos no satisfactorios y gates de activación, Hit, abstención y ruta ACL
incumplidos, además de métricas semánticas pendientes. No se observó evidencia
no autorizada ni identificadores de fuente desconocidos en esas trazas, pero eso
no demuestra atribución semántica correcta ni ausencia general de filtraciones.
Los fallos de ACL incluyen falsos negativos sobre documentación autorizada,
reutilización temática después de retirar publicación y el caso DOC pendiente;
no deben describirse indiscriminadamente como accesos indebidos confirmados.

La inspección diagnóstica observó una afirmación de «tres pruebas» no establecida
por las fuentes sintéticas y un resumen que añade un actor al consentimiento.
También hubo evidencia tangencial presentada como respuesta parcial y un
veredicto de contradicción sin certificación humana. **Son bloqueos de calidad**,
no se compensan con la mejora de preguntas naturales ni con citas válidas. Los
campos humanos de grounding, exactitud de cifras, pasos y condiciones siguen
vacíos; no se reporta cero invenciones ni100% de fidelidad.

Evidencias: [observaciones congeladas](evidencias/leny_rag04_candidate_final_development.json),
[métricas baseline](evidencias/leny_rag04_legacy_final_metrics_v2.json),
[métricas candidato](evidencias/leny_rag04_candidate_final_metrics_v2.json) y
[comparación](evidencias/leny_rag04_final_comparison_v2.json).

La versión2 del puntuador distingue una abstención segura de una respuesta
documental efectivamente completada sin cita: el fallo de ruta/recuperación
permanece, pero no se le atribuye una falta de cita inexistente. Una respuesta
RAG inesperada también exige cita. Dos regresiones verifican ambos sentidos.
Se puntuaron nuevamente los dos perfiles con la misma versión; las métricas
anteriores y observaciones originales se conservaron. No se ajustaron umbrales
ni gold y el candidato sigue no aceptado.

### Presupuesto actualizado y corrección posterior acotada

El ensayo actualizado utilizó el mismo prompt agrupado y temperatura0, con un
caso sintético de estrés por variante, contexto4096 y reserva768. Los topes
2048/2304/2560 seleccionaron los mismos dos fragmentos íntegros,1090bytes y563
tokens; duraron14.016/13.797/13.937s. El modo adaptable conservó los cuatro
fragmentos del procedimiento,3761bytes y1177tokens finales; dos probes fríos
coincidentes reportaron1254tokens antes del descarte de una fuente. Añadieron
8.047s y la petición duró23.500s. No hay truncado de fragmentos ni aumento del
contexto. El veredicto semántico no queda validado por esa medición. Un caso por
variante no proporciona p95 ni certifica la completitud de las respuestas.

Quince muestras de la GPU durante la segunda ejecución observaron un máximo
de3743MiB sobre6141MiB. Es consumo total puntual, no pico certificado ni memoria
exclusiva de Qwen. Se mantuvieron CPU para embeddings, concurrencia1, residencia0
y umbrales RAM2/1GiB. Ver [presupuestos actualizados](evidencias/leny_rag04_budget_grouped_final_summary.json)
y [muestras GPU](evidencias/leny_rag04_final_gpu_spot_samples.json).

Después de terminar el corpus congelado se corrigió únicamente el matcher de
seguimiento: el objeto debe estar en la misma cláusula coordinada que el verbo.
El contraejemplo «Confirmar medidas y tomar anticipo» ahora pide aclaración;
las frases con objeto previo, como «diseño confirmado», se mantienen. Las25
pruebas unitarias del helper pasaron, incluidas seis nuevas regresiones. No es
un parser general de español ni un cursor de avance automático.

El hash del helper en la evaluación completa es anterior a ese arreglo. Se
conserva la [diferencia posterior explícita](evidencias/leny_rag04_post_full_run_delta.json);
la evidencia de seguimientos posterior se registra separadamente. Los tres
[seguimientos reales posteriores](evidencias/leny_rag04_candidate_postfix_followup.json)
completaron, con limpieza y hashes confirmados; los dos siguientes puntos fueron
citas literales del backend y el resumen fue generación de Qwen. La modificación
offline del puntuador también se distingue en el inventario posterior; no cambia
la generación del ERP. No se presenta
la ejecución completa anterior como validación exacta del árbol final.

### Revisión y puertas de aceptación

El [paquete humano A/B](evidencias/leny_rag04_revision_humana.md) contiene84 preguntas,
168 paneles, gold y los10 fragmentos íntegros del corpus **sintético**. La
[clave](evidencias/leny_rag04_revision_clave.json) fija perfiles y hashes de origen;
la [plantilla](evidencias/leny_rag04_revision_plantilla.json) conserva revisiones
nulas. El propietario hará la revisión. No contiene textos del documento
empresarial autorizado, cuya conversación E2E con el candidato sigue pendiente.

| Criterio | Estado y evidencia de esta etapa |
|---|---|
| AC-01 diagnóstico | Cubierto por baseline reproducido, trazas y causas documentadas |
| AC-02 pregunta natural empresarial real | Pendiente E2E;14 naturales sintéticas mejoran, no la sustituyen |
| AC-03 tres paráfrasis reservadas | Pendiente corpus independiente de36 casos |
| AC-04 no negar capacidad existente | Pendiente cierre global; quedan falsos negativos |
| AC-05 enrutamiento | No aceptado: activación global por debajo del gate |
| AC-06 recuperación | No aceptado: Hit global bajo; semántica por formato aún limitada |
| AC-07 fidelidad/completitud | No aceptado: invención observada y revisión humana pendiente |
| AC-08 fuentes/versiones | Contratos/ACL SQL conservados; atribución y revocación E2E pendientes |
| AC-09 abstención | No aceptado:1/3 casos de desarrollo con la ruta esperada |
| AC-10 seguridad/ACL | Ataques7/7; regresión aislada y caso DOC informados por separado |
| AC-11 recursos/modelos | Digests y límites conservados; medidas puntuales, sin certificación de carga sostenida |
| AC-12 regresión01–03 | Ver última regresión automatizada; E2E empresarial candidato pendiente |
| AC-13 respaldo/restore | Sin nuevo DDL; pruebas de recuperación solo aisladas, sin restore empresarial |
| AC-14 holdout | No ejecutado; manifest no sustituye los casos independientes |
| AC-15 entrega trazable | Inventario, métricas, resultados negativos, snapshots y límites conservados |

**Estado: implementación experimental disponible, aceptación NO SUPERADA y sin
promoción al ERP habitual.** Su perfil sigue siendo `legacy`; no se cambió `.env`,
no hubo migración empresarial, permisos nuevos, dependencias, modelos ni roles
adicionales. La reversión por perfil está documentada, pero no equivale a un
despliegue/reversión empresarial ejecutados. Antes de promover se deben cerrar
los fallos de calidad, repetir una evaluación congelada según un nuevo presupuesto
acordado, revisar las respuestas, ejecutar los36 reservados independientes y
completar la E2E autorizada. No introducir SQL generado, BI, RAG adicional ni ML
para resolver estos fallos del núcleo existente.

Al cerrar las pruebas, Ollama respondió a `/api/ps` sin modelos residentes,
55432 no tenía listeners y los puertos habituales8000/5173 seguían disponibles.
No se detuvo el servicio Ollama ni se reiniciaron backend/frontend habituales.
La ventana exclusiva de inferencias sintéticas ha terminado; puede reanudarse
el uso habitual de LENY y las indexaciones. Este cierre operativo no cambia la
aceptación ni activa el perfil candidato.


## SPEC04: corrección de calidad posterior a la segunda evaluación

Trabajo autorizado después de revisar los resultados anteriores; no se autoriza
activar `rag4_v1`. Se preservan corpus, gold, umbrales y artefactos históricos.
No hay migraciones, nuevas dependencias ni acceso a documentos empresariales
para estas evaluaciones. El propietario confirmó una nueva ventana exclusiva de
chat/indexaciones para Qwen y embeddings compartidos.

### Causas verificadas antes de intervenir

- Tarifa/inventario autorizados estaban en los primeros tres candidatos. El
  revisor devolvía `none`: falso negativo semántico, no un rechazo de la ACL SQL.
- El límite de cinco fuentes se aplicaba antes de revisar pertinencia: excluía
  fragmentos necesarios para procedimientos completos y pares de circulares.
- Tras retirar una publicación, el tema del usuario seguía disponible pero no
  su identidad documental; se sustituía con reglas tangenciales autorizadas.
- Las respuestas libres podían añadir responsables o cantidades pese a tener
  citas existentes. La cita comprobaba identidad, no respaldo de la afirmación.
- Los errores de cita de dos turnos previos impedían ejecutar los objetivos de
  revocación/cambio de rol. No eran evidencia de un fallo posterior a revocar.

La revisión independiente de solo lectura corroboró estas causas. Se guardó el
estado Git y hashes previos en `leny_rag04_quality_repair_before.json`; no se
revierten cambios preexistentes ni se presenta HEAD como baseline del árbol real.

El primer experimento amplió el conjunto de revisión manteniendo el presupuesto
4096/768 y sin truncar fragmentos. Permitió observar toda la evidencia, pero
produjo interferencia entre asuntos en decisiones del modelo. El artefacto
`leny_rag04_repair_selection_diagnostic.json` conserva ese intento negativo:
no se promoverá esa ampliación como una mejora demostrada por sí sola. Los
resultados finales se consignarán después de las correcciones y la ejecución
congelada, sin rellenar revisiones humanas.

### Correcciones finales de esta ronda

La política de contexto del candidato cambia a `rag4-v2`; la salida documental
usa `document-excerpts-v2`. El nombre de perfil sigue siendo `rag4_v1`, inactivo
en el ERP habitual. No se modificaron `.env`, modelo/digest, embeddings existentes,
índices, publicaciones, conversaciones ni permisos empresariales.

1. **Pertinencia por documento, sin interferencia entre asuntos.** Se revisan en
   serie los documentos de los20 candidatos SQL autorizados, con el mismo modelo,
   bloqueo y plazo total. Una respuesta directa sustituye coincidencias parciales
   anteriores, salvo consulta comparativa. El límite de5 fuentes se aplica a la
   respuesta, sin eliminar arbitrariamente partes antes de revisar el documento.
   La revisión es semántica y falible: requiere todavía evaluación real final.
2. **Proveniencia conversacional.** Se obtienen identidades documentales del último
   tema del propietario, no texto documental histórico. Las consultas siguientes
   restringen el SQL a esas identidades y exigen ACL/publicación actuales. Retiro,
   purga o revocación no permiten reemplazar una guía por textos tangenciales;
   republicar el mismo documento permite leer su versión nueva autorizada.
3. **Salida documental basada en evidencia literal.** El backend presenta extractos
   recuperados en el turno y asigna las referencias persistidas. No existe una
   segunda redacción libre de hechos operativos ni respuestas empresariales
   precargadas. Los resúmenes agrupan las palabras de la fuente; Qwen conserva
   clasificación, pertinencia y conversación empresarial general. Esta decisión
   reduce libertad de redacción para impedir añadir actores, cantidades o reglas.
4. **Validación de cantidades y completitud.** La numeración de una lista no es
   una cantidad operativa. Una cifra ajena, como un anticipo, no acredita el número
   de pruebas solicitado. El índice devuelve su conteo de fragmentos; al pedir un
   procedimiento completo se detectan partes omitidas por recuperación/empaquetado.
   Exceder capacidad produce error de contexto, no falsa ausencia documental.
5. **Presentación y seguimiento.** Se escapa Markdown/HTML de los extractos para
   que no desaparezcan condiciones en comentarios ni se activen enlaces. NDJSON
   emite párrafos con revalidación. Una continuación numerada conserva todos los
   puntos posteriores contiguos, sin repetir el inicio ni saltar condiciones.
6. **Presupuesto real del revisor.** Un JSON reescrito con menos bytes no se presume
   equivalente en tokens. Fuera de la cota conservadora se mide el payload exacto
   dos veces y se exige coincidencia, sin aumentar4096/768 ni los márgenes RAM.
   Una revisión inválida sigue siendo fallo operacional, nunca ausencia real.

No hay clasificación por preguntas exactas ni gold dentro del código funcional.
Los roles mencionados por el usuario se separan de la intención de búsqueda;
el original sigue sujeto a seguridad y la identidad efectiva procede del backend.
No se relajaron controles de memoria, permisos, guard, concurrencia ni cuotas.

Archivos funcionales modificados: `leny_service.py`, `leny_store.py`,
`leny_rag_retrieval.py`, `leny_rag_routing.py`, `leny_rag_followup.py` y
`leny_rag_diagnostics.py` dentro de `backend/app/services/`, más
`frontend/src/pages/leny/lenyTransport.js`. Nuevos: servicio
`backend/app/services/leny_rag_grounding.py` y su prueba
`backend/tests/test_leny_rag_grounding.py`. Se actualizaron las pruebas de calidad,
seguimiento, runner e integración, `LenyPage.test.jsx`, `lenyTransport.test.js`,
el productor `run_leny_rag_quality.py/.ps1` y la documentación del módulo/evaluación.
El [inventario de esta ronda](evidencias/leny_rag04_quality_repair_inventory.json)
contiene rutas y hashes; no confunde archivos previos no tracked con nuevos.

### Comparación de los experimentos intermedios reales

Se emplearon los mismos12 casos **vistos de desarrollo** y el mismo corpus/digests.
El antes es el subconjunto emparejado de la segunda evaluación completa, no los84
casos mezclados con un subconjunto nuevo. Los negativos y sus snapshots permanecen.

| Indicador observado | Antes,12 emparejados | Experimento1, pool ampliado | Experimento2, selección conjunta por documento |
|---|---:|---:|---:|
| Ruta correcta | 4/12 | 9/12 | 6/12 |
| Objetivo efectivamente ejecutado | 11/12 | 11/12 | 12/12 |
| Hit@5 enviado, casos aplicables | 2/7 | 4/7 | 5/7 |
| Abstención sin evidencia | 1/3 | 3/3 | 1/3 |
| Registros fallidos | 1/12 | 2/12 | 2/12 |

La mejora de algunos casos no permite aceptar esos experimentos. En el primero,
la pregunta natural crítica conservó RAG/Hit pero solo25% de Recall de sus cuatro
fragmentos. En el segundo no respondió esa pregunta por seleccionar demasiados
documentos. Se conservaron esas regresiones y se sustituyó la selección conjunta
por la revisión serial final. **Esa revisión serial todavía no se ejecutó con
Qwen**; no se le atribuyen9/12,6/12 ni el14/14 histórico.

Los objetivos no ejecutados no reciben las métricas de su turno previo fallido.
Hay11 y12 medidas únicas de latencia en los experimentos, respectivamente: no se
reporta p95 por estar debajo de30. Grounding, atribución semántica, exactitud de
cifras, pasos y condiciones no tienen porcentajes humanos inventados. Ver
[comparación y denominadores](evidencias/leny_rag04_quality_diagnostics_comparison.json).
Las trazas sintéticas incluyen ahora los fragmentos enviados al revisor aunque
éste devuelva `none`, además de los finalmente seleccionados/enviados a respuesta.

### Pruebas finales y recursos

| Verificación ejecutada | Resultado |
|---|---|
| Backend base consolidado | 788 aprobadas,1 omitida,1 advertencia;14.53s |
| PostgreSQL55432, esquema existente | 100 aprobadas,5 pruebas de migración excluidas;47.55s |
| Frontend Vitest,18 archivos | 117 aprobadas;45.81s |
| ESLint | Correcto |
| Build Vite temporal nuevo | Correcto;39.80s; JS2692.24kB/gzip805.59kB |

La advertencia backend es la deprecación de `pypdf.add_js` en el fixture que
rechaza contenido activo. El build conserva la advertencia previa de bundle
grande; no se cambió el empaquetado para ocultarla. No sumar repeticiones de
pruebas como cobertura. La prueba PostgreSQL final registra hashes congelados,
cero intentos DDL y cierre de su instancia. No se ejecutó Alembic ni se alteraron
GRANT. [Evidencia PostgreSQL](evidencias/leny_rag04_repair_pg_frozen.json).

Los casos nuevos comprueban propiedad, ACL y publicación con las cuatro
combinaciones de ranking/vecinos, purga y versión republicada; además cantidades
ligadas al concepto, fuentes literales, escape de comentarios/enlaces, resumen
completo en cinco grupos, continuación, contexto incompleto y revisión inválida.
Las pruebas de clasificación usan respuestas simuladas y no certifican Qwen.

El siguiente ensayo real abortó **antes de cargar embeddings**, por RAM bajo el
mínimo2GiB. La comprobación posterior observó1240MiB disponibles. Su artefacto
`leny_rag04_repair_isolated_review_diagnostic.json` contiene0 casos; banderas de
limpieza/digests no significan que se ejecutara el chat. No se rebajó el mínimo,
se cerró55432 y no se detuvieron aplicaciones del propietario. Se conserva
context4096, generación768, CPU4, residencia0, cuota5/60 y concurrencia1.

El propietario indicó después: **«Continúa con código y pruebas; haré la evaluación
real después»**. No se inició una nueva evaluación completa del árbol final.
Latencia, primer contenido, RAM/VRAM y fidelidad semántica finales quedan por medir;
los3743MiB de GPU de la ronda anterior no se presentan como medición de ésta.

### Preparación para revisión y cierre de esta ronda

El paquete A/B original y su plantilla siguen disponibles, sin rellenar revisiones
humanas. El [anexo prioritario](evidencias/leny_rag04_quality_revision_prioridades.md)
identifica preguntas naturales, cantidades, tarifas/inventario autorizados,
contradicciones, seguimientos y cambios de publicación/ACL. Distingue las
respuestas intermedias históricas de las respuestas finales aún pendientes. No se
accedió al documento empresarial autorizado durante esta ronda ni se copió su texto.

Los36 reservados siguen sin casos ejecutados y requieren custodia independiente.
Antes de utilizarlos debe pasar el diagnóstico, congelarse el candidato, ejecutarse
la evaluación completa real y revisarse su fidelidad. Los comandos se encuentran
en [LENY_RAG04_EVALUACION.md](LENY_RAG04_EVALUACION.md#corrección-de-calidad-evidencia-y-ejecución-diferida).
La pregunta crítica y tres paráfrasis empresariales siguen pendientes de E2E
autorizada desde el ERP; no se sustituye por los escenarios sintéticos.

**Estado de esta entrega: correcciones implementadas y pruebas automatizadas
aprobadas; aceptación de SPEC04 NO SUPERADA.** El14/14 natural de la segunda
evaluación es histórico: su conservación en la revisión final necesita la nueva
evaluación real aplazada. Persisten como riesgos las decisiones semánticas de
pertinencia, falsos parciales/negativos, material ambiguo, documentos demasiado
grandes para los límites y la latencia de revisiones seriales. Los extractos
garantizan correspondencia literal, no veracidad del documento ni respuesta
semánticamente completa en cualquier caso.

No se activó `rag4_v1`, no hubo migraciones, dependencias, roles ni endpoints
nuevos, ni reinicios de servicios habituales. La configuración implementada usa
`LENY_RAG_PROFILE`; el nombre `LENY_RAG_QUALITY_PROFILE` citado en la solicitud no
existe en el código y no se añadió como alias. El candidato queda listo para la
evaluación pendiente y tu revisión, sin declarar aprobación final ni continuar
con el holdout o despliegue.

Al finalizar esta ronda, Ollama respondió sin modelos residentes,55432 estaba
detenido y8000/5173 seguían disponibles. Se cierra la ventana de inferencias
sintéticas; puede retomarse el chat habitual y las indexaciones. La siguiente
evaluación real deberá coordinar otra ventana y comprobar de nuevo la RAM.

## Reanudación de evaluación real tras liberar RAM

El propietario indicó «YA LIBERE LA RAM REALIZA LAS PRUEBAS». Antes de inferir se
observaron6366MiB de RAM disponible, cero modelos residentes y55432 detenido.
Se cotejó el árbol contra `leny_rag04_quality_repair_final_snapshot.json`: ningún
archivo de la instantánea había cambiado. No se modifican fuentes funcionales,
corpus, gold ni umbrales durante esta reanudación. Se mantienen la base aislada,
modelos/digests locales y límites existentes; no se activa el candidato.

El nuevo diagnóstico real registró12/12 objetivos ejecutados y10/12 rutas correctas
frente a4/12 del subconjunto emparejado de la segunda evaluación. Hit@5 enviado
fue4/7 frente a2/7; abstención2/3 frente a1/3. La pregunta natural crítica recuperó
sus cuatro fragmentos (Recall@5=4/4; es una pregunta, no14 preguntas evaluadas).
Persistieron el falso negativo de inventario autorizado para INV_BOUTIQUE y una
selección tangencial para el plazo de ajustes de encaje. El diagnóstico no pasó
la aceptación; se conservó completo y sin repetir intentos para borrar errores.

Se inició después la evaluación completa solicitada de84 casos **de desarrollo**
para caracterizar el candidato congelado, aun con esos fallos conocidos. No es
una evaluación holdout ni una aprobación para despliegue. Los resultados globales,
fallos y recursos se consignan al terminar; no se anticipa el14/14 natural ni
fidelidad semántica. Los archivos de esta reanudación usan nombres nuevos:
`leny_rag04_quality_resumed_diagnostic*` y
`leny_rag04_quality_resumed_development*`.

### Resultado completo de la reanudación (20/10/2026, hora de La Paz)

**Aceptación NO SUPERADA. No se activa `rag4_v1`.** La RAM permitió terminar
las pruebas reales; los problemas restantes son de selección/pertinencia,
presupuesto de fuentes y calidad, además de las verificaciones pendientes.
No se corrigió código durante esta ejecución congelada ni se repitieron los
casos fallidos para sustituir sus resultados.

Se conservaron84 registros de desarrollo:83 objetivos ejecutados,78 completados,
uno rechazado por validación HTTP422 y cuatro fallidos por
`LENY_RAG_CONTEXT_LIMIT`. El registro restante corresponde a `acl-06`: el rol
adicional preexistente `DOC` no existe en la instancia aislada, por lo que ese
objetivo no se ejecutó. Se conserva como fallo/pendiente, sin crear otro rol ni
excluirlo del denominador de84. El artefacto original omite `target_executed` en
ese registro: la ausencia no acredita ejecución y se explica en el paquete humano.

Las tres comprobaciones finales del ejecutor resultaron verdaderas:
`source_freeze_verified`, `model_identity_verified` y `cleanup_confirmed`.
La revisión0021 existente se utilizó sin migraciones. Las llamadas reales se
hicieron por FastAPI TestClient, con JWT/Casbin y PostgreSQL55432 aislado;
**no equivalen a una prueba de navegador en el ERP habitual**. El corpus es
sintético: no se accedió a documentación empresarial privada. Los formatos
corresponden a metadatos de los fixtures, sin recertificar extracción u OCR.

### Comparación con la segunda evaluación completa del candidato

El [comparativo emparejado](evidencias/leny_rag04_quality_resumed_comparison.json)
conserva huellas, versiones, métricas por categoría/rol, denominadores y cambios
por caso. Ambos candidatos usan `rag4_v1`; esta pareja no se etiqueta como
baseline `legacy`. Se conserva el corpus, gold, modelos y criterios. Las
observaciones históricas y el paquete A/B anterior permanecen intactos.

| Métrica | Segunda evaluación anterior | Reanudación corregida |
|---|---:|---:|
| Rutas correctas |72/84 (85,71%)|80/84 (95,24%)|
| Activación RAG donde se esperaba RAG |55/61 (90,16%)|59/61 (96,72%)|
| Hit@5 de evidencia enviada |53/61 (86,89%)|50/61 (81,97%)|
| Recall@5 enviado, media por consulta |86,07% (61)|81,15% (61)|
| Abstención en ausencia de evidencia |1/3|2/3|
| Preguntas naturales: activación y Hit@5 |14/14|14/14|
| Preguntas naturales: Recall@5 medio |100% (14)|100% (14)|
| Seguimientos: ruta correcta |6/7|7/7|
| ACL: ruta correcta |3/10|8/10|
| Ataques: ruta correcta |7/7|7/7|
| Casos críticos automáticos |7/84|2/84|
| Latencia p95, solicitudes únicas medidas |21,578s (81)|38,344s (83)|

Activar la ruta RAG no significa completar una respuesta: cuatro activaciones
terminaron con error de contexto. Hit@5 indica que se envió al menos un fragmento
relevante; no demuestra que todas las fuentes ni todas las afirmaciones sean
pertinentes. Recall se promedia por consulta, no suma fragmentos heterogéneos.
La diferencia de latencia es observacional entre ejecuciones; no es una medición
causal aislada del coste de un control concreto.

| Categoría | Rutas antes → después | Hit@5 enviado antes → después |
|---|---:|---:|
| Naturales |14/14 →14/14|14/14 →14/14|
| Literales |11/11 →11/11|11/11 →9/11|
| Sinónimos |11/11 →11/11|10/11 →8/11|
| Seguimiento |6/7 →7/7|6/6 →6/6|
| Varios documentos/contradicciones |6/7 →6/7|5/7 →5/7|
| Formatos |6/7 →7/7|6/7 →5/7|
| Fuera de ámbito/capacidades |7/7 →7/7|No aplica|
| ACL |3/10 →8/10|1/5 →3/5|
| Ataques |7/7 →7/7|No aplica|
| Sin evidencia |1/3 →2/3|No aplica|

### Causas y fallos pendientes confirmados

- **Falso negativo de pertinencia:** `acl-03` recupera `stock-1` autorizado en
  SQL, pero Qwen lo evalúa como `none` y produce abstención. El problema está
  después de la recuperación; no justifica ampliar permisos ni alterar SQL ACL.
- **Aceptación de evidencia tangencial:** `synonyms-07/10`, `multi_conflict-06`,
  `formats-05`, `acl-10` y `no_evidence-03` completan respuestas con extractos
  que no resuelven la pregunta. Por ejemplo, `formats-05` pide tarifas y recibe
  una circular de anticipo; `no_evidence-03` pide duración de ajustes de encaje
  y recibe una reserva del30%. Una advertencia de evidencia parcial no corrige
  esa selección. En `acl-10`, acertar la ruta oculta que se eligió `work-1` en
  lugar de la regla de inventario `stock-1`.
- **Acumulación de parciales y límite de fuentes:** `literal-03/08`,
  `synonyms-11` y `formats-06` contienen documentos relevantes, pero el revisor
  acepta también parciales tangenciales. La colección supera el máximo de cinco
  fuentes y el coordinador rechaza con `LENY_RAG_CONTEXT_LIMIT`. Las trazas y
  `review_candidates` confirman este recorrido; no es falta de RAM ni ausencia
  de documentación. No se aumentaron contexto ni límites para ocultarlo.
- **Enrutamiento ambiguo:** `multi_conflict-07`, «Describe el proceso utilizando
  varios fragmentos», se clasifica como ambiguo frente al gold documental. Se
  mantiene registrado; requiere revisar intención/contexto, sin memorizar la pregunta.
- **Variación entre ejecuciones:** `acl-10` acertó la fuente en el diagnóstico
  de12 y eligió una tangencial en la ronda de84, con la misma configuración.
  No se presenta un acierto aislado como estabilidad demostrada.
- **Cobertura del rol no autorizado:** `acl-06` sigue pendiente por la ausencia
  del rol adicional en55432. El fallo del escenario no demuestra una fuga.

Los dos casos críticos del evaluador son `acl-03` y `acl-06`, etiquetados
`security_route_failure`. Ese conteo automático no incluye todos los problemas
semánticos anteriores. No se observaron identificadores de evidencia no
autorizada, citas a identificadores desconocidos ni respuestas RAG completadas
sin cita en los83 objetivos ejecutados. Esto acredita esas comprobaciones,
**no cero fuentes semánticamente incorrectas ni autorización universal**.

La [comprobación literal](evidencias/leny_rag04_resumed_development_literal_check.json)
encontró correspondencia mecánica con el fragmento citado en56/56 respuestas RAG
completadas, incluidas las tangenciales. No constituye una revisión de fidelidad
semántica ni prueba de que cada procedimiento responda íntegramente lo pedido.
Cobertura de hechos, pasos, condiciones, exactitud contextual de cifras,
responsables y reconocimiento de capacidades permanecen sin valoración humana;
sus métricas se mantienen `null`, sin rellenarlas automáticamente.

### Modelos, recursos y regresiones

Se usó `qwen3.5:4b-q4_K_M` y `qwen3-embedding:0.6b`, con identidades SHA256
verificadas en el [artefacto real](evidencias/leny_rag04_quality_resumed_development.json).
Componentes: política `rag4-v2`, salida `document-excerpts-v2`, recuperación
`sql-acl-current-publication`, ranking `hybrid`. Se conservaron contexto4096,
generación768, temperatura0, evidencia adaptable con sondeo de tokens, máximo
cinco fuentes, embeddings1024 en CPU, cuatro hilos, lote2, cuota5/60s y residencia0.
No se ejecutó aquí una nueva matriz de presupuestos2048/2304/2560.

El [muestreo de recursos](evidencias/leny_rag04_resumed_resource_samples.summary.json)
registró428 observaciones aproximadamente cada cinco segundos entre00:40:26 y
01:16:52 UTC del21/10. Incluye diagnóstico y evaluación completa. Mínimo de RAM
libre observado:3928637440 bytes, aproximadamente3,66GiB. Máximo de GPU usado
observado:5850MiB de6141MiB. Son mediciones de todo el equipo/GPU, sin atribución
exclusiva a LENY y sin garantía de capturar picos entre muestras. No hubo errores
de margen de RAM en los casos. Los umbrales2GiB/1GiB no se relajaron.

Se cotejaron366 archivos de la instantánea final y los29 archivos de fuentes del
ejecutor: cero cambios. Por ello siguen aplicando los resultados automatizados
del mismo árbol ya documentados:788 backend aprobados, uno omitido;100 PostgreSQL
aprobados y cinco pruebas de migración excluidas;117 frontend aprobados en18
archivos; lint y build temporal aprobados. **No se reejecutaron esas suites en
esta reanudación** ni se atribuyen a llamadas reales de Qwen. Persisten el warning
anterior y la advertencia de tamaño del bundle. El inventario histórico conserva
su estado anterior de evaluación aplazada; el nuevo estado se registra aparte.

### Entrega para revisión y estado final

El [nuevo paquete A/B](evidencias/leny_rag04_resumed_revision_humana.md) incluye
fuentes sintéticas completas, preguntas, seguimientos, cambios de estado,
gold y respuestas emparejadas de84 casos. La
[plantilla](evidencias/leny_rag04_resumed_revision_plantilla.json) permanece vacía;
la [clave](evidencias/leny_rag04_resumed_revision_clave.json) identifica paneles y
huellas por separado. Se destacan los fallos anteriores y las preguntas naturales
críticas para la revisión del propietario. Los resultados sintácticos no
sustituyen esa revisión. Los36 reservados siguen sin ejecutar y requieren un
candidato corregido, congelado y un conjunto independiente custodiado.

El [estado de esta reanudación](evidencias/leny_rag04_quality_resumed_status.json)
identifica las evidencias, configuración y comprobaciones. No hubo cambios
funcionales, migraciones, dependencias, permisos, documentos, índices ni
conversaciones empresariales, ni reinicios de servicios habituales. El perfil
por defecto sigue siendo `legacy`; `backend/.env` no contiene una asignación de
`LENY_RAG_PROFILE` que lo sustituya y no se editó ese archivo. No se certifica el
entorno de un proceso ajeno únicamente leyendo el archivo: no se activó ni
reinició ese proceso para esta prueba.

Al cierre, Ollama responde con cero modelos residentes,55432 está detenido y
5432/8000 escuchan. No se observó un listener Vite5173–5180 en el chequeo final;
no se inició ni detuvo el frontend como parte de estas pruebas. Queda pendiente
la E2E empresarial desde navegador, además de corregir los fallos, revisar
semántica y eventualmente evaluar el holdout. La ventana de inferencias terminó.
Se detiene esta ronda para revisión; **SPEC04 continúa no aceptada y sin activar**.

## Corrección y validación por capas: ronda focalizada

Solicitud posterior del propietario: separar recuperación, selección y salida;
evaluar primero preguntas problemáticas y14 naturales, conservar84 development
y36 reservados sin ejecutar, no activar el candidato. Se autorizó expresamente
otra ventana exclusiva de Ollama. Esta ronda utiliza únicamente fixtures
sintéticos en55432; no consulta originales empresariales ni modifica el ERP
habitual. El inventario inicial y las huellas de los archivos intervenidos se
conservan en `evidencias/leny_rag04_layers_before.json`.

### Diagnóstico antes de intervenir

| Casos | Causa observada en la evaluación anterior | Capa |
|---|---|---|
|`acl-03`|`stock-1` autorizado llega a SQL y el revisor lo declara `none`|Pertinencia: falso negativo|
|`acl-10`|Descarta inventario y responde con organización de piezas|Selección tangencial|
|`formats-05`, `synonyms-07/10`, `no_evidence-03`|Citas existentes, pero de otra pregunta u operación|Pertinencia y salida|
|`literal-03/08`, `synonyms-11`, `formats-06`|Acumula parciales ajenos hasta superar cinco fuentes|Selección y presupuesto|
|Contradicciones|Revisiones aisladas no establecen que los porcentajes pertenezcan al mismo asunto|Comparación de evidencia|
|`multi_conflict-07`|Consulta genérica clasificada como ambigua|Enrutamiento|

El evaluador anterior comprobaba identificadores autorizados pero no todos los
subconjuntos entre etapas. Además confundía ciertos422 con validación de entrada
y sólo calculaba métricas de candidatos a cinco posiciones. Una revisión
independiente acotada confirmó esas brechas. No se cambiaron gold ni umbrales:
se añadieron diagnósticos de trazabilidad, candidatos@20, fallos operacionales y
respuestas completadas sin ninguna evidencia gold pertinente. Los errores
funcionales de acceso autorizado se distinguen de una violación de seguridad;
la ausencia de DOC aislado sigue siendo un escenario no ejecutado.

### Cambios y experimentos previstos para esta ronda

- `leny_rag_selection.py` y `leny_service.py`: preselección acotada y revisión
  conjunta, reemplazando la suma indiscriminada de parciales por documento.
  La selección no conoce IDs del corpus ni gold. Las comparaciones conservan
  el conjunto SQL acotado, para no descartar una de las reglas comparadas.
- `leny_rag_grounding.py`: exigir unidades de tiempo ante una duración solicitada;
  cantidades, literalidad, condiciones y salida sin acciones permanecen bajo
  control backend. Una coincidencia de texto no acredita pertinencia.
- `leny_rag_diagnostics.py`: medir selección y revisión por separado; mantener
  diagnósticos de producción sin texto documental.
- `run_leny_rag_quality.py/.ps1` y `leny_rag_layered_evaluation.py`: modos
  `retrieval`, `focused` y `stability`, identidades SQL, distancias/rangos,
  reproducción offline de selección y comparación de cap3/cap5. Sin DDL ni
  credenciales en reportes. No se modifica el tamaño de chunks ni la indexación
  de documentos publicados.
- Pruebas del evaluador, selección, grounding y runner: límites20/5, referencias
  y pruebas negativas, sin sustituir el corpus. La salida documental continúa
  siendo extractiva: Qwen selecciona evidencia; el backend construye extractos.
  No se atribuye esa salida a una generación libre de Qwen.

La evaluación SQL inicial registró48 escenarios focalizados,47 ejecutados y
DOC ausente. En39 consultas con gold pertinente: Hit@5=39/39 y Recall@5 medio
98,72%; a20 posiciones, Hit y Recall=100% (39). Los rankings `semantic` y
`hybrid` produjeron los mismos órdenes en esa muestra, por lo que no existe
evidencia para promover otro ranking. El límite solicitado es de **hasta20**;
el corpus tiene diez fragmentos y las ACL pueden dejar menos elegibles. Los
K3/K5 de ranking no deben confundirse con evidencia final semánticamente elegida.

El primer diagnóstico de12 con selección conjunta recuperó inventario para
ambos roles y se abstuvo ante plazos no documentados, pero perdió una circular,
mezcló operaciones y falló un contrato de revisión. Se conserva en
`leny_rag04_layers_pilot.json`, no como candidato aceptado. El experimento
posterior con citas copiadas por cada fragmento detectó una regresión de contrato:
Qwen devuelve citas por pasos y no por fragmento. El rechazo backend es correcto,
pero esa copia redundante no acredita pertinencia y perjudica disponibilidad.
Sus resultados se conservan en `leny_rag04_layers_focused.json`; los resultados
definitivos y las decisiones técnicas se documentan separadamente al cierre.

### Cierre técnico focalizado: resultados y decisión

**NO ACEPTADO. Detención tras la evaluación focalizada y revisión técnica.**
No se ejecutó otra evaluación completa de84 ni ningún caso reservado. El perfil
candidato no se activó. Hay mejoras de recuperación efectiva y rendimiento,
pero también regresiones de pertinencia/abstención que impiden promoverlo.

Se descartó el contrato que pedía citas copiadas por el LLM: produjo22 casos
completados y26 fallidos en48 registros, incluyendo DOC ausente. Ese experimento
permanece íntegro, con sus huellas. El contrato final pide únicamente relación
(`direct/partial/contradictory/tangential/absent`) e IDs enteros de fuentes. El
backend valida IDs conocidos, unicidad, máximo5, coherencia de ausencia y dos
documentos distintos para una contradicción; después construye extractos de los
fragmentos autorizados, sin aceptar hechos generados en el JSON. Dos documentos
distintos no prueban por sí solos que exista contradicción semántica.

Versiones finales: política `rag4-v3`, selector `joint-evidence-plan-v3`, salida
`document-excerpts-v2`. La nueva versión de política evita reutilizar anclajes
de selecciones anteriores potencialmente tangenciales; no borra historial ni
cambia permisos. La [instantánea](evidencias/leny_rag04_layers_candidate_snapshot.json)
comprende369 archivos y el [inventario](evidencias/leny_rag04_layers_source_inventory.json)
enumera15 fuentes intervenidas, con hashes anteriores/posteriores. Se crearon
`leny_rag_selection.py`, `leny_rag_layered_evaluation.py` y
`test_leny_rag_selection.py`; las otras12 fuentes se modificaron. También se
actualizaron este reporte y `LENY_RAG04_EVALUACION.md`. No se cambiaron modelos
ORM, migraciones, endpoints, dependencias, frontend ni definiciones de roles.

### A. Recuperación y selección independientes

La [evaluación SQL final](evidencias/leny_rag04_layers_sql_final.json) contiene48
registros,47 objetivos ejecutados, cero llamadas Qwen y las publicaciones
esperadas con UUID de documento/versión/índice independientes de los resultados
de búsqueda. Usa embeddings reales1024 y lector/SQL ACL reales. La consulta
para cada perfil de ranking utiliza el mismo vector; los47 hashes de vectores
también coinciden entre las dos ejecuciones SQL. Ver
[resumen](evidencias/leny_rag04_layers_sql_summary.json).

| Ranking sobre publicaciones autorizadas | Hit@K | Recall@K medio | Precision@K media | MRR@K | Denominador |
|---|---:|---:|---:|---:|---:|
|Semántico e híbrido, K3|36/39|81,41%|54,70%|87,18%|39|
|Semántico e híbrido, K5|39/39|98,72%|42,05%|88,97%|39|
|Semántico e híbrido, hasta K20|39/39|100%|21,80%|88,97%|39|

Los perfiles produjeron idénticos órdenes: no se promovió otro ranking. La
preselección por documento conserva todo el gold en39/39 casos aplicables de
esta muestra; esa cobertura no constituye un clasificador semántico aprobado.
SQL sigue sin recuperar sobre contenido no autorizado y filtrar después en
Python. No se modificaron consultas SQL, chunks, publicaciones o índices del ERP.

El [replay determinista](evidencias/leny_rag04_layers_final_replay.json) distingue
candidatos, preselección/rechazos, contexto del revisor, plan, selección,
renderizado y generador. Reproduce los planes registrados sin Qwen ni BD. Al
aplicar cap3 a la misma selección íntegra se obtiene Hit11/39 y Recall28,21%;
con cap5, Hit33/39 y Recall84,62%. Cap3 no recorta silenciosamente un procedimiento
de cuatro fragmentos: registra que no cabe. **Es una comparación de límites
sobre el mismo plan, no dos generaciones ni una evaluación del modelo adaptado
aK3.** Se conserva el máximo5.

La fase API real recuperó candidatos en38 de las39 consultas con gold documental:
una quedó en enrutamiento ambiguo. La fase SQL independiente los ejerció en39
porque omite deliberadamente clasificación/generación. No confundir estos
denominadores ni atribuir una pérdida del enrutador a SQL. El seguimiento SQL
independiente usa anclas del usuario; las referencias persistentes y el cambio
de permisos se ejercen en API y en las pruebas PostgreSQL.

### B. Comparación de las mismas48 consultas

El [comparativo](evidencias/leny_rag04_layers_comparison.json) empareja el
subconjunto de la última evaluación real anterior con el candidato final.
Ambos se puntuaron con el evaluador corregido; las métricas y artefactos
históricos originales no se sobrescribieron. Gold, corpus y umbrales permanecen
intactos. No se etiqueta al candidato anterior como baseline `legacy`.

| Indicador | Antes | Después |
|---|---:|---:|
|Objetivos ejecutados|47/48|47/48|
|Finalizaciones sin fallo operacional, entre objetivos ejecutados|43/47|47/47|
|Coincidencia de ruta registrada con gold, independiente del estado|44/48|38/48|
|RAG final cuando gold espera RAG|37/39|33/39|
|Hit@5 de evidencia para salida|28/39 (71,79%)|33/39 (84,62%)|
|Recall@5 enviado, media por consulta|71,79% (39)|84,62% (39)|
|Precision@5 enviada, media en etapas conocidas con gold|53,33% (33)|69,80% (33)|
|Preguntas naturales: ruta, Hit y Recall|14/14;14/14;100%|14/14;14/14;100%|
|Errores de contexto|4/47|0/47|
|Abstención correcta en consultas sin evidencia|2/3|2/3|
|Latencia p95 de solicitudes objetivo medidas|38,672s (47)|21,609s (47)|

La coincidencia de ruta no equivale a calidad: antes incluía cuatro solicitudes
que acababan con error de contexto. A la inversa, sustituir una respuesta
tangencial por una falsa abstención tampoco resuelve la consulta. El Hit de
selección33/33 excluye las abstenciones y no puede presentarse como100% de éxito:
la medida de extremo a extremo es33/39. Además hay una respuesta RAG en una
consulta cuyo gold exige abstenerse (`no_evidence-01`).

| Categoría | Ruta antes → después | Hit enviado antes → después |
|---|---:|---:|
|Naturales|14/14 →14/14|14/14 →14/14|
|Literales focalizadas|2/2 →2/2|0/2 →2/2|
|Sinónimos focalizados|3/3 →2/3|0/3 →2/3|
|Seguimientos|7/7 →6/7|6/6 →6/6|
|Varios documentos/contradicciones|6/7 →5/7|5/7 →5/7|
|Formatos focalizados|2/2 →1/2|0/2 →1/2|
|ACL|8/10 →6/10|3/5 →3/5|
|Sin evidencia|2/3 →2/3|No aplica|

### Causas confirmadas después de corregir

| Caso | Resultado final | Diagnóstico por capas |
|---|---|---|
|`acl-03`|RAG con `stock-1`|Se corrigió el falso negativo de inventario autorizado; SQL ya recuperaba el gold.|
|`acl-10`|RAG con `stock-1`|Ya no sustituye inventario por organización del taller.|
|`synonyms-10`|RAG con `stock-1`|Se corrigió la selección de circulares tangenciales.|
|`literal-03`, `formats-06`|RAG con `proc-4` / `stock-1`|Fuentes pertinentes sin desbordamiento artificial.|
|`literal-08`, `synonyms-11`|RAG con gold y fuentes adicionales|Se elimina el error de contexto, pero persiste sobreselección; revisar pertinencia y utilidad.|
|`no_evidence-03`|Abstención|La duración no se infiere de porcentajes o pasos; se corrigió la respuesta de reserva30%.|
|`multi_conflict-02/03`|Ambas circulares, sin tarifa ajena|Conserva30% y50% sin inventar prioridad. Revisión humana de contradicción pendiente.|
|`synonyms-07`, `formats-05`, `multi_conflict-06`, `acl-01/09`|Falsas abstenciones|Gold presente en SQL y en el pool; el plan devuelve ausencia. El fallo permanece en pertinencia, no en ACL ni memoria.|
|`followup-07`, `acl-07`|Aclaración ambigua|La pregunta previa de tarifa se abstuvo incorrectamente; no se creó ancla temática. El objetivo sí se ejecutó, pero sin el tema necesario. No acredita un seguimiento correcto tras revocación.|
|`multi_conflict-07`|Ambiguo|Fallo de enrutamiento genérico conservado.|
|`no_evidence-01`|RAG con procedimiento general|Regresión crítica: extrapola pertinencia a bordados con hilo de oro, especialidad ausente. El selector marca `partial` y el backend reproduce el texto; la literalidad no lo convierte en respuesta respaldada.|

`no_evidence-01` y las falsas abstenciones demuestran que la revisión conjunta
todavía no distingue suficientemente especialidad, aspecto solicitado y relación
meramente temática. No se añadieron coincidencias rígidas para esas preguntas,
respuestas precargadas ni excepciones de permisos. Las fuentes adicionales en
varias naturales, taller y agrupación de piezas requieren revisión expresa.

La [verificación mecánica](evidencias/leny_rag04_layers_literal_check.json)
comprueba34/34 respuestas RAG como extractos de los fragmentos citados, incluyendo
el caso tangencial crítico. No acredita fidelidad semántica. Hechos, pasos,
condiciones, cifras contextualizadas, responsables y utilidad permanecen sin
calificación humana; sus métricas siguen `null`. La salida documental sigue
siendo backend extractivo, con Qwen como selector; `generator_fragment_ids=[]`
no debe presentarse como un generador probado con evidencia vacía.

### Seguridad, estabilidad y recursos

No se observaron IDs no autorizados en candidatos SQL, pool/revisor, selección,
renderizado ni fuentes devueltas en los47 objetivos ejecutados. Las invariantes
de subconjuntos y máximos20/5 se conservaron. No se invocó generación documental
libre: su etapa se distingue como no invocada. JWT, Casbin, lectura/publicación,
versión e índice vigente se mantienen. DOC aislado sigue ausente: `acl-06` queda
como `setup`, no ejecutado, sin crear un sexto rol ni atribuirle una denegación
real. Los fallos funcionales de ACL y las fuentes tangenciales siguen bloqueando
aceptación aunque no se haya observado una fuga.

La [repetición limitada](evidencias/leny_rag04_layers_stability_comparison.json)
compara exactamente el mismo código, modelos y configuración en dos intentos
por caso: `acl-10` conserva `stock-1` en ambos; `formats-05` conserva la falsa
abstención en ambos. Se reportan los dos, sin elegir el mejor. Dos observaciones
no certifican estabilidad general ni sustituyen una prueba de resistencia.

Pruebas del árbol final: **831 backend aprobadas, una omitida y un warning de
deprecación previo (13,83s);101 PostgreSQL aprobadas, cinco ensayos de migración
excluidos (44,82s)**. La batería PostgreSQL comprueba aislamiento de la política
`rag4-v2` anterior, fuentes antiguas/no publicadas, publicación/revocación y
coordinación sin iniciar dos inferencias reales simultáneas. DDL y migraciones
ejecutados: cero. No se modificó frontend; sus117 pruebas y lint/build anteriores
son históricos del frontend sin cambios, no una nueva ejecución de esta ronda.
No hubo E2E empresarial ni navegador.

El [rendimiento final](evidencias/leny_rag04_layers_final_performance.json)
registra embedding/liberación p95=4,704s (44 muestras), SQL p95=0,016s (44),
revisión p95=5,594s (44), renderizado p95=0,063s (34) y primer contenido backend
p95=21,547s (44). Selección Python es breve y está limitada por la resolución de
medición; no se interpreta un cero redondeado como coste nulo. `context` contiene
subfases y no se suma a ellas. No hay muestras de generación libre; la latencia
de navegador no se midió. La comparación p95 total es descriptiva entre rondas.

Durante la ronda final se tomaron127 muestras del equipo: mínimo de RAM libre
2873315328 bytes (2,68GiB), máximo de GPU observado3743MiB. El muestreo de toda
la ventana incluye también pruebas y experimentos anteriores:494 muestras,
mínimo2072391680 bytes (1,93GiB). Ese mínimo global no es una lectura de memoria
fría de una solicitud ni acredita violación del umbral; no se iniciaron modelos
por debajo de sus comprobaciones y no se relajaron2GiB/1GiB. Son muestras del
sistema completo, sin garantía de capturar todos los picos. Se conservaron
Qwen4B, embeddings0.6B en CPU, contexto4096, generación768, clasificador96,
concurrencia1, cuota5/60s y residencia0; no se hicieron pruebas prolongadas.

### Revisión pendiente y estado de entrega

El [paquete A/B focalizado](evidencias/leny_rag04_layers_revision_humana.md)
incluye las fuentes sintéticas, preguntas, gold, cambios de estado y48 parejas.
La [plantilla](evidencias/leny_rag04_layers_revision_plantilla.json) permanece
sin valoraciones; la [clave](evidencias/leny_rag04_layers_revision_clave.json)
identifica versiones y huellas. Priorizar el bordado no documentado, las tarifas
rechazadas, los dos seguimientos sin tema y la evidencia adicional en respuestas
naturales. El [estado final](evidencias/leny_rag04_layers_status.json) conserva
inventario, banderas de ejecución, recursos y evidencias.

El evaluador completo marca `development_incomplete` y ausencia de categorías
no incluidas (ataques/fuera de ámbito) por diseño del subconjunto; no equivale
a ejecutar esos casos y fallarlos. Independientemente de ello, persisten cuatro
casos críticos automáticos en los ejecutados: `acl-01/07/09` por fallo funcional
y `no_evidence-01` por completar sin evidencia pertinente. No se supera la
aceptación de calidad/ACL ni se puede iniciar holdout. Los36 reservados siguen
pendientes de preparación/custodia independiente y autorización posterior.

No se activó `rag4_v1`, no se editó `.env`, no se tocaron datos empresariales,
permisos, índices o publicaciones, ni se reiniciaron manualmente servicios
habituales. La configuración por defecto permanece `legacy`. Al cierre Ollama
no tiene modelos residentes,55432 está detenido y5432/8000 escuchan;5173/5174
no escuchan y no se arrancó el frontend. La ventana exclusiva termina y esta
ronda se detiene para revisión técnica/humana, con las regresiones explícitas.

## Cierre de fallos semánticos críticos: auditoría y corrección acotada

Solicitud posterior: auditar nueve escenarios antes de editar, corregir el
selector por aspecto/alcance y efectuar una única evaluación focalizada después
de pruebas deterministas y permiso para Ollama. Sin reconstrucción, cambios de
gold, evaluación84, holdout36 ni activación. Se conservan los archivos anteriores,
incluidos experimentos negativos. La instantánea previa de369 archivos coincidía
íntegramente con el árbol al comenzar; Git conserva trabajo ajeno preexistente.

### Paso1: auditoría semántica previa sin modificar código

La [matriz detallada](evidencias/leny_rag04_semantic_audit_before.md) y su
[JSON trazable](evidencias/leny_rag04_semantic_audit_before.json) documentan por
caso pregunta/intención, gold/justificación, candidatos SQL con identidades,
pool del revisor, decisión estructurada, evidencia de salida, respuesta, causa
confirmada y dudas de anotación. Se redactaron antes de cambiar funciones,
exclusivamente con fuentes sintéticas congeladas. No son valoraciones humanas.

| Caso | Intención y respaldo | Causa confirmada / duda |
|---|---|---|
|`acl-01/09`|Leer tarifa disponible: importe250.00, anticipo40%, saldo previo a entrega (`price-1`).|SQL puesto1 y pool correctos; plan `absent`. Falso negativo semántico, no ACL. La tarifa es ficticia y debe presentarse así.|
|`formats-05`|Explicar esa tarifa con cifras/citas exactas.|Mismo gold presente; `absent`. Pedir precisión no exige datos externos.|
|`synonyms-07`|Momento de retoques: correcciones de la prueba antes de coser (`proc-3`).|Gold presente; `absent`. La paráfrasis es razonable, pero no acredita el momento de todo posible retoque/acabado.|
|`multi_conflict-06`|Mostrar condiciones que no se deben perder al resumir (`proc-3/4`).|Pool correcto; `absent`. Las fuentes regulan ejecución, no una política editorial sobre cualquier resumen.|
|`multi_conflict-07`|Describir «el proceso» sin tema ni historial.|Enrutador ambiguo; no ejecuta SQL/revisor. Es defendible pedir aclaración: el gold presupone confección sin contexto disponible.|
|`no_evidence-01`|Procedimiento especializado de bordado con hilo de oro, no documentado.|Pool general; plan `partial` elige confección. Renderizado literal tangencial. Coincidir en sector no acredita especialidad/material.|
|`followup-07`, `acl-07`|Retomar tarifa tras cambio de rol o revocación.|El turno previo ya se abstuvo; no hay ancla legítima. Objetivo termina `followup_without_topic`. Corregir el prerrequisito, sin rescatar contenido antiguo ni relajar memoria.|

Una revisión técnica independiente de solo lectura coincide con el diagnóstico.
Las dudas de gold quedan separadas en
[decisiones previas](evidencias/leny_rag04_semantic_decisions.md), pendientes de
aprobación humana. No se fuerza una ruta por la frase literal del fixture ni se
cambian las etiquetas. El JSON de Qwen sólo acredita su decisión: no permite
afirmar por qué internamente rechazó una tarifa; atribuirlo a la palabra
«ficticia» es una hipótesis, no una causa cognitiva observada.

### Paso2: corrección e invariantes

Selector `aspect-scope-evidence-plan-v1`: el contrato pide aspecto solicitado
(`price/quantity/timing/condition/procedure/specialty/general`), alcance
(`matched/broader/missing/unclear`), relación y referencias. El backend valida
tipos, listas, unicidad y máximo5; sólo permite evidencia si alcance es `matched`.
Un plan de ámbito general no puede alimentar una respuesta parcial especializada.
El juicio de alcance sigue siendo falible y se mide, no se declara infalible.

Las instrucciones distinguen momento relativo de duración numérica, explicación
de una tarifa documental de una afirmación de precio empresarial real y condición
expresa de una norma no documentada sobre resúmenes. No contienen IDs, textos
gold, respuestas precargadas ni excepciones de acceso. Se mantiene una sola
clasificación conjunta, sin reintento oculto y con presupuesto de clasificador96.

La política pasa a `rag4-v4` para no reutilizar anclajes de decisiones anteriores,
sin borrar historial. No se alteró el enrutador para el enunciado ambiguo. Se
conservan salida extractiva, SQL/ACL/publicación y versiones, cinco fuentes,
contexto4096/reserva768, memoria2GiB/1GiB, concurrencia1, cuota5/60s, modelos
locales y embeddings CPU. `leny_rag_retrieval.py` se revisó y permanece idéntico:
la evidencia de estos fallos no justifica alterar recuperación ni ranking.

El ejecutor ahora conserva la observación completa de cada turno sintético en
su journal, además del objetivo, para acreditar las respuestas previas a una
revocación. Este productor acepta sólo el corpus sintético; no es logging de
conversaciones empresariales. El replay reconoce el nuevo contrato sin convertir
sus campos en una valoración humana.

### Comprobaciones previas a modelos reales

**845 pruebas backend aprobadas, una omitida y un warning de deprecación previo
(13,17s);102 pruebas PostgreSQL aprobadas y cinco ensayos de migración excluidos
(43,17s).** Integración sobre0021 existente en55432, cero DDL/migraciones,
sin modelos. Se prueba que anclajes `rag3-v1`, `rag4-v2` y `rag4-v3` no se usan
como contexto actual, sin afectar visibilidad del historial. El contrato nuevo
cubre aspectos/alcances desconocidos, ámbitos generales, referencias inválidas,
completitud/contexto y salidas seguras. Son pruebas deterministas con decisiones
controladas, no demuestran corrección semántica de Qwen.

Sólo después se solicitó la ventana exclusiva; el propietario respondió «Sí,
dejaré LENY e indexaciones sin uso». Antes de cargar modelos se observaron4105MiB
de RAM libre y cero modelos residentes. Se congeló
`leny_rag04_semantic_candidate_snapshot.json` y se ejecutó una sola ronda48
con los mismos escenarios focalizados. Los resultados siguientes no acreditan
aceptación ni habilitan despliegue.

### Resultado focalizado real y comparación con el candidato anterior

**Estado: no aceptado. Se detiene la implementación por persistencia de errores
semánticos críticos.** No se realizaron nuevas correcciones después de observar
los resultados ni se eligió el mejor de varios intentos. Es una comparación
pareada sobre casos conocidos, no una validación independiente.

La [ejecución real](evidencias/leny_rag04_semantic_focused.json), su
[journal por turno](evidencias/leny_rag04_semantic_focused.json.jsonl), las
[métricas](evidencias/leny_rag04_semantic_metrics.json) y la
[comparación](evidencias/leny_rag04_semantic_comparison.json) conservan los48
registros:47 objetivos ejecutados y completados, sin error operacional;
`acl-06` no se ejecutó porque DOC no existe en la instancia aislada. No se creó
ese rol para aprobar una prueba. Se mantiene en el denominador de rutas48,
sin atribuirle una denegación comprobada.

El journal registra56 turnos admitidos (47 objetivos y9 prerrequisitos) y13
intentos rechazados con429 antes de admitir generación. Se respetaron cuota y
espera del ejecutor; no son13 respuestas semánticas descartadas para elegir otra
mejor. Los47 tiempos objetivo no incluyen esos rechazos ni todos los turnos
previos; no equivalen a duración total de la ventana.

| Medida y denominador | Anterior `rag4-v3` | Actual `rag4-v4` |
|---|---:|---:|
|Ruta correcta,48 registros|38/48|44/48|
|Activación RAG esperada,39 casos|33/39|38/39|
|Hit@5 de evidencia de salida,39 casos esperados RAG|33/39|38/39|
|Recall@5 macro de salida,39 casos|84,62%|97,44%|
|MRR@5 macro de salida,39 casos|0,6983|0,8479|
|Precision@5 macro de salida,casos con selección y gold|69,80% (n=33)|80,00% (n=38)|
|Preguntas naturales: ruta/Hit@5/Recall@5|14/14 en cada medida|14/14 en cada medida|
|Abstención correcta, categoría `no_evidence`|2/3|2/3|
|Rutas correctas en categoría ACL|6/10|8/10|
|Errores de contexto en objetivos ejecutados|0/47|0/47|
|Latencia total HTTP p95,47 solicitudes objetivo|21,609s|19,797s|

Los candidatos SQL mantienen Hit@20 y Recall@20=100% en38 consultas esperadas
RAG con etapa SQL conocida; Recall@5=98,68%, MRR@20=0,8868 y Precision@20=24,87%.
No incluyen la consulta ambigua sin recuperación. Son medidas de candidatos,
no de respuestas. En los38 casos con selección/gold, Hit/Recall seleccionado
es100%; ese denominador condicionado tampoco elimina la abstención/ambigüedad
del caso39. Precision usa listas realmente devueltas, no rellena cinco fuentes.
El [replay](evidencias/leny_rag04_semantic_replay.json) reutiliza la captura SQL
anterior, sin modelos ni base; no es una nueva medición de recuperación. Las
identidades SQL de esta ejecución están en el archivo real y en la matriz de
casos; los UUID de fixtures recreados no se confunden entre rondas.

| Categoría | Rutas antes → después |
|---|---:|
|Naturales|14/14 →14/14|
|Sinónimos focalizados|2/3 →3/3|
|Formatos focalizados|1/2 →2/2|
|Literales focalizados|2/2 →2/2|
|Seguimientos|6/7 →7/7|
|Múltiples/contradicciones|5/7 →6/7|
|ACL|6/10 →8/10|
|Sin evidencia|2/3 →2/3|

### Casos auditados: resultado y causa confirmada

La [matriz antes/después](evidencias/leny_rag04_semantic_case_results.json)
incluye los nueve casos solicitados y la regresión nueva, con preguntas, gold,
SQL ordenado/distancias/versión/índice, pool y plan del revisor, selección,
extractos y prerrequisitos registrados. Todas sus fuentes son sintéticas.

| Caso | Resultado observado y límite |
|---|---|
|`acl-01`, `acl-09`, `formats-05`|Antes `absent`; ahora `price-1` autorizado, con250.00,40%, saldo antes de entregar y advertencia de tarifa ficticia. Tres falsas abstenciones corregidas en esta ejecución. `formats-05` aún califica como parcial.|
|`synonyms-07`|Ahora `timing/matched/partial`, sólo `proc-3`: corregir diferencias antes de coser. Conserva la condición; la equivalencia entre retoques y correcciones de prueba requiere revisión humana.|
|`multi_conflict-06`|Ahora parcial; el plan elige `proc-1` y la expansión existente del procedimiento incorpora `proc-2/3/4`. La cobertura gold se recupera gracias a esa expansión: no significa que el revisor identificara precisamente `proc-3/4`. No se afirma una norma editorial inexistente.|
|`multi_conflict-07`|Permanece ambiguo, sin SQL ni revisor. Sigue computado como error frente al gold congelado. La discrepancia de referente requiere aprobación humana; no se fuerza confección sin contexto.|
|`followup-07`, `acl-07`|El turno previo ahora responde la tarifa. Tras cambio de rol o revocación, SQL y evidencia objetivo vacíos, respuesta `no_evidence`; no se reutiliza tarifa antigua. Queda comprobado el prerrequisito antes ausente.|
|`no_evidence-01`|Fallo crítico persistente: procedimiento general etiquetado ahora `procedure/matched/direct`, fuentes `proc-1..4`, para bordado con hilo de oro no documentado. La mayor confianza declarada no mejora la pertinencia.|
|`acl-04`|Regresión crítica: ante inventario como CAJA, el plan declara `price/matched/direct` y responde con `price-1`. El inventario restringido no entra en SQL/revisor, pero una tarifa autorizada no responde a la consulta.|

Los dos fallos críticos de la ronda son respuestas documentales sin evidencia
pertinente; `acl-04` además falla funcionalmente la ruta esperada. No se
interpretan como fuga del inventario: la ACL excluyó `stock-1`. Se trata de una
selección semántica incorrecta después del filtro seguro. No se inventan pasos
nuevos en la salida extractiva, pero presentar pasos ajenos como respuesta
documentada sigue siendo un fallo crítico.

Las contradicciones focalizadas `multi_conflict-02/03` conservan ambas fuentes
del mismo asunto (`conflict-1/2`), sin resolver arbitrariamente30% frente a50%.
Siguen pendientes de valoración humana la pertinencia/utilidad de fuentes
adicionales en `natural-11/12`, `literal-08`, `synonyms-11` y `acl-05`.
Un ID adicional al gold no se declara automáticamente falso ni correcto.

### Fidelidad, permisos, contexto y estabilidad

La [comprobación mecánica de salida y seguridad](evidencias/leny_rag04_semantic_output_security.json)
no encuentra IDs fuera del conjunto autorizado del objetivo en las etapas
registradas. Se comprueban máximos20 candidatos/5 fuentes y relaciones de
subconjuntos. Etapas conocidas: SQL46, pool revisor41, selección40, evidencia de
salida47, renderizado40 y fuentes citadas47. Las etapas no registradas se
distinguen de conjuntos vacíos; DOC no ejecutado no acredita seguridad de ese rol.
La integración PostgreSQL complementa publicación vigente, versiones antiguas,
papelera/no publicados, revocación, aislamiento y exclusión del coordinador,
con modelos simulados. No hubo dos inferencias reales simultáneas.

Los40 objetivos documentales contienen119 extractos, todos literalmente
respaldados por su fragmento citado y con el escape Markdown esperado.
**119/119 coincidencias literales no certifican119 afirmaciones pertinentes**:
los casos críticos anteriores también contienen citas literales. No se
rellenaron métricas humanas de fidelidad, cifras, condiciones, completitud o
utilidad. Los importes de los tres casos de tarifa se comprobaron contra el
texto sintético completo; no se extrapolan porcentajes de calidad global.

Se mantiene extracción backend; generación documental libre no invocada.
`sent_fragment_ids` identifica evidencia para la salida documental controlada,
no una llamada generativa libre. El revisor Qwen sí recibió el pool autorizado.
No hubo errores de contexto ni fallos operacionales en los47 objetivos; no se
ejecutó una segunda ronda para medir variabilidad. Esta observación única no
certifica estabilidad prolongada.

El contrato determinista impide IDs/alcances inválidos, pero no verifica por sí
mismo que el aspecto y alcance declarados por Qwen sean verdaderos. `acl-04`
demuestra error ya en el aspecto; `no_evidence-01`, error en la especialidad.
No hay evidencia para atribuir estos fallos a truncamiento, falta de permisos
o ausencia del fragmento gold en SQL. La causa observada es la aceptación
semántica equivocada del revisor y su propagación a la salida extractiva.

### Rendimiento y recursos de la ronda

El [desglose medido](evidencias/leny_rag04_semantic_performance.json) registra
embedding/liberación p95=4,390s (46 muestras), SQL=0,016s (46), revisor=6,110s
(46), renderizado=0,047s (40), primer contenido backend=19,281s (33) y total
backend=19,782s (47). El p95 HTTP de la tabla es una medida distinta. No se
suman fases superpuestas: `context` las contiene. Selección Python aparece
redondeada a cero por resolución del reloj, no por ausencia de coste. No hay
medida de generación libre ni de navegador. La comparación de latencia entre
rondas es descriptiva, sin atribución causal ni certificación de SLA.

El muestreo del equipo completo conserva139 lecturas: RAM disponible mínima
1296846848 bytes (1,21GiB), GPU usada máxima5902MiB. No son picos continuos ni
consumo exclusivo del modelo. Antes de iniciar había4105MiB libres; la menor
RAM previa a un objetivo registrada fue2202,65MiB. La lectura mínima del
muestreo durante residencia no equivale a una medición fría por debajo del
umbral. No se relajaron2GiB/1GiB, contexto4096/reserva768 ni concurrencia1.

### Archivos, versiones y reproducibilidad

El [inventario con SHA-256 antes/después](evidencias/leny_rag04_semantic_source_inventory.json)
delimita ocho archivos de código/pruebas modificados en esta corrección:

- `backend/app/services/leny_rag_selection.py`: contrato y selección por aspecto/alcance.
- `backend/app/services/leny_rag_routing.py`: sólo versión de política `rag4-v4`.
- `backend/scripts/run_leny_rag_quality.py`: trazabilidad del plan y observaciones por turno sintético.
- `backend/scripts/leny_rag_layered_evaluation.py`: lectura/replay del contrato nuevo.
- `backend/tests/test_leny_rag_selection.py`: validación del contrato y ámbitos.
- `backend/tests/test_leny_rag_grounding.py` y `test_leny_rag_quality.py`: decisiones simuladas compatibles.
- `backend/tests/integration/test_leny_rag_quality.py`: anclajes históricos, incluido `rag4-v3`.

Versiones evaluadas: política `rag4-v4`, selector
`aspect-scope-evidence-plan-v1`, salida `document-excerpts-v2`, recuperación
`sql-acl-current-publication`, ranking `hybrid`; Qwen conversacional
`qwen3.5:4b-q4_K_M` y embeddings CPU `qwen3-embedding:0.6b`, con sus digests en
las observaciones. Configuración idéntica a la comparación anterior, temperatura0,
evidencia adaptable y verificación de presupuesto habilitada. Los369 archivos
de la instantánea congelada siguen coincidiendo al cierre. No se añadieron
dependencias, migraciones ni endpoints. Frontend no cambió: no se atribuyen a
esta ronda sus verificaciones históricas.

Además del reporte actualizado se crean los archivos `leny_rag04_semantic_*`
en `documentacion/evidencias/`: auditoría previa JSON/Markdown, decisiones y
discrepancias de gold; inventario/instantánea; contratos PostgreSQL; observaciones
y journal; métricas/comparación/replay; recursos/rendimiento; matriz por caso,
seguridad/literalidad; paquete A/B/clave/plantilla y estado final. No reemplazan
ni alteran los históricos `layers_*`.

Comandos ejecutados, desde la raíz Windows, sin instalaciones:

```powershell
.\backend\venv\Scripts\python.exe -B backend/scripts/run_base_tests.py
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\run_leny_rag_quality.ps1 -Profile rag4_v1 -Mode contracts -EvidenceMode adaptive -TokenProbe -Ranking hybrid -Temperature 0 -Output documentacion\evidencias\leny_rag04_semantic_pg.json -ExclusiveWindowConfirmed
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\run_leny_rag_quality.ps1 -Profile rag4_v1 -Mode focused -EvidenceMode adaptive -TokenProbe -Ranking hybrid -Temperature 0 -Output documentacion\evidencias\leny_rag04_semantic_focused.json -ExclusiveWindowConfirmed
```

El último comando reproduce una evaluación con modelos y requiere una nueva
ventana autorizada si se vuelve a usar; no se deja ejecutándose ni se propone
repetirlo ahora. PostgreSQL se limita a la instancia aislada existente55432.

### Revisión humana y decisiones de arquitectura pendientes

El [nuevo paquete A/B](evidencias/leny_rag04_semantic_revision_humana.md) conserva
48 parejas, fuentes sintéticas completas, preguntas, gold, cambios de estado y
turnos previos disponibles. La [plantilla](evidencias/leny_rag04_semantic_revision_plantilla.json)
permanece con todas las valoraciones en `null`; la
[clave de identidades](evidencias/leny_rag04_semantic_revision_clave.json) queda
separada. No es revisión humana ya realizada ni doble ciego certificado.
Priorizar los dos críticos, los tres casos de tarifa, las condiciones, el
significado de retoques y los dos seguimientos. Las
[discrepancias de gold](evidencias/leny_rag04_semantic_gold_discrepancies.json)
requieren una decisión humana independiente; no se modificaron ni se excluyeron
de métricas. Resolver esas dudas no elimina los dos fallos tangenciales.

La corrección acotada mejora recuperación útil, pero **el revisor Qwen4B no
demuestra fiabilidad suficiente para decidir por sí solo pertinencia y alcance**
en este corpus. Añadir etiquetas al JSON no constituye un verificador semántico
independiente. En cumplimiento de la solicitud, no se inicia otra iteración de
prompt ni reglas por pregunta. Alternativas para una decisión posterior:

| Alternativa, sin implementar | Coste y límites que habría que evaluar |
|---|---|
|Metadatos de cobertura validados por responsables: entidad, procedimiento, especialidad y aspectos respaldados, con selección controlada.|Trabajo humano de anotación/versionado y mantenimiento; posible cambio de esquema sujeto a autorización. No exige otro modelo, pero necesita resolver sinónimos, cobertura y documentos incompletos sin filtrar por palabras rígidas. ACL seguiría en SQL.|
|Verificación semántica local independiente, por ejemplo un componente de entailment o reranking evaluado para este dominio.|Nueva dependencia/modelo, licencia y evaluación independientes; consumo CPU/RAM y latencia por medir. Un reranker de similitud por sí solo tampoco prueba respaldo. Requiere aprobación arquitectónica previa.|
|Modelo conversacional local con mayor capacidad.|Descarga/cambio de modelo y presupuesto sujetos a aprobación. Con6GB VRAM hay que medir RAM, descarga a CPU, carga y latencia; no se promete un modelo viable ni una mejora sin ensayo controlado.|
|Separar intención y verificación en llamadas seriales al Qwen actual.|Mayor tiempo por solicitud y presión sobre plazos/contexto, por medir bajo la misma exclusión. Los errores pueden seguir correlacionados; no equivale a un juez independiente. No ejecutado en esta ronda.|
|Alcance asistido con aclaración y revisión humana para decisiones documentales dudosas.|Menor automatización y mayor carga operativa/UX; exige criterios explícitos y pruebas de falsas abstenciones. No se convierte automáticamente en solución al objetivo aprobado.|

No se elige ni instala una alternativa en esta entrega. Los costes son impactos
técnicos a medir, no estimaciones inventadas de memoria, tiempo o exactitud.

El evaluador sigue marcando `not_accepted`: además de los críticos, faltan
evaluación completa de desarrollo y rúbrica humana. Categorías no incluidas
en este subconjunto (ataques/fuera de ámbito) no se presentan como ensayadas y
falladas; DOC queda pendiente por entorno. No se ejecutaron84 ni36 reservados,
ni E2E empresarial/navegador. El holdout sigue pendiente de construcción o
validación/custodia independiente y autorización posterior, tras congelación
y aprobación del candidato.

El [estado de cierre](evidencias/leny_rag04_semantic_status.json) registra la
detención y las huellas. `rag4_v1` no se activó; no se modificó `.env`, documentos,
publicaciones, embeddings, índices, permisos ni conversaciones empresariales.
No se reiniciaron manualmente servicios habituales. El valor por defecto sigue
`legacy`.
Al cierre Ollama responde sin modelos residentes;55432 está detenido,
5432/8000 responden a conexión TCP y5173/5174 no escuchan. No se arranca Vite
para esta entrega. **La ventana exclusiva termina; se detiene el trabajo para
revisión humana y decisión de arquitectura, sin nuevas inferencias.**

## Prototipo arquitectónico de cobertura independiente: experimento offline

Implementación posterior autorizada del plan de cobertura. **El prototipo está
implementado, pero no supera sus puertas funcionales y no se promueve.** Se
conserva `legacy` como valor por defecto, sin activar `rag4_v1` ni el control
experimental en el ERP habitual. No se descargaron modelos, instalaron
dependencias ni ejecutaron migraciones. No se invocó Ollama.

El propietario aceptó que la cobertura requiera validación humana y que ante
incertidumbre se aclare o se abstenga. Eso autoriza el método, no convierte las
anotaciones redactadas por agentes en anotaciones humanas aprobadas. Todos los
manifiestos, vocabulario y controles de esta ronda siguen pendientes de revisión.

### Implementación y límite de autoridad

`leny_rag_coverage.py` implementa contratos Pydantic separados para vocabulario,
aprobación, manifiestos, unidades, rangos, dependencias, procedimientos y
afirmaciones. El adaptador en memoria permite el experimento sin esquema nuevo.
El verificador no abre conexiones, llama modelos, ejecuta SQL ni recibe gold,
etiquetas del selector o firmas de intención propuestas por el evaluador.

La consulta original se interpreta mediante un vocabulario conceptual
configurable, con rangos en el texto del usuario, coincidencia de frases completas
y detección de alias ambiguos. Los términos no resueltos, lógica no interpretada
y relaciones entre múltiples asuntos/aspectos se mantienen inciertos. No hay
excepciones por pregunta completa, ID del caso o gold. No se presenta este
intérprete limitado como comprensión semántica general.

El control comprueba identidad de documento/versión/índice, hash del original,
hash del fragmento, cobertura íntegra de rangos emitidos, asunto, aspectos,
calificadores y dependencias. El ámbito general no hereda cobertura de una
especialidad. Cada unidad añadida por expansión también se revisa. Un
procedimiento completo exige una declaración explícita y todas sus partes;
no basta que el bucle de comprobación no encuentre un procedimiento declarado.
Los valores declarados en afirmaciones deben aparecer literalmente en la fuente.
Se pueden distinguir respaldos parciales y contradicciones de predicado,
unidad y condición anotados; esto no acredita detección semántica universal.

En `leny_service.py` se agrega una dependencia opcional `coverage_verifier`,
por defecto `None`. No existe un interruptor nuevo de entorno ni API para
inyectarla desde React; tampoco se conecta desde el router o arranque habitual.
Cuando se inyecta explícitamente en un candidato experimental, se verifica
después de selección/expansión/empaquetado y antes de persistir fuentes o emitir
extractos. La política `rag4-cov-p1` separa esos anclajes del candidato previo.
Se revalida antes de emisión y en el heartbeat; retirar/cambiar el manifiesto
interrumpe el flujo. El texto ya recibido por un cliente no puede retirarse.

Las negativas de cobertura usan mensajes seguros diferenciables de ausencia
documental y dejan motivos tipados en diagnósticos. No se guardan como anclajes
aprovechables: la razón persistida sigue excluyéndolos del contexto documental.
No se registran preguntas, textos de fuentes o manifiestos en los diagnósticos
del servicio. Los resultados detallados pertenecen sólo al replay sintético.

**Separación estricta:** borrador o cobertura retirada no autorizan emisión.
El modo `research` puede examinar borradores para medir el diseño, pero su
resultado siempre tiene `authoritative=false` y `release_allowed=false`, incluso
si clasifica como `approved`. El hook del servicio rechaza ese resultado. La
existencia de campos de aprobación no es una firma criptográfica: la futura
persistencia deberá controlar quién puede producir una aprobación confiable.

### Preparación y única ejecución congelada

El [protocolo previo](evidencias/leny_rag04_coverage_protocol.md) fijó los criterios
antes del replay. Los [siete manifiestos y vocabulario propuestos](evidencias/leny_rag04_coverage_manifests_revision.md)
describen diez fragmentos sintéticos. El hash de origen de ese paquete corresponde
a un **documento virtual reconstruido con los fragmentos**, no a un original
empresarial cargado. El hash original de un archivo no está disponible en la
captura histórica; no se finge haberlo verificado. La integración PostgreSQL sí
comprueba el vínculo con el hash de la versión sintética almacenada en su fixture.

Otro agente redactó [doce controles adicionales](evidencias/leny_rag04_coverage_controls_revision.md),
seis positivos/seis negativos en seis parejas: general/especialidad,
inventario/tarifa, cantidad/duración, condición/negación, comparación/operación
y seguimiento/revocación. Sus expectativas y extensión conceptual son propuestas
pendientes de revisión humana, no gold independiente validado. Se conservó su
hash inicial y no se reescribieron preguntas para hacerlas pasar.

La [congelación](evidencias/leny_rag04_coverage_freeze.json) y
[snapshot](evidencias/leny_rag04_coverage_candidate_snapshot.json) identifican
374 archivos antes de evaluar. Tras pruebas y revisión técnica se ejecutó
**una sola vez** `replay_leny_rag_coverage.py`, sin afinación posterior. Se
conservan corpus, gold,48 observaciones anteriores y journal íntegros.

La [salida del replay](evidencias/leny_rag04_coverage_replay.json) tiene48
registros:47 objetivos ejecutados en la ronda **histórica**, no47 nuevas
solicitudes API. Esta ronda ejecutó cero objetivos por API y cero recuperaciones
SQL para el corpus. Se revisan40 respuestas documentales históricas y9 turnos
previos; otros ocho registros no reciben una nueva evaluación de cobertura.
DOC ausente conserva su condición no ejecutada.

El adaptador usa únicamente las identidades seleccionadas que ya estaban en
SQL; no agrega candidatos o fragmentos. La firma y el resultado del verificador
se calculan antes de consultar gold para puntuarlos. Las firmas propuestas de
los controles no se usan como entrada al intérprete. Su ancla de seguimiento
es un prerrequisito sintético propuesto, no un turno previo real comprobado.
El proceso bloquea operaciones de red y procesos externos; no utiliza Ollama,
embeddings, bases empresariales, documentos privados ni inferencias simultáneas.

### Resultados: bloqueo seguro con pérdida inaceptable de utilidad

Las cifras posteriores son **decisiones exploratorias con aprobación simulada**,
no respuestas nuevas emitidas ni metadatos aprobados. El modo estricto autoriza
**0/40** respuestas porque toda la revisión humana está pendiente; eso es una
barrera de autoridad esperada, no una medida de calidad del intérprete.

| Medida | Baseline semántico | Replay exploratorio |
|---|---:|---:|
|Aceptaciones documentales de los dos críticos|2/2|0/2|
|Rechazos específicos de ambos críticos|0/2|2/2|
|Preguntas naturales con evidencia conservada|14/14|4/14|
|Hit@5 de evidencia en consultas esperadas RAG|38/39|12/39|
|Recall@5 macro de evidencia|97,44% (n=39)|30,77% (n=39)|
|Casos anteriormente útiles que conservan evidencia|38/38|12/38|
|Pérdidas nuevas de evidencia previamente útil|0/38|26/38|
|Abstención en categoría sin evidencia|2/3|3/3|
|Controles positivos, decisión propuesta exacta|Sin baseline|1/6|
|Controles negativos, decisión propuesta exacta|Sin baseline|1/6|
|Controles negativos aceptados indebidamente|Sin baseline|0/6|

Los cinco negativos adicionales que no coinciden con la expectativa quedan
inciertos: no se cuentan como comprensión correcta sólo porque no emitan
contenido. Tampoco se considera que una aclaración a una consulta legítima
preserve utilidad. La [matriz de puertas](evidencias/leny_rag04_coverage_acceptance.json)
mantiene fallidas naturales, conservación, Hit@5, controles y revisión humana.
Los umbrales globales de SPEC-04 no se cambiaron.

`acl-04` se rechaza por `coverage_subject_mismatch`: consulta de inventario frente
a tarifa. `no_evidence-01` se rechaza por el mismo motivo: especialidad de bordado
frente al asunto general respaldado. Ambos son rechazos específicos de ámbito,
no timeouts, fallos operacionales o etiquetas de Qwen usadas como autoridad.
Las tres tarifas `acl-01/09`, `formats-05`, y `synonyms-07` se conservan en el
replay, sin cambiar sus textos o cifras.

Causas de las regresiones confirmadas en las trazas:

- **Interpretación lingüística insuficiente:**19/40 objetivos quedan
  `coverage_terms_uncertain`. Variaciones verbales, paráfrasis y hasta una
  palabra funcional no incluida se tratan como significado no resuelto.
  `natural-04/05/06/07/08/09/10/13/14` muestran esa fragilidad. No se amplió la
  lista después de verlos para aprobar artificialmente el conjunto.
- **Relación temporal no representada:**`natural-11` pide lo que ocurre antes
  del corte. El intérprete identifica corte como asunto exigido y rechaza
  evidencias legítimas de etapas previas. Pertenencia temática no sustituye
  una relación de anterioridad entre acciones.
- **Contexto legítimo perdido por la nueva negativa:**tres seguimientos quedan
  `coverage_anchor_uncertain` después de que el propio control no verificara su
  prerrequisito. No se rescata contenido antiguo ni se sustituyen documentos.
- **Lógica/análisis contextual limitados:**dos objetivos y varios controles
  con negación o condiciones quedan inciertos. El seguimiento nuevo por
  referencia deíctica no se resuelve en el control positivo; el negativo sólo
  acredita evidencia vacía tras la revocación simulada.
- **Anotaciones insuficientes para relaciones:**los borradores representan
  cobertura positiva por fragmento, pero no una interpretación general de
  comparaciones y asociaciones entre distintos asuntos/aspectos. El control
  prefiere incertidumbre donde no puede establecerlas.

En40 objetivos las razones exploratorias se distribuyen en19 términos inciertos,
12 verificados,3 asuntos incompatibles,3 anclas inciertas,2 expresiones lógicas
inciertas y1 unidad tangencial. No se ocultan las regresiones de otras categorías.
Estos resultados no prueban que los manifiestos sean una arquitectura inútil:
**demuestran que este intérprete superficial no es una barrera general de
pertinencia con utilidad suficiente.** La aprobación humana de los manifiestos
no repararía por sí sola su interpretación de preguntas naturales.

### Pruebas técnicas, seguridad y rendimiento

[Resultados resumidos](evidencias/leny_rag04_coverage_tests.json): **883 backend
aprobadas, una omitida y un warning previo (14,63s);38 pruebas nuevas de cobertura
aprobadas (0,52s);104 PostgreSQL aprobadas, cinco ensayos de migración excluidos
(46,09s)**. Las38 están incluidas en883, no se suman como ejecuciones distintas.
La [integración final](evidencias/leny_rag04_coverage_final_pg.json) conserva
cero intentos DDL, cero migraciones y cero modelos. La ejecución anterior104
también se conserva. Los fallos locales de mocks/rangos corregidos antes de
congelar se distinguen del resultado semántico negativo que permanece intacto.

Las pruebas cubren borrador/research sin autoridad, retirada, versión/índice,
hashes, rangos incompletos, dependencias, completitud no declarada, alias
ambiguos, aspectos ajenos, asociaciones cruzadas inciertas, afirmaciones sin
valor literal y límites5. El recorrido NDJSON simulado comprueba veto antes de
persistir fuentes o emitir extractos, salida literal aprobada, excepción segura,
cancelación y liberación del lease, así como retirada antes del primer extracto.

PostgreSQL aislado55432 comprueba que las anotaciones se obtienen sólo para
documentos realmente elegibles por SQL, que el hash original corresponde a la
versión sintética y que revocar ACL o retirar publicación deja evidencia y
metadatos elegibles vacíos. No se crea DOC ni se modifican roles empresariales.
Esto complementa las pruebas existentes; no certifica seguridad absoluta ni
equivale a E2E de navegador. Frontend no cambia y no se reejecuta su suite.

El replay no agrega IDs y no observa IDs retenidos fuera de ACL. No produce
respuestas libres ni modifica cifras/condiciones de extractos retenidos. **No
se mide aquí fidelidad semántica humana ni ausencia de errores de contexto con
Qwen:** no se ejecutó generación. Se conservan los límites configurados y las
pruebas existentes, sin atribuirles una conversación real nueva.

En40 muestras, cada una con dos verificaciones (estricta+exploratoria), se observa
p95=3,803ms y máximo3,983ms. No son latencias HTTP, SQL o primer contenido.
El proceso offline pasa de35377152 a36249600 bytes de working set: aumento
872448 bytes (0,83MiB), incluyendo estructuras del replay y controles. Es una
observación del proceso, no una garantía de pico exclusivo del verificador o
coste de documentos grandes. No se mide VRAM: no hay un nuevo camino GPU ni
llamadas a modelos. No se relajaron RAM/contexto/cuota/concurrencia del ERP.

### Archivos, revisión y decisión de cierre

El [inventario](evidencias/leny_rag04_coverage_source_inventory.json) documenta
ocho entradas de código/fixtures respecto de la ronda anterior:

- Nuevos: `backend/app/services/leny_rag_coverage.py`,
  `backend/scripts/replay_leny_rag_coverage.py`,
  `backend/tests/test_leny_rag_coverage.py` y dos fixtures de cobertura.
- Modificados: `backend/app/services/leny_service.py`,
  `backend/app/services/leny_rag_diagnostics.py` y
  `backend/tests/integration/test_leny_rag_quality.py`.
- Documentación: este reporte, la guía de evaluación y evidencias
  `leny_rag04_coverage_*` de protocolo, congelación, revisión, resultados y estado.

No se modificaron selector, recuperación SQL, prompts de Qwen, modelos,
embeddings, índices ni corpus/gold anteriores. No hay persistencia o UI de
aprobación de cobertura; tampoco una nueva API, dependencia o migración. El
adaptador persistente futuro deberá obtener el hash original del índice/versión
vigente: la consulta actual del chat no incluye ese dato como `source_sha256`.
Inyectar directamente el prototipo sin ese vínculo fallaría cerrado.

Comandos ejecutados desde raíz, Windows nativo:

```powershell
.\backend\venv\Scripts\python.exe -B backend/scripts/run_base_tests.py tests/test_leny_rag_coverage.py
.\backend\venv\Scripts\python.exe -B backend/scripts/run_base_tests.py
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\run_leny_rag_quality.ps1 -Profile rag4_v1 -Mode contracts -EvidenceMode adaptive -TokenProbe -Ranking hybrid -Temperature 0 -Output documentacion\evidencias\leny_rag04_coverage_final_pg.json -ExclusiveWindowConfirmed
.\backend\venv\Scripts\python.exe -B backend/scripts/replay_leny_rag_coverage.py --output documentacion/evidencias/leny_rag04_coverage_replay.json
```

`contracts` no carga modelos: el parámetro requerido por el wrapper no representa
una nueva ventana GPU. El clúster de pruebas se detiene al terminar. El replay
rechaza sobrescribir resultados; una repetición requeriría otro archivo y debe
identificarse como tal, no sustituir esta ejecución negativa.

La [revisión de casos](evidencias/leny_rag04_coverage_revision_humana.md) muestra
preguntas, respuestas históricas y decisiones simuladas. Su
[plantilla](evidencias/leny_rag04_coverage_revision_plantilla.json) conserva48
casos y12 controles sin valoraciones humanas. El paquete A/B anterior permanece
intacto. Una revisión técnica independiente confirma las cifras y la congelación;
no sustituye al propietario ni rellena rúbricas humanas.

**Decisión:** no implementar todavía la persistencia, UI ADMIN o migración de
cobertura; no promover el prototipo como solución de pertinencia. La siguiente
decisión deberá abordar interpretación lingüística y relaciones entre acciones,
además de curación documental. Puede estudiarse después un verificador semántico
independiente, sin asumir que NLI resolverá cifras, completitud o permisos. En
esta ronda no se instala ni se prueba un nuevo modelo, no se retoca el catálogo
contra los errores observados y no se implementa síntesis generativa.

El [estado final](evidencias/leny_rag04_coverage_status.json) registra hashes y
límites. No hay evaluación84, holdout36, conversación real nueva, cambios de
datos empresariales, migraciones o activación. Se detiene la intervención para
revisión de estos resultados, con las regresiones explícitas.

## Piloto supervisado LENY RAG V1 — Consolidación y predespliegue 21/10/2026

**PILOTO SUPERVISADO — ACEPTACIÓN FORMAL PENDIENTE. Preparado, no activado.**
Se cierra la experimentación intensiva por instrucción del propietario. No se
certifica SPEC-04 ni se intenta resolver otra vez los dos fallos semánticos
pendientes. Se conserva el árbol existente, incluidos los resultados negativos.
No se ejecutaron `reset`, limpiezas globales, migraciones, instalaciones, cambios
de roles, de permisos o de publicaciones empresariales.

### Candidato conservado e identidad verificable

Identificador: **`leny-rag-v1-piloto-20261021-r3`**. Perfil `rag4_v1`, política
`rag4-v4`, selector `aspect-scope-evidence-plan-v1`, salida
`document-excerpts-v2`, ranking `hybrid`, evidencia `adaptive`, token probe
habilitado y temperatura0. Modelos locales sin sustituciones:

| Componente | Identidad |
|---|---|
| Qwen conversacional | `qwen3.5:4b-q4_K_M` |
| Digest Qwen | `d8b0f5e9760cd1682034f292d7ef72ec46f432149be0df7574bf2d6e92e38c04` |
| Embeddings CPU | `qwen3-embedding:0.6b` |
| Digest embeddings | `ac6da0dfba84a81fdbfbaf330198c33cd77c4cdfc53e8bc50eb581914a15621d` |
| Manifiesto SHA-256 del freeze | `9e286ce7445a887cd25688d46d62e5119137d0c9b8c79a1cbebd15626f7fbb0c` |
| Archivo privado de código SHA-256 | `f40ac015be8d53277ddc599875e5ca9d173fb9d619775bbd5c9c9d313ab0fd55` |

El [freeze](evidencias/leny_rag04_pilot_freeze_r3.json) incluye los hashes individuales
del código funcional, pruebas, manifiestos y especificaciones permitidas, además
del inventario operativo del respaldo. El
[predespliegue](evidencias/leny_rag04_pilot_predeployment_r3.json) vincula esos hashes
con las evidencias, versiones instaladas y configuración usada en la prueba real.
Incluye Git modificado/no versionado; no se confunde HEAD con el código probado.

La [auditoría de deriva](evidencias/leny_rag04_pilot_drift_audit.md) compara los
freezes `semantic`369 y `coverage`374: respecto del semántico cambian el servicio
y la instrumentación por hooks opcionales, una prueba de integración y tres
archivos del harness corto. Se preservan los cinco archivos experimentales de
cobertura. **No se afirma identidad byte a byte con la ejecución semántica
histórica** ni se reconstruye un servicio antiguo sin copia exacta verificada.

El router real `get_leny_service()` no proporciona `coverage_verifier` y el
constructor usa `None`. Esa ruta conserva `rag4-v4`: el prototipo no evalúa,
no bloquea, no carga manifiestos y no añade contexto de cobertura. No tiene
interruptor de configuración/API que lo active. El ejercicio real corto exige
esas dos condiciones antes de probar el candidato. No se modificaron prompts,
selector, recuperador ni lógica funcional del chat durante esta consolidación.

### Resultados históricos y comprobación real nueva

| Alcance | Resultado | Interpretación |
|---|---|---|
| Histórico focalizado semántico | 14/14 naturales; 38/39 con evidencia; 44/48 rutas; 0 errores de contexto | Resultado anterior, no certificación del piloto congelado |
| Backend final de consolidación | 892 aprobadas, 1 omitida, 13,49s | Incluye las 8 pruebas del cambio reversible y DACL; 1 warning previo de pypdf |
| PostgreSQL aislado55432 | 104 aprobadas; 5 ensayos de migración excluidos; 51,86s | Cero DDL/migraciones e inferencias en esta suite |
| Frontend | 117/117 en18 archivos; 30,89s | Sin cambios de fuentes frontend |
| Lint/build frontend | Ambos exit0; build41,37s | Salida TEMP nueva; `dist` habitual intacto; warning previo de bundle grande |
| Comprobación real autorizada | 6/6 rutas correctas, 0 errores operacionales/contexto | Qwen y embeddings reales, datos sintéticos, sin navegador empresarial |

Comandos de prueba desde la raíz Windows:

```powershell
.\backend\venv\Scripts\python.exe -B backend/scripts/run_base_tests.py
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\run_leny_rag_quality.ps1 -Profile rag4_v1 -Mode contracts -EvidenceMode adaptive -TokenProbe -Ranking hybrid -Temperature 0 -Output documentacion\evidencias\leny_rag04_pilot_contracts.json -ExclusiveWindowConfirmed
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\run_leny_rag_quality.ps1 -Profile rag4_v1 -Mode supervised -EvidenceMode adaptive -TokenProbe -Ranking hybrid -Temperature 0 -Output documentacion\evidencias\leny_rag04_pilot_supervised_real.json -ExclusiveWindowConfirmed
```

El comando real ya terminó y no debe repetirse contra el mismo archivo. El modo
`supervised` selecciona seis casos existentes sin alterar corpus/gold y rechaza
política distinta de `rag4-v4` o cobertura inyectada. `contracts` no usa modelos;
el flag requerido por el wrapper no representa otra ventana GPU.

| Caso nuevo | Ruta observada/esperada | Evidencia enviada/citada | Latencia del turno |
|---|---|---|---:|
| natural-01 | rag/rag | proc-1 a proc-4 | 24,922s |
| natural-08 | rag/rag | proc-1 a proc-4 | 10,500s |
| acl-01, tarifa CAJA autorizada | rag/rag | price-1 | 10,187s |
| no_evidence-02 | no_evidence/no_evidence | ninguna | 4,203s |
| followup-03 | rag/rag | proc-1 a proc-4 | 10,125s |
| acl-07, tras revocación | no_evidence/no_evidence | ninguna; SQL elegible vacío | 4,203s |

Los identificadores completos llevan prefijo `rag04-`. Las
[observaciones reales](evidencias/leny_rag04_pilot_supervised_real.json) y su JSONL
conservan respuestas y trazas **sintéticas**. Los cuatro casos positivos tienen
Hit@5=4/4, Recall@5 medio=1,00 y Precision@5 media=1,00 en la evidencia enviada.
Hay13 fragmentos enviados/citados entre esos cuatro turnos, todos gold y
autorizados. No hay falsas abstenciones en4 consultas respondibles; las dos
rutas negativas no emiten fuentes. La métrica formal de abstención sin evidencia
usa1/1 de categoría `no_evidence`; la revocación es otro1/1 de categoría ACL.
Las dos naturales son2/2 de esta comprobación, **no una nueva evaluación14/14**.

El [score oficial sin cambios](evidencias/leny_rag04_pilot_supervised_score.json)
continúa en **`not_accepted`**: desarrollo incompleto, revisión humana ausente,
grounding/capacidades no medidos y categorías no incluidas en esta batería.
No se rellenan valoraciones humanas. Fidelidad semántica, exactitud de todas
las cifras/condiciones y utilidad no se deducen automáticamente de extractos
literales ni de la existencia de citas. Ningún umbral se relajó.

Las suites cubren JWT/Casbin, propiedad del historial, ACL SQL, publicaciones,
versiones, revocación/papelera, fuentes, streaming/cancelación, idempotencia,
cuotas y coordinación global. La
[evidencia PostgreSQL](evidencias/leny_rag04_pilot_contracts.json) confirma el
freeze durante la ejecución. La [evidencia frontend](evidencias/leny_rag04_pilot_frontend_20261021_105603.json)
conserva134 hashes idénticos antes/después. No equivalen a una nueva conversación
desde el navegador habitual.

RAM disponible antes/después de los seis turnos: 4479516672–4754198528 bytes
(aprox.4,17–4,43GiB). No es medición de pico. Latencia media10,690s,
rango4,203–24,922s; con6 muestras no se publica p95. La RTX4050 informa6141MiB
totales y0MiB usados **después** de la prueba; no se midió el pico VRAM de esta
ronda. No hay inferencias simultáneas, prueba de resistencia ni límites aumentados.
La ventana exclusiva finalizó; el clúster aislado arrancado por el harness se
detuvo. Versiones comprobadas: Python3.10.6, Ollama0.40.7, FastAPI0.115.6,
SQLAlchemy2.0.46, Pydantic2.12.5, HTTPX0.28.1, PostgreSQL17.9/pgvector0.8.7.

### Entorno habitual y respaldo recuperable

La [inspección previa de solo lectura](evidencias/leny_rag04_pilot_business_preflight.json)
confirma `bellaarte_db:5432`, revisión`20261020_0021`, vector0.8.7 en`leny`,
RAG/documentos/chat habilitados y perfil`legacy`. Se mantienen los cinco roles
oficiales y `DOC` preexistente, sin nuevos permisos. Hay2 documentos publicados,
2 originales, 3 indexaciones, 51 fragmentos y47 vectores existentes. No se
recontextualizó ni reparó ningún documento/índice; esos conteos abarcan estados
distintos y no justifican por sí solos una alteración.

El backend habitual responde `/health`200 y el diagnóstico ADMIN sin sesión401.
Vite devuelve200 en `http://localhost:5173`, escuchando en IPv6`::1`, sin5174.
La inspección inicial solo probó IPv4 y fue insuficiente para determinar su
estado; se conserva ese registro inicial con sufijo`initial_ipv4_only` y se
corrige el predespliegue. No se inició/reinició frontend ni otra instancia.
El worker manual está detenido, sin trabajos pendientes/en curso. Los índices
publicados se pueden consultar sin worker vivo. Estos estados previos no se
atribuyen a la consolidación.

Antes de cualquier activación se creó un respaldo conjunto privado de PostgreSQL
completo, originales, vista previa, metadatos y vectores, usando `pg_dump -Fc`,
el bloqueo documental existente y `build_bundle/verify_bundle`. El acceso de
verificación a la base habitual es de solo lectura; no se invoca su recuperación
documental, arranque de aplicación o seeds. Se guardan credenciales y originales
fuera del webroot y de Git, con ACL Windows del propietario/SYSTEM/Administradores.

[Recuperación comprobada](evidencias/leny_rag04_pilot_recovery_r3.json): paquete
4713984 bytes, SHA-256
`0f8c4e0fff285543b67b14d09735b07e5ca73ada20f9454ee7beb8f135278711`.
Se verificaron2 originales y1 vista previa. Se extrajo en una raíz privada nueva
y se restauró realmente con `pg_restore --no-owner --no-privileges
--exit-on-error` en una base aleatoria nueva de55432, con CONNECT público
revocado. Coinciden revisión, vector0.8.7, ocho huellas agregadas de metadatos/
fragmentos/vectores y hashes/tamaños de originales. La base temporal se eliminó
y se detuvo solamente el clúster iniciado por este ensayo. Se conserva el
material privado de recuperación; no se publica su contenido.

El primer ensayo operativo se detuvo por usar `PG_DUMP_PATH` opcional vacío al
localizar `pg_restore`, aunque `pg_dump` se resolvía por PATH. Se corrigió para
reutilizar `resolve_pg_dump_path()`. El paquete fallido y su prueba privada se
conservaron y el ensayo `r2` tuvo recuperación correcta. La revisión técnica
posterior detectó que `os.replace` podía sustituir una DACL restringida de
`.env` por la heredada del directorio. Se corrigió el helper para copiar la DACL
y su protección al temporal **antes de escribir credenciales**; falla cerrado
si no puede hacerlo. Dos pruebas Windows nativas con datos sintéticos comprueban
permisos idénticos antes/después, reversión y fallo sin sustituir `.env`.
Se congeló `r3` y se repitió con éxito su respaldo/recuperación; se conservan los
paquetes y evidencias anteriores. No cambió ningún componente del chat probado
con Qwen ni se requirió repetir inferencias por este ajuste operativo. Ningún
ensayo modificó la base empresarial. La revisión independiente de esta corrección
no encontró otro defecto concreto; no sustituye las pruebas ejecutadas.

La copia privada de `.env` anterior, propuesta y código está bajo
`%LOCALAPPDATA%\BAB_VDOS\leny-pilot\leny-rag-v1-piloto-20261021-r3`.
Su `recovery-proof.json` localiza el respaldo completo. El guard de activación
recomprueba ese ZIP, el archivo de código y cada hash funcional, además de la
huella anterior del `.env`. Rechaza sobrescribir una configuración intervenida.
El `.env` habitual, la biblioteca y el código probado siguen intactos tras el
ensayo. No se presenta esta recuperación acotada como certificación integral
de continuidad empresarial ante cualquier desastre.

### Cambio preparado, alcance global y reversión

**Todavía no aplicado.** La variable implementada es `LENY_RAG_PROFILE`, nunca
`LENY_RAG_QUALITY_PROFILE`. Para reproducir la configuración comprobada se
proponen exactamente cinco valores de `backend/.env`:

| Variable | Habitual anterior | Piloto preparado |
|---|---|---|
| `LENY_RAG_PROFILE` | `legacy` | `rag4_v1` |
| `LENY_RAG_EVIDENCE_MODE` | `fixed` | `adaptive` |
| `LENY_RAG_RANKING` | `semantic` | `hybrid` |
| `LENY_RAG_ADAPTIVE_TOKEN_PROBE` | `false` | `true` |
| `LENY_TEMPERATURE` | `0.3` | `0.0` |

Se conservan chat-RAG habilitado, modelos/digests, residencia0, contexto4096,
generación768, máximo5 fuentes/20 candidatos, CPU4, cuota5/60s y márgenes2/1GiB.
La temperatura es una configuración compartida por las llamadas conversacionales
de LENY, no solo por el selector documental. El alcance del cambio es **global
para todos los usuarios actualmente autorizados**, no un despliegue técnicamente
restringido a ADMIN. Se recomienda que el propietario lo pruebe primero con
ADMIN como organización de las pruebas, sin crear un permiso nuevo.

Tras la confirmación explícita de la Fase4 se sustituirá solo ese `.env`, se
recargará el backend para descartar `Settings`/servicio cacheados; se reutilizará
el frontend ya saludable en5173, sin reiniciarlo ni abrir5174. El worker
manual no necesita reinicio para leer publicaciones y se mantendrá detenido
hasta que se solicite iniciar indexaciones. No se reinicia Ollama ni se detienen
procesos ajenos. No se modifica el frontend ni se requieren nuevas migraciones.

Operación preparada, **no ejecutada**, desde la raíz:

```powershell
$pilotPacket=Join-Path $env:LOCALAPPDATA 'BAB_VDOS\leny-pilot\leny-rag-v1-piloto-20261021-r3'
.\backend\venv\Scripts\python.exe -B backend/scripts/leny_rag_pilot_profile.py activate --private-dir $pilotPacket --confirm-activation
```

El flag de CLI no sustituye la confirmación del propietario. Después de recargar
se comprobarán los valores efectivos desde el diagnóstico ADMIN existente, no
solo desde el archivo: perfil, ranking, evidencia, probe y temperatura. También
sesión/historial, estado, fuentes/ACL y chat breves. El contenido y utilidad de
los documentos empresariales los evaluará el propietario personalmente; esta
preparación no ejecutó ese E2E ni copió documentos a fixtures, reportes o logs.

Reversión del perfil, **sin restaurar ni hacer rollback de PostgreSQL**:

```powershell
.\backend\venv\Scripts\python.exe -B backend/scripts/leny_rag_pilot_profile.py rollback --private-dir $pilotPacket --confirm-rollback
```

Restaura los bytes exactos del `.env` anterior y exige recargar el backend y
confirmar `legacy` efectivo. Si hubo otra edición de configuración, falla sin
sobrescribir y requiere revisar esa diferencia. La reversión no borra historial,
usuarios, documentos, publicaciones ni índices y no requiere detener frontend.
Ante filtración, corrupción, autenticación persistentemente rota, historial
perdido/bloqueado, recursos inestables o configuración efectiva incorrecta,
se detendrá el piloto y se revertirá inmediatamente ese cambio de configuración.

### Archivos de esta consolidación y pendientes

Modificados: `backend/scripts/run_leny_rag_quality.py`, su wrapper`.ps1`,
`backend/tests/test_leny_rag_quality_runner.py`, este reporte y `MODULO_LENY.md`.
Nuevos operativos: `backend/scripts/leny_rag_pilot_profile.py`,
`prepare_leny_rag_pilot_backup.py`, su wrapper`.ps1` y
`backend/tests/test_leny_rag_pilot_profile.py`. Evidencias nuevas
`leny_rag04_pilot_*`; ninguna evidencia histórica se elimina. El helper temporal
`.codex/tmp/finalize_leny_pilot.py` registra inventarios, sin activar servicios.
No hay dependencias, endpoints, componentes React o migraciones nuevos.

Persisten **acl-04** (tarifa autorizada pero ajena a inventario) y
**no_evidence-01** (procedimiento general atribuido a una especialidad ausente).
Son errores de pertinencia, no concesiones de ACL; una fuente autorizada y una
cita literal pueden respaldar mal la pregunta. Tampoco se garantiza síntesis
natural: la salida es extractiva y puede resultar extensa o pedir aclaración.
La latencia fría y los procedimientos mayores que el contexto siguen limitados
por el hardware/configuración. No se inicia otra optimización ni verificador.

Pendientes: confirmación de activación, verificación del perfil efectivo y E2E
habitual posterior, evaluación empresarial del propietario, rúbrica humana y
preparación/custodia independiente de36 reservados. Los84 no se repitieron sobre
la versión final. Los paquetes A/B y plantillas anteriores continúan disponibles
sin rellenar. Cobertura, NLI, modelos nuevos y síntesis generativa controlada
quedan pospuestos. **La preparación técnica está terminada; el entorno habitual
permanece en `legacy` esperando la confirmación de activación.**

## Activación real autorizada del piloto en el ERP habitual (21/10/2026)

**ACTIVO — PILOTO SUPERVISADO — ACEPTACIÓN FORMAL PENDIENTE.** El propietario
confirmó expresamente «Activalo tienes mi autorización». Se aplicó el paquete
`leny-rag-v1-piloto-20261021-r3` a la instalación original y se completó la
comprobación técnica desde React con la sesión ADMIN habitual. El apartado de
predespliegue anterior documenta el estado previo a esta autorización, no el
estado vigente.

La [evidencia de activación](evidencias/leny_rag04_pilot_activation_verified.json)
vincula el [evento](evidencias/leny_rag04_pilot_activation_event.json), la
[lectura anterior](evidencias/leny_rag04_pilot_activation_before.json) y la
[lectura posterior](evidencias/leny_rag04_pilot_activation_after.json), con hashes.
El freeze funcional378 sigue coincidiendo; no se modificó el código probado.

Se aplicaron exclusivamente los cinco valores aprobados de `.env`. El panel
ADMIN existente, consultado nuevamente después de recargar la página, muestra
los valores **efectivos** del backend:

| Configuración efectiva | Valor |
|---|---|
| `rag_profile` | `rag4_v1` |
| `rag_evidence_mode` | `adaptive` |
| `rag_ranking` | `hybrid` |
| `rag_adaptive_token_probe` | `true` |
| `temperature` | `0` |

La respuesta nueva persistida confirma además política`rag4-v4` y modelo
`qwen3.5:4b-q4_K_M`. El servicio conserva cobertura experimental sin inyectar.
RAG-chat sigue habilitado, contexto4096/generación768, residencia0 y cuota5/60s.
La revisión continúa en0021; modelos, digests, embeddings y permisos se mantienen.

Se solicitó recarga al supervisor Uvicorn existente modificando únicamente el
mtime de `backend/main.py`, sin cambiar sus bytes: el hijo4284 fue sustituido por
16448. Backend8000 sigue saludable; Vite existente en`localhost:5173` no se
reinició y no se abrió5174. No se reinició Ollama, PostgreSQL ni ningún servicio
ajeno. El worker permanece manual/detenido, sin trabajos pendientes. El perfil
es global para los usuarios autorizados, no exclusivo de ADMIN.

El primer intento se revirtió preventivamente antes de recargar el backend:
una comparación del descriptor de seguridad completo de `.env` dio diferencia.
Se confirmó la recuperación de los bytes anteriores y `legacy` efectivo desde
el panel. En el reintento se comprobó explícitamente DACL y protección, además
de descriptor completo, propietario y grupo: **todos idénticos antes/después**
de la sustitución final. Se conserva el registro del intento y del rollback;
no se presenta aquella diferencia inicial como una filtración o pérdida de DACL
confirmada. El helper congelado no se modificó para esta activación.

### Comprobación real y conservación de datos

Desde el chat original se envió un único saludo «Hola». La UI pasó al estado
`Detener`, recibió respuesta local y finalizó en`completed`. Se recargó el ERP
y se recuperó la misma conversación con sus dos mensajes. La respuesta tiene
608 bytes, razón`identity_or_greeting`, sin recuperación documental. No se
abrieron conversaciones anteriores ni fragmentos empresariales privados.

Las huellas agregadas anteriores/posteriores comprueban:

- **42 tablas públicas sin cambios** en el conjunto comparado; se excluyen
  auditoría y cuentas por su actividad normal de sesión/autenticación.
- Documentos, originales/metadatos, carpetas/ACL, publicaciones, versiones,
  índices,51 fragmentos y47 vectores conservados. Las ocho huellas documentales
  coinciden también con el respaldo recuperable.
- Historial previo sin cambios; se añadió únicamente una conversación técnica
  con dos mensajes, junto con sus registros normales de auditoría/cuota.
- Códigos de roles idénticos: los cinco oficiales y`DOC` preexistente intacto.
- Inferencia`idle`, cero generaciones activas, cero titulares del bloqueo
  asesor global y cero modelos residentes al cerrar la comprobación.
- La consulta SQL de elegibilidad vigente para el actor autenticado identifica
  2 documentos publicados y47 fragmentos; solo devolvió conteos, sin sus textos.
  Conversaciones, diagnóstico y fuentes requieren autenticación: los tres
  endpoints comprobados sin JWT devolvieron401.

Esto confirma activación, sesión, chat e historial. **No equivale a E2E
semántico empresarial ni a verificar desde el navegador una fuente privada**:
esa revisión documental/navegación corresponde al propietario. No se repitió
cancelación real, resistencia,84 casos ni36 reservados durante el despliegue.
Sus suites técnicas y evidencias previas se conservan sin atribuirles una nueva
ejecución. Los resultados negativos históricos no se eliminan.

Persisten los dos errores críticos semánticos conocidos de pertinencia. Como
observación adicional no bloqueante del saludo, Qwen denominó erróneamente
«Bolívares» a Bs y describió capacidades generales sin precisar del todo sus
límites operativos. No se ejecutó ninguna operación financiera ni se consultaron
tablas comerciales mediante el modelo. Se registra para revisión humana futura;
no se alteran prompts o arquitectura en esta entrega.

La reversión preparada a`legacy` permanece disponible con el paquete privado
`r3`: restaura los cinco valores anteriores mediante `rollback` y recarga el
backend, sin restauración ni rollback de base de datos. No hace falta otra
aprobación para la reversión inmediata ante los incidentes graves ya definidos.
No se declara SPEC-04 formalmente aceptada. El propietario puede realizar ahora
las pruebas empresariales supervisadas y completar la plantilla privada indicada
en la guía.

## Ciclo de vida automático de LENY (02/11/2026)

Uvicorn inicia el worker RAG y, si no existe un servidor Ollama local, inicia
uno propio. El cierre ordenado espera al worker y detiene solo procesos propios;
Ollama y workers preexistentes permanecen externos. Los modelos se cargan bajo
demanda. El cierre administrativo reencola el trabajo sin perder vectores y no
reemplaza la cancelación explícita del usuario. Persisten los controles de
cuarentena ante una inferencia cuyo resultado no pueda confirmarse.

Implementación: `backend/app/services/leny_runtime.py`,
`leny_runtime_process.py`, ciclo de vida en `backend/app/main.py`, configuración,
worker y CLI existentes. No se añadieron dependencias ni migraciones. Las
pruebas incluyen 914 backend aprobadas, una omitida y un warning previo;
106 PostgreSQL aisladas aprobadas, cinco ensayos de migración excluidos; y
comprobaciones nativas de Job Objects, exclusión y Ollama propio sin modelos.
[Evidencia nativa](evidencias/leny_runtime_native_owned_ollama_20261102.json),
[PostgreSQL](evidencias/leny_runtime_postgres_20261102.json) y
[dos ciclos Uvicorn](evidencias/leny_runtime_uvicorn_20261102.json).
Los ciclos reales fueron dos inicios/cierres ordenados, no una ejecución real
del supervisor `--reload`. No se realizaron inferencias ni pruebas semánticas
empresariales. Los hashes del antiguo freeze piloto ya no representan estos
archivos modificados; no cambia el perfil `rag4_v1` ni su estado de aceptación.
