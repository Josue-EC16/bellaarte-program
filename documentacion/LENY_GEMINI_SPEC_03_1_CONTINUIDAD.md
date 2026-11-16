# LENY SPEC-03.1 — continuidad del habitual y retirada del provisional

Inicio: 13/11/2026. Actualización operacional: **14/11/2026**, tras autorización expresa del propietario para activar/reiniciar y dejar su revisión manual como segunda verificación. **Continuidad habitual activada en el ERP original**, Gemini y Qwen habilitados, Qwen predeterminado. Comprobación técnica realizada; aceptación semántica humana pendiente. Las abstenciones observadas se conservan y no se declara perfección conversacional ni aceptación integral de SPEC-03.1.

## 1. Diagnóstico del contexto

La conversación indicada por el propietario utilizó Gemini y `quality_profile=baseline`, política `rag-v11-synthesis-v1`. No ejecutó la candidata SPEC-03. El segundo turno se guardó como `contextual_unavailable`, sin fuentes; la pregunta explícita posterior sí produjo una referencia. Se consultaron únicamente metadatos/códigos para este diagnóstico público, sin revelar identidades ni respuestas empresariales.

La respuesta documental anterior tenía 207 caracteres: no faltaba presupuesto. `begin_turn` la excluía de la memoria ordinaria por `context_eligible=false`, mientras `topic_history` conservaba solo una pregunta abreviada. La memoria documental ampliada se ejecutaba únicamente en el provisional y además dependía de reconocer expresiones por regex.

## 2. Causa del rechazo del gerente

«¿Quién es el gerente?» no obtenía una decisión determinista empresarial. Pasaba al clasificador contextual con un antecedente incompleto y podía terminar como `unavailable` antes de recuperar documentos. La reproducción autenticada A volvió a obtener ese código; «¿Dónde está documentado?» obtuvo incluso `contextual_manipulation`. Son rechazos de intención, no fallos demostrados del embedding o del validador de síntesis.

`PRUEBA_CONOCIMIENTO_II` estaba activo, publicado y su versión/índice/huella coincidían con el consentimiento externo existente. Ese rechazo no fue causado por la barrera externa. En la inspección había aproximadamente 5,1 GiB libres, por encima de la guarda de 2 GiB. Se detectó y sustituyó controladamente Uvicorn `--reload` antes de editar.

## 3. Perfil efectivo y retirada de SPEC-03

Por decisión expresa del propietario, se mejora **solo el habitual** y se retira la opción provisional. No se crea otro perfil ni se ejecuta migración. React conserva únicamente Qwen/Gemini; creación envía el proveedor y no `quality_profile`. El servidor rechaza nuevas solicitudes `spec03` con `LENY_PROFILE_RETIRED`/409; acepta compatibilidad habitual sin perfil o `baseline`.

Conversaciones antiguas SPEC-03 mantienen mensajes, fuentes, proveedor y metadatos históricos sin UPDATE masivo. Sus nuevas respuestas pasan por el habitual. La interfaz informa de la transición. Los módulos y evidencias antiguas se conservan para diagnóstico; su síntesis no se trasplanta al habitual.

## 4. Causas adicionales de falsos rechazos

- Referencias como «sus responsabilidades», «¿Quién los controla?» y «¿Dónde está documentado?» no compartían un reconocimiento consistente.
- Un artículo como «los» en «los vestidos» se confundió en el primer ajuste con pronombre dependiente; una prueba positiva detectó y corrigió el defecto.
- Las presentaciones lingüísticas `sources`, `detail` o `procedure` se estaban pasando como modos de empaquetado que este no admite. Ahora presentación e interfaz del RAG están separadas.
- En modo linked se sustituía la base del prompt y podían perderse las instrucciones adicionales de contexto. Se compone sobre el prompt ya preparado.
- Falta de evidencia se confundió inicialmente con revocación. Se separaron ausencia, revocación, contenido sensible y error operativo; no se inventa una causa común.
- Tras un fallo del proveedor, una respuesta antigua de otro tema no debe convertirse en la fuente del turno fallido. El tema puede conservarse desde la pregunta del usuario, sin reutilizar la respuesta anterior como evidencia.
- C4 reprodujo otro falso rechazo: el intérprete devolvió capacidad no disponible para «¿Y después?» con antecedente documental vigente. La corrección admite solo referencias informativas de presentación reconocibles y con fuentes actuales; vuelve al RAG y conserva la validación. No normaliza mensajes que además soliciten modificar inventario o ejecutar SQL. C5 verificó posteriormente esa cadena.

## 5. Empresa, tema y referente

Se reutiliza `leny_spec03_context.py` como helper interno del habitual, pese a su nombre histórico. Se distinguen `business_entity`, `topic` y `referent`, más pares conversacionales y procedencia de fuentes. BELLAARTE es el marco predeterminado, no una fuente de hechos. Menciones explícitas del usuario a otra empresa prevalecen y se conservan separadas del tema; volver a mencionar BELLAARTE restablece esa entidad. El reconocimiento determinista de nombres no es universal: las demás expresiones se interpretan con la consulta original, sin inventar relaciones.

Se inspeccionan hasta 40 mensajes propios para seleccionar un máximo de tres pares/6000 bytes. No se envía todo el historial. Se priorizan explicaciones completas; si una respuesta larga no cabe se conserva un extracto de párrafos completos y se marca la omisión, sin certificar progreso completo. Empresa/tema/referente son datos interpretativos, nunca respaldo documental ni tareas ejecutadas.

## 6. Archivos modificados

| Grupo | Rutas principales |
|---|---|
| Coordinación y memoria | `backend/app/services/leny_service.py`, `leny_spec03_context.py` |
| Selección y síntesis habitual | `backend/app/services/leny_rag_selection.py`, `leny_rag_synthesis.py` |
| Configuración y diagnóstico | `backend/app/core/config.py`, `backend/.env.example`, `leny_rag_diagnostics.py`, `leny_external_scope.py` |
| Retirada por API | `backend/app/api/routers/leny.py`; esquema histórico conservado |
| Interfaz | `frontend/src/pages/leny/LenyPage.jsx`, `useLenyChat.js`, `LenyPage.test.jsx` |
| Evaluación | Nuevas pruebas `test_leny_continuity*.py`, integración `test_leny_continuity_sql.py`, scripts de paquete/estado SPEC03.1; launchers existentes con salida separada |

Rutas abreviadas de servicios relativas a `backend/app/services/`. El checkpoint privado inicial está señalado por `%LOCALAPPDATA%\BAB_VDOS\leny-spec031\active.txt`. Conserva hashes y archivos previos; no copia la API Key ni el `.env` completo. La evidencia nueva usa prefijo `leny_spec031_`; no reemplaza los informes SPEC-03.

## 7. Clasificación y enrutamiento

La entrada original pasa primero las guardas. Operaciones ERP, SQL, manipulación y acceso indebido no adquieren autorización por mencionar un cargo. Una pregunta informativa breve y clara puede ir directamente a RAG sin otra inferencia. Referencias o intenciones no resueltas usan una interpretación estructurada; no se encadenan los clasificadores anteriores además de ella. Mensajes con varios pedidos no obtienen pase directo por una palabra empresarial.

La reformulación conserva la pregunta original y solo orienta la recuperación. Un cambio de tema elimina el anclaje documental anterior, conservando la empresa. Identidad/funciones internas sin evidencia no se sustituyen por conocimiento general. Asesoramiento o redacción legítimos siguen permitidos y se identifican como generales.

## 8. Seguimientos

Contexto del historial consultado por propietario y revalidado con SQL, publicación y consentimiento externo antes de transmitir. Una fuente revocada no se reconstruye desde el historial. Para «¿Dónde está documentado?» se usan fuentes actuales del antecedente; si el turno anterior no tuvo respaldo, se explica esa ausencia sin citar otro tema ni llamar a eso revocación.

«¿Y después?» se interpreta respecto de lo explicado, no de una ejecución empresarial. Selección y síntesis reciben contexto conversacional pertinente; una etapa no documentada no se inventa. Si el procedimiento o el corpus son parciales, la continuidad no garantiza que exista otro paso respaldado. Los resultados reales se reportan sin convertir toda abstención en error ni toda respuesta en éxito.

## 9. Validadores focalizados

Se conserva el contrato habitual `blocks`, validación anterior y sus controles de cifras/unidades/condiciones. No se adopta el esquema atómico de la candidata retirada. Se flexibilizó la pertinencia de sujetos explícitos: «la modista revisa…» no debe necesitar la frase literal «debe» para ser candidata. Siguen bloqueadas atribuciones ambiguas a otro cargo; el título del archivo no acredita funciones.

No se eliminaron comprobaciones de referencias, ACL, publicación o salida completa. Una heurística lexical no prueba implicación semántica. Permanecen límites conocidos del validador habitual, incluido su tratamiento conservador de cantidades; no se declara verificación universal de afirmaciones. Los pares positivos/negativos y la revisión humana siguen siendo necesarios.

**Corrección local adicional del 14/11:** la petición de crear una estructura de manual falló nuevamente en Qwen (`LENY_RAG_REVIEW_INVALID`). Tras validar el ámbito original, una solicitud inequívoca de redacción adaptable sin referencia documental puede ir a generación general, con encabezado y alcance general impuestos por backend. Reutiliza `intent`, `DRAFTING` y `explicit_source_request`; no relaja `verify_plan`, no acepta un JSON inválido y no concede permisos. Una petición que diga «según el manual» sigue usando RAG; una operación o solicitud mixta insegura no recibe este pase. La excepción está acotada a Qwen, síntesis habitual e interruptor de continuidad activo. No cambia sus parámetros ni añade inferencias. Su resultado real se registra en G.

## 10. RAG y fuentes

Sin reconstruir el buscador: PostgreSQL/pgvector, embeddings CPU/1024, ranking híbrido, títulos, índices, 20 candidatos y cinco fragmentos finales conservados. Sin reindexación ni cambios de publicaciones/ACL. Contexto estructural existente y fuentes se revalidan; no se inventan localizadores. El consentimiento externo sigue restringido a versiones aprobadas, no a todas las publicaciones presentes o futuras.

## 11. Pruebas automatizadas

Última regresión: **1160 pruebas backend aprobadas en 17,19 s**, más **una prueba de importación aislada en 1,08 s**. Una omitida histórica y una deseleccionada en el proceso principal, ejecutada aparte: 1161 aprobadas distintas. Aviso de deprecación de pypdf en una fixture de archivo malicioso, sin fallo. Doce comprobaciones PostgreSQL/pgvector sintéticas aprobadas en 7,34 s, sin DDL/inferencia ni base empresarial. Frontend: 54 aprobadas; ESLint dirigido correcto. `pip check` sin incompatibilidades. Build temporal: 4089 módulos, 26,18 s, aviso preexistente de bundle grande; no se sustituyó `dist`.

**Regresión final después del ajuste Qwen, 14/11:** 1167 aprobadas en 22,07 s más una importación aislada en 1,16 s: **1168 aprobadas distintas**, una omitida y una deselección ejecutada aparte. Siete pruebas nuevas verifican redacción general identificada, referencia explícita que conserva RAG y solicitudes operativas/maliciosas sin generación. La primera ejecución tuvo tres fallos en estas pruebas nuevas: dos dobles devolvían el esquema de evidencia al clasificador de ámbito y una exigía rechazo donde una aclaración segura también era válida. Se corrigieron esos dobles/aserciones, sin cambiar las guardas para aprobar. La ejecución fallida permanece en `leny_spec031_local_drafting_attempt1.xml`. Las pruebas SQL/frontend anteriores conservan su fecha y no se presentan como reejecutadas el 14/11: no hubo cambios posteriores en sus componentes.

Pruebas nuevas cubren artículos frente a pronombres, empresa explícita, revalidación del historial, cambio de tema, fallo del proveedor sin préstamo de fuentes, ausencia frente a revocación, contrato `blocks`, modos de empaquetado, retirada y renovación normal de sesión del evaluador. Mocks no acreditan calidad del modelo.

Comandos desde raíz:

```powershell
backend\venv\Scripts\python.exe -B backend/scripts/run_leny_spec03_regression.py --continuity
& backend/scripts/test_leny_spec03_schema.ps1 -ContinuityTests
backend\venv\Scripts\python.exe -B backend/scripts/build_leny_spec031_review.py
backend\venv\Scripts\python.exe -B backend/scripts/collect_leny_spec031_state.py
backend\venv\Scripts\python.exe -B backend/scripts/measure_leny_spec03_resources.py --continuity
```

La integración usa el clúster sintético 55432 solo tras verificar su manifiesto y destino. La regresión se ejecuta con configuración sanitizada y guardas contra SQL/procesos; la prueba de importación tiene su propio control de red. No se ejecutaron fixtures destructivas contra el ERP habitual.

## 12. Pruebas reales Gemini

Sesión normal, credenciales/token en memoria, API original y NDJSON completo. A reproduce el habitual anterior; B conserva fallos del provisional; C inicial y siguientes conservan también intentos fallidos. El código de contexto se importa de forma diferida: B pudo observar cambios locales durante su preparación y **no es una comparación pura e inmutable**. No se oculta esa limitación ni se reabre un perfil para fabricar una comparación favorable.

La primera cadena corregida respondió gerente con una fuente, donde A había rechazado. También mostró abstenciones y una clasificación errónea de ausencia como revocación, corregida posteriormente. Hubo indisponibilidad de Google y bloqueos por cuota normal del chat. Se mantuvieron los intentos y se respetó `Retry-After`; no se repiten solo hasta lograr éxito.

La sesión evaluadora terminó durante el lote; se conservó el punto de continuación y se pidió nueva autenticación. Se añadió renovación normal entre casos para lotes largos, sin modificar JWT, cookies del ERP, usuarios ni sesiones mediante SQL. Los códigos operativos no cuentan como falsos rechazos semánticos.

Resultado antes de activar: **11 trabajos / 83 intentos conservados**, no 83 éxitos ni 83 observaciones independientes. Tras la activación se agregaron cuatro trabajos con trece intentos: **15 trabajos / 96 intentos totales**. Incluyen desarrollo iterativo, seguridad y fallos. El primer trabajo Qwen quedó pausado por cuota: su segundo caso no ejecutado no se cuenta como intento. No se reenvió ningún request consumido para sustituir su resultado; G es una comparación posterior a un cambio de código identificado.

| Trabajo | N intentos | Respuestas con fuentes y alcance documentado/parcial | Generales | Errores o límites relevantes |
|---|---:|---:|---:|---|
| A habitual anterior | 11 | 5 | 1 | Gerente rechazado antes de RAG; fuentes clasificadas como manipulación |
| B provisional histórico | 11 | 2 | 2 | Siete errores; referencia no inmutable por imports diferidos |
| C primera corrección | 11 | 3 | 0 | Seis errores; ausencia confundida con revocación, luego corregida |
| C2 cadena intermedia | 11 | 2 | 0 | Dos fallos del proveedor; siete aclaraciones conservadas |
| C3 cobertura | 22 | 11 | 2 | Una cuota y un bloqueo sensible HTTP; cuatro aclaraciones y tres rechazos esperados o por adjudicar |
| C4 confirmación | 8 | 4 | 1 | Un falso rechazo de seguimiento y dos aclaraciones; motivó ajuste acotado |
| C5 referencias corregidas | 4 | 4 | 0 | Cadena completa, seis referencias abiertas HTTP 200, cuatro historiales coincidentes |
| C6 conversación histórica | 1 | 1 | 0 | Conservó `quality_profile=spec03` en datos, ejecutó política habitual corregida |
| Z Qwen inicial | 1 | 0 | 0 | HTTP 429, segundo caso sin ejecutar |
| Z2 Qwen | 2 | 0 | 0 | Un error `LENY_RAG_REVIEW_INVALID` al seleccionar para manual; operación bloqueada correctamente |
| Z3 Qwen | 1 | 1 | 0 | Generación real completada y cinco fuentes accesibles; no certifica calidad semántica |
| D habitual ya activo | 4 | 2 | 0 | Ubicación y gerente documentados; responsabilidades sin evidencia y petición posterior de fuente aclaradas |
| E Qwen tras activar | 3 | 1 | 0 | Se reproduce error de selección del manual; otra generación completada; operación rechazada |
| F procedimiento habitual activo | 4 | 1 | 0 | Confección parcial; seguimiento reconocido, pero selector devuelve absent; dos aclaraciones posteriores |
| G Qwen redacción corregida | 2 | 0 | 1 | Misma petición de manual respondida como general; operación rechazada |

En C3, 24/24 referencias consultadas respondieron HTTP 200. El control de historial no concluyó en todos los intentos: hubo admisiones rechazadas sin mensaje y una expiración de sesión posterior a la respuesta. Se conservan indicadores nulos/falsos y estados HTTP individuales, sin presentarlos como coincidencias verificadas.

## 13. Comparación antes/después

Los resultados individuales, fuentes accesibles, estado, motivos, tiempos y denominadores se publican sin textos privados en `evidencias/leny_spec031_comparison.json`. El paquete humano conserva preguntas, respuestas, contexto, pasajes y rúbrica; no incluye valoraciones humanas prellenadas. Los rechazos de gerente y fuentes se distinguen de insuficiencia documental, proveedor y cuotas.

No se atribuye fidelidad a `answered`, HTTP 200, JSON o fuente accesible. No se calculan Hit/Recall ni porcentajes de fidelidad sin gold adjudicado. Los 36 holdout no se usaron; las ocho preguntas reservadas del propietario siguen sin abrirse.

La referencia A y C4 utilizan la misma pregunta sobre gerente: A la rechaza por `contextual_unavailable`; C4 produce una respuesta con fuente. C5 contiene cuatro turnos consecutivos en una conversación: confección (alcance parcial), continuación, responsable y fuentes. Sus textos y pasajes reales están exclusivamente en el paquete privado. La ausencia de repetición indebida, la atribución del responsable y la completitud deben ser calificadas por el propietario, no se deducen de los estados.

Paquete privado: `%LOCALAPPDATA%\BAB_VDOS\leny-spec031\20261113-004205\review\human-review\REVISION_HUMANA_SPEC031.html`. Contiene 20 casos de desarrollo y ocho espacios reservados vacíos, rúbrica editable y exportación local sin red. Incluye D y la petición Qwen corregida; las condiciones no ejecutadas no crean paneles vacíos. `APENDICE_TODOS_LOS_INTENTOS.html` y el JSON adjunto conservan los **96 intentos**, incluidos los negativos y fallidos. No abrir ni subir el paquete en servicios externos. No se introdujeron calificaciones humanas.

La comparación C5/F es especialmente relevante para revisión: comparten las cuatro preguntas congeladas. En el primer turno fueron idénticos los diez candidatos y los fragmentos seleccionados; las redacciones generadas fueron diferentes. En F, «¿Y después?» conservó un par de contexto y se interpretó como `followup`, con diez candidatos recuperados; el selector declaró `scope=matched`, `relation=absent`, sin elegir evidencia. No fue un rechazo por herramientas ni una guarda de RAM. C5 había seleccionado respaldo y contestado ese seguimiento. Es una diferencia real en recuperación/selección contextual que **no queda resuelta ni adjudicada semánticamente** con el resultado de C5. No se obligó al selector a aceptar evidencia ni se repitió hasta obtener una respuesta favorable.

## 14. Seguridad y Qwen

JWT/Casbin, propietario, ACL, publicación, consentimiento, cuotas, coordinación durable y barrera de salida intactos. Casos de documentos no publicados/revocados, otro propietario y consentimiento revocado se realizan con sintéticos, sin modificar permisos empresariales. El modelo no obtiene SQL, herramientas ni acciones ERP.

Qwen mantiene proveedor predeterminado, modelo/parámetros y recorrido local. Ambos proveedores deben permanecer habilitados; un error de Google no provoca cambio silencioso. La detección determinista de información sensible es parcial y no se presenta como anonimización universal.

Z3 completó generación, NDJSON, persistencia y apertura de fuentes en 33,813 s. Z2 falló en selección documental para la solicitud de manual en 18,938 s y E volvió a reproducir el error en 23,406 s. Tras la corrección focalizada de ruta, G respondió esa misma petición como `context_drafting`/`general`, sin fuentes, en 21,172 s; el historial coincidió. No se publicaron datos internos como respuesta al fallo. La operación de inventario continuó rechazada en G, 0,203 s. Esto demuestra esa corrección concreta, no que Qwen haya superado todas las preguntas.

Comprobación final local: `/health` 200, ruta LENY protegida sin credenciales 401, página React 200, Ollama 200 con Qwen instalado. El evaluador normal se cerró al terminar; usuario, contraseña y token no se guardaron. Ningún cambio comercial, migración, reindexación, publicación o ACL formó parte de esta corrección.

## 15. Tokens, latencia y memoria

Gemini 3.1 Flash-Lite, medium, entrada 32678/salida 8192 y cuotas 15 RPM/250000 TPM/500 RPD conservadas. Continúa el máximo técnico de evaluación de 150 llamadas Google/día. Los agregados incluyen errores y uso desconocido, sin pensamiento interno ni prompts en logs técnicos. Embeddings locales siguen requiriendo 2 GiB disponibles; no se redujo esa guarda.

Tiempos por turno y llamadas se comparan separando fallos de Google/cuota y respuesta documental. Sin p95 con menos de 30 muestras comparables ni afirmación de aceleración general. Pruebas de contrato ejecutadas en paralelo pueden afectar tiempos ambientales: estos lotes no son un benchmark de rendimiento aislado.

C5: 22,156 / 10,688 / 10,750 / 17,937 s; mediana 14,3435 s, N=4. C6: 12,140 s, N=1. C5 utilizó once llamadas Google en cuatro turnos: 18289 tokens de entrada, 1041 de salida y 1962 de pensamiento informados; no son once llamadas nuevas por turno. C6: dos llamadas, 2660/97/628 tokens respectivamente. Totales durables de evaluación al cierre: 134 HTTP Google, por debajo del tope de 150; errores y consumos desconocidos permanecen en `leny_spec031_effective_state.json`.

Estos 134 HTTP corresponden al cierre inicial, no al contador diario del 14/11. La verificación operacional nueva consumió **diez HTTP Google**: D seis (8114 entrada / 285 salida / 1482 pensamiento) y F cuatro (7914 / 391 / 958), sin consumos desconocidos en esos lotes. E/G son locales. La primera preparación de D fue rechazada por revisión automática porque la guarda propuesta solo reservaba ocho llamadas en el peor caso; no se ejecutó. La consulta real confirmó cero usadas ese día y se preparó D/F con un margen mínimo de 40 bajo el tope durable de 150. No se amplió ninguna cuota.

D: 22,813 / 8,281 / 10,266 / 0,156 s, mediana 9,2735 s. F: 9,797 / 9,265 / 0,157 / 0,172 s, mediana 4,7185 s; incluye tres aclaraciones y no se interpreta como aceleración. G: 21,172 / 0,203 s, orientación y rechazo respectivamente; no son una muestra homogénea. Memoria ambiental al cierre del 14/11: 2,14 / 2,17 / 2,16 GiB disponibles, VRAM global 0/6141 MiB. No se redujo la guarda de 2 GiB ni se atribuyeron esos valores a picos de inferencia.

Tres instantáneas ambientales al cierre: RAM disponible 4,54 / 4,55 / 4,62 GiB; VRAM global 0 de 6141 MiB en la última. No representan picos de inferencia ni consumo atribuible a LENY. No hay comparación frío/caliente suficiente; se declara no disponible. Los tiempos y contadores por fase se incluyen cuando existen en `leny_spec031_comparison.json`, sin contenidos privados.

## 16. Activación y reversión

`LENY_CONTINUITY_ENABLED` es un interruptor técnico, no un perfil. **Estado operacional final: true**, `LENY_SPEC03_EVALUATION_ENABLED=false`. Se mantienen Gemini habilitado y Qwen predeterminado. C5/C6 fueron opt-in de evaluación; D/F usaron el habitual global, sin perfil enviado ni prefijo de opt-in `031-C`. Registran `enabled=true`, política `rag-v11-context-v1`. El permiso técnico de evaluación experimental está retirado, mientras los tickets privados de captura siguen imponiendo un límite adicional sin conceder acceso. La API de estado informa `quality_evaluation_enabled=false`; nuevas conversaciones SPEC-03 se rechazan. El selector Qwen/Gemini permanece.

Histórico: la revisión automática rechazó el intento inicial de activación por considerar condicional la autorización antes de revisión humana. No se ejecutó aquel comando ni se eludió el rechazo. **El 14/11 el propietario autorizó expresamente continuar y activar/reiniciar, dejando su prueba manual como segunda verificación.** Con esa autorización nueva, la activación sí se ejecutó y se comprobó. `.env` cambió únicamente en las dos banderas indicadas; API Key y demás valores se conservaron. `leny_spec031_pre_activation_*.json` mantiene las evidencias anteriores, incluido el bloqueo, sin presentarlas como el estado final.

Procedimiento **ejecutado**: se verificaron huellas del árbol final y `.env` inicial; memoria, identidad de procesos, lease global, ausencia de trabajos y transacciones activas. El backend encontrado estaba nuevamente en `--reload`, PID de launcher 10396, diferente al registro anterior; se identificó por ejecutable/ruta real. Se aplicaron solo dos banderas con registro privado de valores anteriores y hashes, reversión en memoria ante fallo y reinicio protegido mediante `backend\venv\Scripts\python.exe -B backend/scripts/restart_leny_review_backend.py`. Salud 200, PID 10976. Tras las pruebas y corrección Qwen se repitió el reinicio con las mismas guardas, salud 200, **PID final 25816, sin autoreload**. La guarda de antecedentes no empresariales y la corrección Qwen quedaron cargadas.

El control de Chrome terminó porque el host no estaba disponible y la vía nativa no pudo comprobar la URL. No se eludió esa restricción. El propietario abrió sesión en la consola segura y D/E/F/G utilizaron autenticación normal, NDJSON completo e historial/fuentes por API. Al cierre, `/health` 200, React 200, LENY sin credenciales 401 y Ollama 200. D/F/G tienen 10/10 verificaciones de historial coincidentes y 3/3 fuentes abiertas HTTP 200; no son métricas de fidelidad. El evaluador se cerró sin guardar credenciales.

Reversión operacional de continuidad: cambiar solo `LENY_CONTINUITY_ENABLED=false`, conservar `LENY_SPEC03_EVALUATION_ENABLED=false`, Qwen/Gemini habilitados y Qwen predeterminado; ejecutar el mismo reinicio protegido y comprobar salud. Revierte también la excepción local de redacción porque depende de esa bandera. No borrar historial ni ejecutar downgrade de 0025. El provisional permanece retirado. Los cambios de retirada por API/UI y el ajuste de pertinencia son comunes y no dependen del interruptor: su reversión requiere parche de código, no solo apagarlo.

Respaldo adicional antes del ajuste Qwen: `before-local-drafting/leny_service.py`, manifiesto SHA-256, huella posterior e `inverse-local-drafting.patch` en el checkpoint privado. Permite invertir únicamente esa corrección si el hash del archivo sigue siendo el esperado; revisar el parche y abortar ante cambios ajenos. No restaura el servicio completo desde HEAD.

`before.json` identifica 14 archivos respaldados con SHA-256 en el checkpoint privado inicial. `candidate-snapshot.json` apunta a los archivos finales y `inverse-backed-files.patch`: cubre **solo** esos respaldos iniciales, no todos los archivos nuevos o ampliados posteriormente. Antes de aplicar una inversión, comprobar que cada archivo aún coincide con su hash final, revisar los hunks y aplicar selectivamente; abortar ante cambios ajenos. Scripts/pruebas aditivos figuran en el inventario final y pueden dejarse sin ejecutar. Para cualquier archivo posterior no respaldado, revisar el diff específico de SPEC03.1; nunca restaurarlo completo desde HEAD. No se afirma una reversión automática total. No hay reversión de datos porque no se modificaron datos empresariales; las conversaciones de evaluación permanecen identificables en el historial.

## 17. Límites y aceptación

Corregir contexto no crea documentación inexistente ni demuestra todas las relaciones semánticas. Falta revisión humana de pertinencia, atribución, completitud y fuentes. Los fallos operativos y las abstenciones se conservan por separado; la aceptación integral no se infiere de tests unitarios.

| Criterio | Estado y evidencia |
|---|---|
| Empresa predeterminada e intención informativa | Activo; ubicación → gerente en D respondió con fuentes sin repetir empresa; cuatro historiales coincidentes |
| Seguimiento y consulta de fuentes | C5 completó cuatro respuestas con fuentes; F reconoció contexto pero se abstuvo desde el segundo turno. Adjudicación semántica humana pendiente |
| Cambio de tema | Cadena C3 de seis turnos completada; juicio de pertinencia pendiente |
| Paráfrasis y seguridad | Regresión positiva/negativa, doce casos SQL sintéticos, barrera sensible y operación/SQL/inyección conservados; no verificador semántico universal |
| Compatibilidad Qwen | Generación real E, fallo de manual Z2/E conservado y corrección verificada en G como general; operación sigue bloqueada |
| Estado operativo | Salud original correcta, ambos proveedores habilitados, Qwen predeterminado |
| Presupuestos/modelos/cuotas | Sin cambios: Gemini 3.1 Flash-Lite medium 32678/8192; Qwen 4096/768; cuotas 15/250000/500 |
| Comparación | A y correcciones trazables; B no inmutable; 96 intentos conservados, sin aceptación estadística SPEC-04 |
| Activación habitual corregida | Ejecutada con nueva autorización; banderas reales verificadas y cadenas ordinarias D/F/G completadas |
| Aceptación humana | Pendiente: 20 casos de desarrollo más ocho reservados y apéndice privado |

Veredicto: **corrección integrada y activada en el ERP original; comprobación técnica finalizada; revisión manual humana pendiente como segunda verificación**. No se declara aceptación semántica integral: F conserva abstenciones que necesitan revisar la evidencia y las respuestas completas, sin prometer continuidad perfecta ni cumplimiento estadístico SPEC-04. El propietario puede probar Qwen y Gemini desde LENY. No se han iniciado capacidades SQL/BI/ML/AutoML ni rediseños del RAG.
