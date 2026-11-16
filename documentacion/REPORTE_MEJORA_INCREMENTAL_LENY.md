# Reporte de mejora incremental LENY

## Integración y evaluación en el ERP original — 03/11/2026

**Esta sección reemplaza el estado operacional del reporte histórico conservado debajo.** El propietario autorizó integrar en el original, ajustar las opciones propias, recargar el backend y probar con autenticación normal desde terminal. La versión está en el árbol original; no se hizo merge, migración, reindexación ni instalación. La revisión humana y la aceptación global SPEC-04 siguen pendientes. Tener opciones activas no significa que todos los casos funcionen satisfactoriamente.

### Configuración y recorrido comprobados

API original `127.0.0.1:8000`, frontend habitual `localhost:5173/app/leny`. `rag4_v1`, ranking híbrido y `controlled-synthesis-v1`. Qwen `qwen3.5:4b-q4_K_M`, contexto4096, generación768, temperatura0, residencia0. Embeddings `qwen3-embedding:0.6b`,1024 dimensiones, CPU. Una inferencia simultánea mediante el coordinador PostgreSQL durable. Se conservan cuotas, límites y márgenes de memoria. Veinte candidatos y cinco referencias finales cuentan **fragmentos**, no documentos: encabezado y continuación consumen lugares propios.

Opciones candidatas efectivas: `LENY_RAG_LINKED_SUPPORT=true`, `LENY_RAG_SECTION_CONTEXT=true`, `LENY_RAG_SOURCE_COVERAGE=true`, `LENY_RAG_FOLLOWUP_CONTEXT=false`. Vecinos globales permanecen apagados. La captura privada por turno registra valores realmente cargados y protocolo de síntesis; `general-structured-v1` identifica la ruta general nueva. Los valores predeterminados del código siguen apagados y no describen la configuración activa.

Flujo: JWT/Casbin/propiedad de conversación → controles de seguridad y capacidad → intención empresarial/normalización de erratas → embedding CPU → SQL con ACL y publicación antes de ranking/resolución por título → selección acotada con dependencias estructurales → presupuesto/probes existentes → una síntesis con pasajes identificados → validación de estructura, referencias y afirmaciones acotadas → revalidación de permisos/publicación → persistencia y NDJSON completo → apertura autenticada de cada fuente. Los textos son datos no confiables; el generador no recibe herramientas ni acceso SQL transaccional.

Sin evidencia: se prepara una orientación general o ejemplo en una generación estructurada, sin fuentes documentales, y se añade un aviso explícito de ausencia de respaldo y posible inadecuación. La validación impide presentar esa salida como práctica interna. Si la generación no supera los controles, se reconoce que tampoco pudo elaborarse una orientación fiable. No se atribuye al modelo acceso ilimitado a la biblioteca ni hechos empresariales por su conocimiento general.

El backend se reinició de forma explícita y controlada mientras el coordinador estaba libre. La recarga automática de Uvicorn bajo un proceso Windows oculto no cargó varias revisiones iniciales; se verificó esa discrepancia con trazas. Se dejó el proceso original sin `--reload` para evitar cargar cambios mientras se evalúa. No se detuvo Ollama ni Vite. Las revisiones futuras del backend requieren recarga explícita.

### Causas raíz verificadas

- Encargada: se verificó el original DOCX por SHA y su extracción; el índice tenía45 fragmentos y nueve encabezados de funciones. La recuperación inicial seleccionaba introducción/definición/limpieza, no una visión representativa de funciones. Además, la ruta de asesoramiento permitía una respuesta general pese a disponer de evidencia. No era una ausencia del documento ni prueba de que hubiera que cambiar embeddings.
- Primera prueba: Qwen confundía el momento de acordar/registrar con la fecha relativa en que ocurre la prueba y añadía conflicto. Eran hechos distintos. La cifra presente en otro pasaje tampoco demostraba respaldo del bloque generado.
- Fuente por título: un título válido podía caer en ambigüedad empresarial; al resumir una fuente corta, el selector descartaba su parte final aun estando recuperada. Se corrigió la resolución autorizada y la cobertura acotada de fuentes pequeñas.
- A1+A3: seleccionar cinco cuerpos y luego añadir su encabezado excedía cinco. El esquema ahora reserva espacio para dependencias y verifica que pertenecen al mismo índice. Una secuencia PDF explícita puede requerir la página siguiente: se vincula solo si existe encabezado de procedimiento y numeración consecutiva, con identidad propia.
- Seguimiento: usar el final de la respuesta previa perdía la explicación; añadirla al embedding favorecía repetir. Dos experimentos no demostraron continuidad útil. Se excluyó la pista experimental. La conversación anterior nunca demuestra tareas ejecutadas ni permite recuperar una fuente revocada.
- Respuesta general: el aviso inicial no impedía que el streaming libre inventara después «nuestra empresa». Se sustituyó esa ruta sin evidencia por JSON validado antes de emitirlo. Una solicitud de mutación explícita de inventario/ventas se marca capacidad no disponible.

### Ajuste del validador

Se conservan controles obligatorios: identidad de referencias/pasajes, índice publicado, ACL, salida utilizable/completa, límites y ausencia de herramientas. Se aceptan paráfrasis sin exigir coincidencia literal ni repetición de todos los marcadores del párrafo. El soporte puede combinar encabezado y cuerpo de diferentes fragmentos del mismo índice; cada uno conserva su referencia. No se mezclan índices para prestar cifras.

Las heurísticas no son un certificado de implicación semántica. Si un bloque incluye cantidades, se comprueba solo su soporte explícito. Para impedir el intercambio conocido de cantidades entre materiales, no se publica libremente esa asociación sintetizada: se conserva un bloque breve con datos exactos del soporte, o se remite a la fuente si no cabe. Es un compromiso deliberado: parte de la respuesta cuantitativa puede ser literal, no una síntesis completa. Los ordinales de pasos no se confunden con cantidades empresariales.

Las condiciones dudosas se omiten; no se unen citas arbitrarias de «errores comunes» y «criterios de calidad» para simular una explicación. Se conservan bloques independientes válidos y se marca alcance parcial. Si ninguno sobrevive, hay abstención explícita. No se restaura el fallback silencioso de páginas completas. No se añade NLI, juez Qwen, bucle de reparación ni segundo pase de síntesis. El validador todavía puede aceptar paráfrasis semánticamente defectuosas sin señal detectable y puede abstenerse ante salidas corregibles: requiere revisión humana.

### Resultado por mejora y comparaciones

Los resultados individuales finales, incluidos fallos, están en `evidencias/leny_original_api_summary.json`. Los textos completos y pasajes están exclusivamente en el paquete privado. Se preservaron los trabajos anteriores y los intentos de activación inefectiva; no se eliminan para mejorar porcentajes.

| Variante | Hipótesis / cambio mínimo | Evidencia y correcciones | Estado operacional |
|---|---|---|---|
| B0 original | Medir API normal antes de los cambios |6 turnos, mediana47.6955s. Encargada0 fuentes; vestido3; ambos seguimientos con abstención; primera1; manual0. No es fidelidad humana aprobada | Baseline preservada |
| A1, dependiente de A3 | Encabezado/sujeto con IDs propios; listado de funciones por encabezado del contenido; fronteras de sección |2 turnos iniciales: encargada47.235s/5fragmentos; MODISTA48.953s/sin evidencia atribuible. Corrección posterior reserva lugares del encabezado; SQL sintético comprueba no cruzar a otro cargo incluso desconocido. No se infiere cargo del archivo | Activada, cobertura parcial explícita; aceptación semántica pendiente |
| A2, dependiente de A3 | Resolver título con ACL; fuente corta íntegra si cabe; muestreo acotado de fuente larga incluyendo final | Dos tandas de2casos y corrección de1. La sección final de capacitación pasó de no documentada a respuesta con3referencias; resumen tuvo fallos/truncamiento. No se promete totalidad por cinco fragmentos | Activada; resumen completo sigue sujeto a presupuesto y fidelidad |
| A3 | Un pase JSON, soportes combinables, eliminación de falsos conflictos, rescate de bloques independientes | Tandas3+3 y corrección1; primera prueba llegó a responder con fuentes sin falso conflicto. Pruebas de paráfrasis fiel, cambio de cargo, cifra prestada, cifras intercambiadas y antes/después. La combinación detectó nuevos fallos que se conservan | Activada provisionalmente; no es verificador semántico certificado |
| A4 | Pista acotada revocable para «¿Y después?» sin ancla literal | Dos experimentos de3turnos. Primero tuvo1abstención y repetición; segundo contestó, pero repitió los pasos. Que `answered` sea verdadero no cumple continuidad | Excluida: flagfalse; problema funcional pendiente |
| A5 | Sumas de llamadas/tokens, causa y alcance visible | Pruebas de acumulación y fallo sin reutilizar contadores anteriores; embedding sin contador se declara incompleto.41 pruebas frontend de chat/fuentes/transporte, incluyendo alcance tras recuperar historial | Conservada por beneficio objetivo de diagnóstico/UI |
| Combinación original | A1+A2+A3+A5 con A4 experimental apagada | `FINAL-effective-01`:18intentos, incluye error de selección, abstenciones y respuestas generales defectuosas. `FINAL-effective-02`: repetición completa tras correcciones; consultar tabla generada al cierre | Integrada para revisión; no afirmar aceptación integral |

No son experimentos estadísticos puros B0+Ai: A1/A2 requieren el contrato A3; entre tandas se corrigieron interacciones, prompts y fallos demostrados. Las comparaciones son de ingeniería sobre casos identificados. Las18preguntas de la combinación ya se utilizaron para diagnosticar fallos y no constituyen holdout no visto. La batería reservada completa de SPEC-04 no se abrió para optimizar ni se ejecutó como aceptación final.

### Pruebas y recursos

Ejecutadas desde terminal con intérprete/paquetes existentes:

- 491 pruebas backend seleccionadas aprobadas: transporte/seguridad, routing, retrieval, selección, síntesis, fuentes, packing, seguimiento y pruebas originales nuevas. JUnit: `evidencias/leny_original_backend_tests.xml`.
- 16 pruebas de runtime con límites de procesos/HTTP simulados aprobadas; no arrancan servicios reales. Una primera ejecución tuvo8fallos porque el entorno imponía `LENY_RUNTIME_AUTOSTART=false` a pruebas cuyo escenario exige true. Se conservó ese resultado; se repitió únicamente con su configuración simulada correcta. No se corrigió código productivo para obtener verde.
- 108 pruebas PostgreSQL aisladas aprobadas,5deseleccionadas. Manifiesto/marcador/data_directory/revisión0021 comprobados; sin DDL, migración ni modelo. Contratos: `leny_original_integration_contracts_operational.json`. Un intento de sobrescribir un checkpoint sin su archivo compañero fue rechazado correctamente y se utilizó un nombre nuevo.
- 41 pruebas frontend aprobadas, lint de los tres archivos afectados y build en directorio temporal nuevo correctos. Vite advierte bundle grande; no se amplió esta tarea para dividirlo. Las tres primeras pruebas nuevas de alcance revelaron que la reconciliación borraba la etiqueta; se corrigió y repitió.
- API normal: login y refresh con credenciales introducidas por el propietario; token solo en memoria. Conversación nueva por caso independiente; mismo ID para seguimientos. Se consume todo NDJSON hasta terminal y se comprueba cada fuente con GET autenticado. Se guardan errores, cancelaciones/timeout y respuestas vacías, no solo HTTP200. No se fabricaron JWT.

Comandos reproducibles: `python -B -m pytest` con `DATABASE_URL` de puerto1 para unitarias y `--basetemp` nuevo; las pruebas de runtime son simuladas y se ejecutan aparte. `run_leny_rag_quality.ps1 -Profile rag4_v1 -ResponseMode controlled-synthesis-v1 -Mode contracts -Output <archivo-nuevo>` verifica aislamiento antes de fixtures. Frontend: `pnpm.cmd exec vitest run ... --no-cache --configLoader runner --environment jsdom`, `pnpm.cmd exec eslint <archivos>` y `pnpm.cmd exec vite build --outDir <temporal-nuevo>`.

Prueba real: `run_leny_authenticated_review.py --watch`, seguido de `--enqueue <identificador-nuevo>` desde otra terminal; `monitor_leny_review.py <identificador> --expected <N>`. No repetir automáticamente intentos fallidos ni usar nombres existentes. El watcher dura una hora entre trabajos; al expirar exige autenticación normal nueva. `set_leny_review_variant.py combined` recarga solo el backend original identificado mientras LENY/worker están libres. No ejecutar variantes durante un trabajo.

El exportador registra N, tiempos individuales, mediana/rango, llamadas/tokens y tiempos por fase. Un contador ausente significa total incompleto, no cero. Hay sondeos y selección además de la generación: no se afirma «una llamada total». RAM/VRAM y CPU muestreadas son globales; la residencia declarada por Ollama no equivale a memoria atribuible de todos los procesos. Los lotes anteriores muestran hasta3743MiB globales y2995MiB de residencia del modelo según Ollama. No se mide velocidad general ni p95: cada condición tiene menos de30muestras comparables. Residencia0 implica recargas frecuentes; no es comparación frío/caliente controlada.

No se calcularon Hit/Recall/MRR, fidelidad ni completitud humana sin gold empresarial adjudicado. No se acreditan objetivos SPEC-04: activación≥95%, falsos rechazos≤5%, Hit@5≥90%, Recall@5macro≥85%, fidelidad≥90%, referencias≥95%, ausencia de evidencia≥95%. Una cita válida solo prueba identidad/acceso. Seguridad de ACL/revocación/inyección se cubre con contratos y escenarios sintéticos; la cuenta real utilizada no demuestra todos los roles reales.

### Archivos, evidencia y reversión

Archivos funcionales propios: `core/config.py`; servicios `leny_capabilities`, `leny_service`, `leny_rag_retrieval`, `leny_rag_selection`, `leny_rag_synthesis`, `leny_store`, `leny_inference_state`, `leny_rag_diagnostics`; `schemas/leny.py`; `useLenyChat.js`, `LenyPage.jsx` y pruebas. `leny_review_capture.py` solo captura con ticket privado ligado al actor/conversación/hash de pregunta y antigüedad; no concede acceso. La captura normal no registra texto privado en logs. Se preservaron cambios ajenos en otros archivos LENY.

Scripts de sesión, monitor, activación, reinicio y exportación están en `backend/scripts/`; tests nuevos en `test_leny_original_integration.py` e `integration/test_leny_original_features.py`. No hay nuevas tablas/dependencias/modelos. El snapshot real combina HEAD y manifiesto SHA de archivos, porque HEAD solo no reproduce el árbol modificado.

Paquete protegido: `%LOCALAPPDATA%/BAB_VDOS/leny-original-integration`. Contiene respaldos iniciales `backups/20261103-112707`, manifiesto del código candidato, parches propios, resultados por trabajo, trazas por petición, muestras de recursos y `REVISION_HUMANA.md`. No subir este paquete ni `.env`. El informe público contiene solo identificadores de caso, códigos, contadores, configuración técnica y tiempos. No se copió código de Open Notebook ni se añadieron dependencias de referencia.

Reversión operacional mínima: ejecutar `python -B backend/scripts/set_leny_review_variant.py B0` desde raíz con el venv, cuando no haya solicitudes/trabajos activos. Apaga las cuatro opciones y reinicia el backend identificado; no modifica datos. Mantiene los ajustes de routing/capacidad y diagnóstico: **no equivale a restaurar todo el código anterior**.

Reversión completa propia: proteger cambios posteriores; comprobar primero `git apply --reverse --check --ignore-space-change <paquete>/own-backend-changes.patch` y el equivalente `own-frontend-changes.patch`; ambos se comprobaron en seco. Aplicarlos con `--reverse --ignore-space-change` solo si la comprobación sigue pasando. Preservar los scripts para recargar; después restaurar exclusivamente las claves de configuración propias desde el respaldo privado y reiniciar de forma controlada. No copiar `.env` entero sobre modificaciones posteriores ni restaurar archivos completos antiguos, no usar reset/clean. Los parches se basan en el árbol local respaldado y el snapshot frontend B0 conservado, no en HEAD. No hay rollback de migración.

### Revisión del propietario y límites

Abrir una conversación nueva en el ERP y comparar los casos de la tabla final con `REVISION_HUMANA.md`. Para cada respuesta revisar pregunta, respuesta completa, pasajes, citas, atribución de cargo/cifra/condición y alcance. La rúbrica queda vacía hasta que el propietario la complete. Los consejos generales se evalúan aparte de las respuestas documentales y no cuentan como éxito de recuperación.

Pendientes conocidos: continuidad útil sin repetición; abstenciones de síntesis/selección; omisión de condiciones o cantidades que obliga a consultar fuentes; cobertura limitada de documentos extensos; riesgo semántico no detectable por heurísticas. No se deben presentar funciones de otro cargo para llenar un vacío documental. La versión activa es revisable y reversible, pero el objetivo conversacional completo no queda certificado con estos resultados.

En la combinación se observaron también afirmaciones generales no justificadas de inexistencia de manual y una interpretación adicional de las condiciones de inventario. La primera se añadió a los controles de la ruta general; la segunda queda señalada para adjudicación humana, sin certificar respaldo por una cita válida. La selección de medidas de can-can tuvo un falso negativo aun con candidatos disponibles; no se atribuye a embeddings ni se declara resuelto. No se acredita cero errores factuales críticos ni aceptación de la variante semántica.

La corrección final de la ruta general permite bloques acotados de hasta3000caracteres (documentales conservan900), distingue etiquetas «Ejemplo1» de importes y normaliza saltos de línea escapados. La misma salida real de ayuda para iniciar manual pasó en replay sin inferencia nueva; la prueba de API posterior se identifica por separado. La ampliación es de validación textual de salida, no de contexto4096, salida768 o memoria. No equivale a demostrar mayor utilidad: esa respuesta puede seguir siendo extensa.

`GENERAL-correction-03` conserva tres intentos posteriores: manual se abstuvo por confundir versión/numeración de una plantilla con cifras internas; unidades se abstuvo al detectar una afirmación no respaldada de inexistencia de manual; operación fue rechazada. La corrección de plantilla transforma su versión numérica en campo por definir y reconoce `Paso1:` como ordinal, sin permitir importes/medidas arbitrarios. `GENERAL-template-04` identifica la comprobación real posterior; no se mezcla con las18muestras anteriores para mejorar artificialmente su tasa.

### Cierre medido de la combinación

| Checkpoint | N | Resultado de transporte/política | Alcance emitido | Latencia descriptiva | Recursos globales |
|---|---:|---|---|---|---|
| FINAL-effective-01 |18|13answered,3clarification,1refused,1error|4documentadas,3parciales,6generales;5sin etiqueta|Mediana30.6955s|RAM libre3.173–5.994GiB; VRAM0–3743MiB|
| FINAL-effective-02 |18|10answered,6clarification,2refused|1documentada,5parciales,4generales;8sin etiqueta|Mediana25.7345s|RAM libre4.563–6.364GiB; VRAM0–3743MiB|

El segundo lote redujo respuestas generales sin validar, pero aumentó abstenciones: **no se declara mejora global de calidad ni cumplimiento del objetivo completo**. Encargada respondió con4fragmentos y alcance parcial; primera prueba con1; can-can con1 y omisión de cantidades; título de ayuda para iniciar manual se abstuvo; resumen de fuente respondió parcialmente; medidas cayó a orientación general indebida antes del último control; seguimiento no cumplió continuidad. Operación ERP e inyección fueron rechazadas en el segundo lote. La cuenta real abrió las referencias emitidas por los mecanismos normales; el denominador preciso por turno figura en la evidencia estructurada.

**Cierre operacional comprobado:**72turnos normales de API en15checkpoints, incluidos baseline, intentos negativos, dos lotes completos y correcciones identificadas. `GENERAL-template-04` terminó `answered`, alcance `general`,0fuentes,36.203s: orientación y plantilla con aviso y campos por definir. `GENERAL-correction-03` dejó registrado el rechazo de la operación ERP y la abstención de unidades. No se reescribieron sus resultados con el intento posterior.

Estado al cierre: API y frontend respondieron200; backend original PID29796, sin recarga automática. Las huellas de documentos, versiones, ACL documentales/carpetas, indexaciones, fragmentos, embeddings y roles no cambiaron entre las capturas de solo lectura antes/después de la evaluación final. Esto no es una auditoría completa de todas las tablas comerciales ni una garantía ante cambios concurrentes posteriores. Se verificaron Python3.10.6 y los dos modelos/digests existentes, sin descargas. La sesión local de credenciales de evaluación se cerró al acabar; los servicios del ERP continúan disponibles.

La configuración actual es una candidata operativa provisional para la revisión solicitada. Persisten fallos reales de respuesta y no se presenta como aceptación funcional completa. La reversión de los parches propios se comprobó en seco contra el árbol final con `--ignore-space-change`; no se ejecutó. El manifiesto del código y las trazas permiten distinguir la combinación completa del pequeño ajuste posterior exclusivamente de la ruta general.

Tablas legibles: [casos antes/después](evidencias/leny_original_api_cases.md) y [llamadas, tokens y recursos por checkpoint](evidencias/leny_original_api_costs.md). Los tokens son sumas disponibles; faltan los contadores que el proveedor no devuelve. Los resultados de correcciones posteriores se informan separadamente. El archivo privado `REVISION_HUMANA.md` ofrece pares A/B de los seis casos comunes y luego todas las respuestas/fuentes para revisión.

---

## Reporte histórico de la copia experimental (estado anterior)

Fecha: 03/11/2026. **Candidata parcial de ingeniería; aceptación funcional pendiente.**
## Alcance y estado
Trabajo en rama codex/leny-incremental-20261103, worktree C:/Users/MARCELO/AppData/Local/Temp/BAB_LENY_INCREMENTAL_20261103.
No se activó ni recargó el ERP habitual. No se modificaron sus documentos, publicaciones, ACL, datos comerciales ni configuración. Por autorización expresa posterior se usó su bloqueo/estado técnico de inferencia para excluir solicitudes simultáneas a Ollama. No se creó JWT ni se suplantó sesión de navegador.
El encargo integral **no está cerrado**: falta línea base empresarial completa de encargada, flujo E2E con identidad normal aislada, comparaciones de A1/A2/A4 con recuperación y modelo reales, medición VRAM y revisión humana. Estos pendientes no se presentan como aprobados.
## Snapshot y aislamiento
HEAD original5a1d15a04c2f97483769c86e82dbba056adce6b8 más28 archivos modificados/nuevos copiados sin .env, venv ni originales. Huellas en evidencias/leny_incremental_snapshot.json.
B0 código app/tests/frontend archivado localmente en evidencias/leny_incremental_B0_code.zip, SHA256 f7aa160794ef9abc7011ccc32e371ecdefc163f710fe847893106534acdbb4c6.
Prototipos completos conservados en leny_incremental_experiments_code.zip. No subir paquetes privados o originales al remoto.
Configuración de evaluación:4096/768/temp0, modelos actuales, una inferencia y evidencia sintética. Los flags nuevos permanecen false por defecto.
PostgreSQL aislado existente validado por manifiesto/marcador SQL/data_directory/revisión0021. No se ejecutaron migraciones. El wrapper inicia/detiene solo ese clúster cuando lo posee. TestClient y fixtures se revisaron; los contratos no requieren iniciar Uvicorn.
## Protocolo y resultados por variante
|Variante|Hipótesis/cambio|Casos y resultado|Coste|Decisión|
|---|---|---|---|---|
|B0|Flujo actual y contrato de síntesis|207 regresiones iniciales aprobadas.106 integración aislada.3 generaciones con evidencia fija aceptadas por validador;2 incluyeron advertencia injustificada de conflicto|15.282/9.312/8.719s; entrada1228/salida319 tokens agregados de generaciones finales|Baseline parcial; no E2E ni gold empresarial|
|A1|Añadir encabezado/condición por sección verificable y conservar ID propio|5 pruebas nuevas aprobadas. Paquete exige misma sección o heading DOCX inmediatamente anterior. Dependencia de heading consume slot. Se detectó incompatibilidad: un bloque puede necesitar soporte de encabezado y cuerpo en fuentes diferentes, que el contrato actual no expresa bien|Sin inferencias nuevas de esta variante|Prototipo excluido de candidata; evidencia archivada. No se declara mejora de recuperación real|
|A2|Advertir cobertura parcial al resumir título explícito si faltan fragmentos|3 pruebas comparativas aprobadas: B0 omite aviso; variante lo muestra; fuente corta completa no se etiqueta parcial. Reutiliza título autorizado|Sin llamada extra; no se midió E2E|Conservada como opción experimental apagada; no es implementación completa de Source Chat/secciones|
|A3a|Cifras solo en soportes expresamente indicados|5 pruebas: rechaza cifra prestada del pasaje no citado; acepta combinación válida y numeración. Si ambos pasajes se citan, cifras intercambiadas aún pasan. Replay de3 salidas reales aceptó3/3 en ambos modos|Replay sin generación adicional|No aceptada como verificador semántico; opción apagada|
|A3b|Restringir limitation según veredicto de selección|5 pruebas de contrato aprobadas; repetición con mismo Qwen/evidencia:3/3 aceptadas; conflicto injustificado2/3→0/3. En2 casos cambió a missing_details, cuya pertinencia sigue por revisar|10.579/7.391/6.172s; entrada1228/salida315; una generación/caso|Beneficio objetivo acotado; opción reversible, semántica pendiente|
|A4|Progreso derivado de puntos completos exactos, nunca de cita sola|4 pruebas aprobadas. Rechaza progreso por keywords/paráfrasis/cita global/numeración duplicada; solo registra punto completo literal. Esto resulta insuficiente para síntesis con palabras propias|Sin inferencias|Prototipo excluido; no reinstalar un requisito literal para seguimiento|
|A5|Acumular todas las llamadas/tokens y clasificar causa sin texto privado|3 pruebas de agregación/categorías; ejemplo4 llamadas+embedding=5,140entrada/398salida y1 llamada sin contador;2 sondas reales confirman contador por llamada. Mantiene contadores anteriores como última generación|CPU despreciable; sin LLM extra|Conservada por beneficio objetivo de trazabilidad; no se atribuye mejora semántica|
|Combinación candidata|Instrumentación A5 + opciones A2/A3 apagadas por defecto|316 pruebas seleccionadas aprobadas;38 frontend aprobadas. Integración final en ejecución al preparar este reporte; resultado se añade al terminar|N pequeño, sin p95|Candidata parcial; no activar|
Los5 tests deA1 y4 deA4 se ejecutaron antes de retirarlos: quedaron en archivo experimental y tests fuera del descubrimiento ordinario. No se borró trabajo del propietario: se restauraron esos archivos desde B0 del árbol local, no desde HEAD.
## Evidencia y límites
- evidencias/leny_incremental_B0_contracts_paths_fixed.json:106passed,0failed,5deselected; sinDDL/migraciones/modelos. Un intento inicial falló por temporales, conservado en B0_contracts.json.
- evidencias/leny_incremental_unit.xml:320passed durante prototipos; luego5 tests deA3b añadidos y9 deA1/A4 retirados del conjunto candidato.
- evidencias/leny_incremental_candidate_unit.xml:316passed.
- Frontend:21LenyPage+9LenySources+8transporte=38passed; no cambios de UI cosméticos.
- evidencias/leny_incremental_comparison.json: métricas permitidas de6 inferencias, modelos/digests y limitaciones.
- Paquete de texto sintético completo: %LOCALAPPDATA%/BAB_VDOS/leny-incremental-evaluation/fixed-evidence/{b0-a3-fixed-01,a3-limitations-01}.json. No contiene documentos empresariales.
Las3 consultas por condición tienen la misma evidencia/pregunta/modelo; no constituyen30muestras comparables. Medianas9.312 y7.391s descriptivas: no demostrar aceleración ni p95. RAM disponible es global y son lecturas antes/después, no pico atribuible. No se midió VRAM en esta ronda.
Un intento deA3b se detuvo antes de inferir por RAM<2GiB; el reintento autorizado respetó el mismo margen. No se aumentaron límites.
El archivo privado contiene mensajes/raw/pasajes para revisión. No se completó rúbrica humana ni se usó Qwen como juez. Pasar JSON/validador no certifica fidelidad.
## Ejemplos compartibles sintéticos
Encargada: B0 resume correctamente las funciones del ejemplo, pero agrega «Las fuentes presentan diferencias». A3b conserva el resumen y elimina esa falsa declaración; agrega falta de detalles, pendiente de valorar. Esto no diagnostica todavía el documento empresarial real de encargada.
Materiales:3metros de tul/2metros de satén se conservaron en ambas generaciones. Prueba negativa: soporte citado solo para tul5metros, afirmación tul8metros tomada de otro pasaje; B0 la acepta yA3a la rechaza. Si cita ambos pasajes, la asociación errónea sigue siendo límite conocido.
Condición: ambas generaciones preservaron aprobación de medidas y nueva revisión si cambian; soloA3b eliminó advertencia de conflicto sin respaldo.
## Cambios revisables
Configuración: leny_rag_source_coverage, leny_rag_explicit_support y leny_rag_verdict_limitations false por defecto.
Síntesis: alternativa de soporte explícito, exclusión de ordinal inicial del conteo de cantidades, esquema de alcance condicionado y validación backend.
Servicio: aviso parcial opcional por título/resumen, contadores agregados al cierre y código seguro de fallo.
ManagedProvider: acumula llamadas/entrada/salida sin copiar texto ni parámetros arbitrarios; embeddings sin contador de tokens se identifican como incompletos, nunca toman tokens de generación anterior.
No se conserva sección/cursor nuevo en el flujo activo. No se añadieron tablas, dependencias ni índices.
## Comandos ejecutados
Desde copia, con intérprete C:/laragon/www/bellaarte-program/backend/venv/Scripts/python.exe:
- ENVIRONMENT=test, LENY_RUNTIME_AUTOSTART=false y DATABASE_URL con puerto1 no operativo para unitarias. PYTHONPATH apunta al backend de copia.
- python -B -m pytest sobre archivos v11/retrieval/followup;207passed.
- pytest sobre variantes+regresión seleccionada;217,219 y320passed en checkpoints.
- pytest final sobre incrementales metrics/support/coverage y regresión seleccionada, --basetemp nuevo --junitxml=documentacion/evidencias/leny_incremental_candidate_unit.xml;316passed.
- run_leny_rag_quality.ps1 -Profile rag4_v1 -ResponseMode controlled-synthesis-v1 -Mode contracts -Output ...B0_contracts_paths_fixed.json;106passed.
- node Vitest existente run LenyPage/LenySources/lenyTransport --root copia/frontend --no-cache --configLoader runner --environment jsdom;38passed. Dependencias existentes enlazadas por junction; no instaladas.
- run_leny_incremental_fixed.py --run-id b0-a3-fixed-01 --limit3.
- run_leny_incremental_fixed.py --run-id a3-limitations-01 --limit3 --verdict-limitations.
Invocaciones elevadas usaron Set-Location explícito porque el transporte de aprobación no conserva cwd. Errores de permisos de sandbox no se contabilizan como fallos semánticos.
## Ejecución aislada y reversión
No ejecutar run_leny_v11_backend_review.py ni verify_leny_v11_production.py: son scripts históricos contra el entorno habitual y no se usaron en este encargo.
Para unitarias: reutilizar comando/env anteriores con --basetemp inexistente propio. Para contratos: usar wrapper de esta copia que verifica manifiesto; nunca provisionar/migrar por comodidad. Para sondas: run-id nuevo, verificar margenRAM y compartircoordinación autorizada. El guard SQL del runner solo permite consultas de bloqueo/estado y UPDATE leny.inferencia_estado; no autoriza consultas empresariales.
Reversión operacional de opciones, cuando se apruebe activación: LENY_RAG_SOURCE_COVERAGE=false, LENY_RAG_EXPLICIT_SUPPORT=false, LENY_RAG_VERDICT_LIMITATIONS=false y recarga posterior autorizada. Actualmente no hay nada activado que revertir.
Reversión de código de esta candidata: conservar overlay y aplicar parche inverso solo a cambios propios frente al B0 archivado. Nunca reset/clean del repositorio habitual. No rollback de migración porque no huboDDL.
## Puertas pendientes y siguiente trabajo
1. Copia privada de documentos/actor empresarial autorizado e identidad normal aislada; diagnóstico completo de encargada antes de atribuir fallo a recuperación.
2. E2E del servicio con query embeddings CPU, recuperación SQL y Qwen, fuentes e historial; las pruebas con mocks y generación fija no lo sustituyen.
3. A1 entre fragmentos de encabezado/cuerpo necesita contrato explícito seguro; no atribuir cargo por archivo.
4. A2 necesita selección/cobertura real de secciones y casos al final de documento; el aviso parcial solo cumple una propiedad limitada.
5. A3 requiere pruebas de asociación entidad/cifra/condición y evaluación reservada, con cero errores críticos antes de aceptación.
6. A4 requiere progreso demostrable para paráfrasis sin exigir literalidad; no hay mejora aceptada.
7. Revisión humana A/B, consumoVRAM y bateríaSPEC04 completa/no vista. No declarar cumplidos sus porcentajes conN3.
La candidata se entrega para inspección técnica incremental. **No satisface todavía todas las puertas del encargo ni autoriza merge/despliegue/activación.**


## Continuaci?n pendiente de identidad
Se consult? al propietario qu? cuenta normal copiar al entorno aislado. Hasta recibir ese identificador/confirmaci?n no se ejecutar? un E2E empresarial con identidad inventada. El resto de resultados anteriores conserva sus l?mites.
