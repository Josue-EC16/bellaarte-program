# LENY RAG V1.1 — Implementación y aceptación pendiente

Fecha: 02/11/2026. Estado: **ACTIVATED — variante habilitada en el ERP real; prueba funcional e inferencia/revisión humana pendientes**.

El propietario autorizó implementar el plan mediante «APLICA EL PLAN». Esta entrega modifica código en el mismo proyecto. No activa el modo nuevo en el entorno habitual, no inicia servicios, no consulta documentos privados y no modifica BD, roles, publicaciones, originales o índices. No introduce modelos, dependencias ni migraciones.

## Diagnóstico contrastado

- `leny_policy.py` y `leny_rag_routing.py`: la clasificación original reduce finalidad a business/documents. La palabra manual activa RAG aunque el objetivo sea redactar un ejemplo. La revisión contextual puede emitir aclaraciones genéricas. V1.1 conserva los controles originales y añade intención separada tras ellos.
- `leny_rag_retrieval.py`: SQL filtra ACL/publicación antes del ranking. El título se retornaba pero no participaba en búsquedas. RRF y vecinos ±1 ya existían; no se atribuye a embeddings un error de selección posterior.
- `leny_rag_selection.py`: el límite inicial de tres documentos puede excluir el correcto; el revisor no recibía título/localizador. JSON válido no demuestra pertinencia. Los fallos históricos inventario→tarifa y especialidad→procedimiento general continúan siendo puertas bloqueantes de aceptación real.
- `leny_service.py` expandía determinadas preguntas procedimentales a todos los fragmentos del documento. `leny_rag_grounding.py` construye extractos literales; incluso el resumen agrupa sin parafrasear. React muestra ese texto, no causa su literalidad.
- La fragmentación conserva unidades/localizadores/offsets NFC; no garantiza encabezados heredados en cada párrafo. V1.1 aprovecha estructura existente en lectura. Corregir una versión requiere autorización separada.
- Publicado no significa norma empresarial aprobada. Sin señal explícita no se inventa aprobación, vigencia editorial o especialidad.

## Flujo y archivos

Seguridad/autenticación → intención → capacidad habilitada → búsqueda SQL autorizada por título/contenido → selección → veto conservador de ámbito → empaquetado → síntesis completa en memoria → validación → revalidación → fuentes persistidas y emisión NDJSON.

| Subsistema | Implementación |
|---|---|
| Intención/capacidades | `backend/app/services/leny_capabilities.py`: documental, asesoramiento, redacción, mixta y respuestas de seguridad/indisponibilidad/ambigüedad compatibles con `PolicyDecision`. Registro cerrado de capacidades; SQL transaccional, BI, ML y AutoML deshabilitados, sin ejecutores. Las operaciones de cláusulas posteriores tampoco se autorizan por una primera petición de redacción. |
| Títulos/selección | `leny_rag_retrieval.py`, `leny_rag_selection.py`: coincidencia normalizada exacta y parcial dentro de ELIGIBLE, sin sustitución silenciosa; ambigüedad solicita precisión. Pool de hasta20, metadatos como datos no confiables, vecinos con fronteras fiables. Veto parcial de inventario/cargo/material explícito antes de extracción o síntesis. |
| Síntesis | `leny_rag_synthesis.py`: contrato JSON interno de bloques documentados/general/ejemplo, fuente y soporte literal; generación hasta768, contexto4096, temperatura0. Validación previa a cualquier delta documental. Conserva representación de soporte y citas emitidas por backend. |
| Coordinación | `leny_service.py`, `leny_ollama.py`, `leny_inference_state.py`: misma exclusión durable y fase generation, plazos, cancelación, memoria y revalidación. Versión de política independiente para evitar reutilizar anclajes antiguos. |
| Fuentes | `leny_rag_sources.py`: persistencia opcional de referencias efectivamente citadas, sin renumerarlas; valida autorización de toda la selección. Historial y consulta de fuentes conservan controles actuales. |
| Presentación | Texto Markdown persistente distingue documentación, orientación y ejemplo. `LenyPage.jsx` muestra preparación/verificación; `LenyMarkdown` conserva protección de HTML/enlaces. No cambia la API pública. |
| Evaluación | Runner Python/PowerShell acepta response-mode, identifica síntesis vs extracción y registra generación efectivamente invocada incluso si termina en fallback. No completa rúbricas humanas. |

## Reversibilidad y límites

`LENY_RAG_RESPONSE_MODE=document-excerpts-v2` sigue siendo el predeterminado y conserva el camino anterior. La variante requiere también `LENY_RAG_PROFILE=rag4_v1`. Para probarla en un proceso de evaluación aislado se utiliza `controlled-synthesis-v1`; no se cambió `backend/.env`.

La consulta documental sin evidencia se abstiene. Una petición mixta de redacción puede continuar con orientación explícitamente general sin textos antiguos; un seguimiento documental revocado no se reconstruye con memoria del asistente. Un fallo operativo conserva su error, sin reintentar ni fabricar éxito.

JSON inválido, truncamiento o presupuesto insuficiente producen alternativa extractiva solo después de la selección y el veto de ámbito. El contador `synthesis_fallback` distingue esta salida de `synthesis_validated`; el primero puede producirse sin invocar generación si el prompt no cabe. Errores de seguridad/proveedor/revocación no utilizan ese fallback.

La síntesis contabiliza conservadoramente bytes UTF-8 de su prompt real **y esquema**, reserva768+256 y no reutiliza sondeos de otro prompt. Es deliberadamente conservadora: puede volver a extracción con documentos largos. Antes de ampliar límites se medirán la tasa y causa de fallback, tokens, RAM, VRAM y latencia reales. La alternativa mínima ya disponible es extracción pertinente o acotar la sección.

El contrato verifica identidades, soporte literal, cifras y unidades/monedas presentes, marcadores explícitos de condición y actores. **No prueba entailment, completitud universal ni resistencia integral a inyección.** La posición y significado de una negación pueden seguir siendo erróneos. Las reglas de ámbito pueden abstenerse incorrectamente cuando falta un encabezado heredado. No se declara resuelta la calidad histórica por estas barreras.

Se conservan modelo/digest de embeddings, query policy, dimensión1024, CPU, RRF, límites20/5, RAM2/1GiB y cuota/concurrencia. Umbrales numéricos de similitud y MMR quedan pospuestos; no hay evidencia medida que justifique activarlos. No se instala NLI ni un segundo juez; Qwen no valida su propia aceptación.

## Validación y comparación pendiente

Verificación ejecutada: **461 pruebas backend aprobadas** en la selección de contratos V1.1, seguridad, fuentes, selección, empaquetado, seguimiento y runner. **38 pruebas frontend distintas aprobadas** (21 página,9 fuentes,8 transporte); ESLint de los dos archivos React modificados aprobado. `git diff --check` sin errores. No es la suite total del ERP.

Hubo cuatro errores iniciales al crear temporales de pytest por permisos/ruta; se resolvieron usando un directorio temporal propio dentro del workspace. Vitest requirió ejecución aprobada fuera del sandbox para leer dependencias instaladas; no se instalaron paquetes. Los resultados finales anteriores corresponden a las ejecuciones corregidas.

Pruebas automáticas con datos sintéticos/dobles controlados: enrutamiento de las seis preguntas solicitadas, redacción sin RAG obligatorio, contexto acotado, prioridad de seguridad, títulos autorizados/ocultos, cuarto documento, vecinos, cargo distinto, especialidad/material ausente, formato/citas/soportes, cifras/unidades, generación incompleta, fallback, revocación antes de emitir, fase durable generation y límites HTTP4096/768. Las pruebas del modo extractivo se conservan.

La comparación real usa dos salidas nuevas del runner existente con igual corpus/configuración y distinto `-ResponseMode`. El launcher exige manifiesto PG55432 y una ventana exclusiva autorizada; puede iniciar exclusivamente su clúster aislado. No se ejecutó este launcher porque esta entrega no presupone autorización de la ventana de inferencia sobre Ollama habitual ni acceso a credenciales privadas.

Antes de activación:

1. Ejecutar integración SQL en PG55432 y comparación pareada de ambos modos con los mismos documentos sintéticos; congelar código/corpus. El parámetro Python es `--response-mode`; PowerShell, `-ResponseMode`.
2. Incorporar las seis preguntas exactas y paráfrasis a la revisión focalizada, sin presentarlas como holdout. Utilizar documentos empresariales solo cuando el propietario identifique y autorice sus versiones; originales/ACL/publicaciones no se alteran para probar.
3. Presentar A/B legible con pregunta, ruta, SQL/selección, respuesta, pasajes/localizadores, elementos esenciales, omisiones, citas y valoración humana pendiente. Texto empresarial solo en paquete privado.
4. Evaluar por separado enrutamiento, recuperación, respuesta directa, fidelidad, completitud, citas, utilidad, latencia y memoria. No contar JSON válido o literalidad como fidelidad semántica.
5. Mantener umbrales SPEC04: RAG≥95%, falsos rechazos≤5%, Hit@5≥90%, Recall@5≥85%, fidelidad≥90%, referencias≥95%, abstención≥95%. Cero críticos individuales, incluyendo los dos históricos. Procedimientos completos: todos sus elementos esenciales. p95 solo con≥30 muestras comparables, errores incluidos y frío/caliente separados.
6. Revisar humanamente antes de aceptación. No activar si un promedio oculta fuga ACL, cargo/cifra/regla inventados, cita tangencial o condición esencial omitida.

Reversión: volver a `document-excerpts-v2` en el proceso autorizado y recargar únicamente el backend autorizado. No requiere restauración de BD ni reindexación. La generación libre no dispone de herramientas, SQL, acceso directo a tablas ni facultad de modificar el ERP.

## Activación real para revisión manual (02/11/2026)

Autorización posterior del propietario: integrar y probar directamente en producción, usar Qwen real y medir recursos; el propietario realizará la revisión humana. Después de los bloqueos del conector de Chrome, el propietario eligió ejecutar las preguntas personalmente.

Se activó `LENY_RAG_RESPONSE_MODE=controlled-synthesis-v1` conservando los demás ajustes efectivos. Se guardó copia privada íntegra de la configuración anterior, con huellas de integridad y permisos Windows restringidos, fuera del directorio web. Se solicitó la recarga del supervisor Uvicorn existente; salud HTTP200 verificada. PostgreSQL conserva revisión0021, inferencia idle y cero trabajos pendientes/en curso en esa comprobación.

Se verificó igualdad antes/después de huellas y cantidades de documentos, versiones, ACL documentales/carpetas, indexaciones, fragmentos, embeddings y roles. No se ejecutó migración, no se modificaron publicaciones ni se recontextualizó. Esta comprobación de integridad no sustituye una prueba de recuperación documental con Qwen.

Se inició monitor local acotado a30min de RAM disponible, CPU del sistema, memoria/uso GPU y metadatos numéricos de modelos residentes. Son muestras globales del equipo, no consumo exclusivo atribuible a LENY. No captura preguntas, respuestas, títulos, contraseñas ni tokens. Las muestras permanecen en almacenamiento privado. No se publican percentiles ni se declara aceptada la calidad antes de la prueba manual.

El helper nuevo `backend/scripts/verify_leny_v11_production.py` ofrece `snapshot`, `activate`, `rollback` y `monitor`; `review` solo usa autenticación normal si el propietario proporciona una credencial local protegida, nunca crea JWT. En esta activación no se usó ese camino autenticado ni se creó una credencial. El bloqueo del navegador no se eludió.

## Revisión del propietario y correcciones posteriores (02/11/2026)

**NO ACEPTADO funcionalmente.** El propietario comprobó respuestas poco interpretadas, repetición de «¿Y después?» y abstención de MODISTA. Su ajuste de requisito es priorizar búsqueda documental en toda consulta empresarial válida; sin evidencia útil, ofrecer orientación general identificada y sin atribución interna. La seguridad y las capacidades no disponibles siguen prevaleciendo.

Diagnóstico en la base real, solo lectura: las cuatro respuestas documentales registradas eran extractivas. Tres reconstrucciones del prompt original superaban el presupuesto conservador en bytes, lo que evitaba intentar síntesis; no implica exceso real de tokens. Las dos respuestas generales de redacción quedaron `interrupted`, aunque el propietario las consideró útiles: no contarlas como generaciones completas. No se publican sus textos.

Correcciones aplicadas:

- Búsqueda documental previa también para asesoramiento/redacción permitidos. Sin evidencia, aviso explícito de que la orientación no procede del conocimiento empresarial y puede no ajustarse al caso. Citas prohibidas cuando no hay fuentes.
- Modo síntesis sin fallback extractivo silencioso: ante fallo de validación pide precisar o reintentar; el modo extractivo completo continúa disponible mediante configuración reversible.
- Soportes referenciados por IDs de pasajes, sin duplicar citas extensas en la salida generada. Hasta cuatro pasajes de la misma fuente por bloque; el esquema vincula fuente/pasajes y Python revalida identidad, cantidades, unidades, condiciones y actores.
- Segmentación temporal en lectura por oraciones completas con condiciones dependientes; no reindexa ni altera originales. Fuentes añadidas al final por backend.
- Dos sondeos del prompt y esquema exactos cuando los bytes conservadores exceden el presupuesto; deben coincidir y caber en3072 tokens de entrada reservados. Contexto4096/generación768 sin aumento.
- Seguimiento incorpora hasta1200 caracteres de redacción previa solo para identificar progreso; exige tema coincidente, fuentes antiguas todavía autorizadas y nueva recuperación/revalidación. Ese texto no acredita hechos vigentes.

### Inferencias reales medidas, sin aceptación automática

Se ejecutaron sondas seriales con Qwen habitual, sobre evidencia ya mostrada al propietario, con lease e inferencia durable normales. No se creó sesión/JWT alternativo ni se alteró su historial. Cada respuesta cruda y evidencia quedó exclusivamente en el paquete privado. Un primer intento no pudo guardar su informe por UUID sin serializar; se corrigió el productor y no se cuenta como resultado exitoso.

| Sonda guardada | Entrada/salida tokens | Tiempo total de sonda | Resultado técnico |
|---|---:|---:|---|
| Soporte inicial |584/234|12.250s|Unsupported claim|
| Esquema con IDs |1678/459|27.969s|Missing explicit condition|
| Pasajes más precisos |610/358|13.844s|Unsupported claim|
| Varios pasajes |1799/670|33.140s|Invalid passage reference|
| Fuente vinculada a pasajes |1799/695|31.344s|Missing explicit condition|

**0/5 sondas guardadas liberadas por el validador.** No se interpreta cada rechazo mecánico como alucinación semántica demostrada: exigir marcadores literales puede rechazar paráfrasis válidas; su alcance requiere revisión de los soportes privados. Tampoco se rebajan controles para convertirlas en aprobadas. El conjunto es conocido y ajustado, no holdout ni comparación ciega. Las sondas no incluyen el flujo completo de clasificación/búsqueda/chat y no representan latencia E2E.

RAM disponible mínima global observada:1.49–2.21GiB según sonda; GPU memoria usada pico3743MiB en todas. Son consumo/margen del equipo completo, no de LENY exclusivamente. Las cinco muestras no sustentan p95/SLA. No se modificaron límites; los valores por debajo2GiB se observaron durante inferencia, distintos del umbral de entrada2GiB y margen residente1GiB.

### MODISTA: evidencia disponible y decisión pendiente

El documento publicado cuyo título menciona MODISTA contiene43 fragmentos, pero ninguno menciona MODISTA. Se contrastó también su DOCX original publicado en solo lectura: el texto XML, incluidos otros componentes Word, no contiene MODISTA ni funciones; no contiene imágenes incrustadas. Estos recuentos no certifican por sí solos todo el significado del documento. Su título no autoriza atribuir funciones de otro cargo. Antes de añadir metadatos de responsabilidad, el propietario debe señalar la sección y confirmar la atribución; no se cambió su publicación/versión.

Verificación automatizada final de esta corrección: **515 pruebas backend aprobadas**, en la selección de contratos/regresiones; salud backend200 y diff sin errores. Esto no certifica síntesis real: sigue pendiente resolver el rechazo de condiciones con revisión de la respuesta/pasajes, comprobar recuperación integral de cargos y completar nueva aceptación del propietario. No se solicita repetir toda la batería como si el problema estuviera resuelto.

## Ajuste de paráfrasis autorizado (03/11/2026)

El propietario pidió expresamente hacer el validador menos restrictivo y corregir la interpretación de citas/pruebas. Se retiró la exigencia de que cada bloque repita literalmente todos los marcadores «antes», «después», «solo» o «no» de los pasajes usados. Se conservan vetos limitados a prohibiciones explícitas de la misma acción, negaciones nuevas frente a un soporte afirmativo y excepciones eliminadas. Estos patrones tampoco demuestran equivalencia semántica completa.

Las referencias de pasaje siguen siendo reales y de la fuente indicada; las cifras/unidades deben estar presentes en el fragmento citado completo, sin quedar limitadas al subconjunto de pasajes elegido por Qwen. Esto evita rechazar una síntesis que combina cantidades existentes en otros pasajes de la misma fuente. **Límite asumido:** la presencia en una fuente no prueba la asociación semántica correcta de cada cifra con entidad/condición. La revisión humana sigue siendo necesaria; no se presenta este ajuste como verificador de afirmaciones integral. Se mantienen ACL, elegibilidad/publicación vigente, secretos, citas y restricciones de herramientas.

El enrutamiento reconoce la programación de pruebas de confección sin nombre de empresa y tolera errores acotados de vocabulario como PRIEMRA→primera. La normalización se usa como pista de recuperación, preservando el mensaje original para seguridad/historial; no corrige ni elimina instrucciones maliciosas. Consultas de exámenes/laboratorio no se aprueban automáticamente como confección.

Verificación: **525 pruebas backend aprobadas**, incluyendo nuevas regresiones de paráfrasis, cantidades, citas de prueba y errores ortográficos; salud200 y diff correcto. Dos respuestas conocidas antes bloqueadas pasan la nueva validación, mientras que otras con referencias inválidas/cifras ajenas siguen rechazadas. Es un replay adaptado de casos conocidos, no una evaluación no vista.

**Nueva generación real:** usando la evidencia extensa ya mostrada al propietario, Qwen produjo una salida que pasó el validador ajustado: entrada1805tokens, salida597tokens,28.969s de sonda completa (duración del proveedor16.829s), RAM disponible mínima global2868965376bytes (aprox2.67GiB) y memoria GPU global máxima3743MiB,25muestras. Se conservaron4096/768. No es latencia E2E ni p95 y pasar este validador no equivale a aceptación humana. La respuesta y soportes están en el paquete privado; no se alteró el historial del propietario para simular una prueba de navegador.

Las cinco sondas negativas anteriores se conservan. La ronda nueva aporta1 generación técnicamente liberable, sin afirmar estabilidad global ni fidelidad certificada. Siguiente revisión focalizada del propietario: resumen de encargada Boutique, fecha de primera prueba con error de escritura y seguimiento «¿Y después?», en una conversación nueva. No se alteraron documentos, publicaciones, roles, índices ni modelos.

## Prueba del flujo backend completo y reducción de falsos rechazos (03/11/2026)

El propietario pidió expresamente hacer las pruebas por terminal con el backend y el modelo reales. Se añadió `backend/scripts/run_leny_v11_backend_review.py`: ejecuta clasificación, embedding CPU, SQL con ACL/publicación, selección, síntesis, validación, historial, fuentes, cuota y lease normales. Reutiliza la cuenta de la última revisión V1.1 del propietario y comprueba `reader`/Casbin; no crea JWT, usuarios o permisos. Crea conversaciones de revisión reales, sin modificar datos comerciales, biblioteca o índices. Preguntas, respuestas, fragmentos y muestras se guardan exclusivamente en el paquete privado protegido fuera del directorio web; la terminal imprime solo estados, contadores y tiempos.

Se reprodujeron dos rechazos adicionales que una sonda de generación directa no detectaba:

- Resumen de encargada: Qwen respondió con bloques general/example, pero el validador exigía una cita aun cuando esa orientación estaba permitida. Se permite ahora una respuesta completamente general, con aviso visible de ausencia de respaldo empresarial, sin fuentes ficticias. Los hechos internos siguen prohibidos en esos bloques.
- Confección: cantidades estaban en otra página seleccionada del mismo documento. Se admite respaldo numérico entre fragmentos seleccionados del **mismo índice publicado**, y se agregan las referencias a las páginas que aportan las cantidades/unidades. No se toman cifras de otro índice, documento o versión. Sigue siendo comprobación mecánica de presencia, no prueba de asociación semántica de cada cifra.

Los casos completos iniciales fueron: encargada38.469s→aclaración (Missing documentary support), confección53.859s→aclaración (Unsupported claim), fecha de primera prueba25.531s→respuesta documental con1fuente. Se conservan esos resultados negativos.

Pruebas automatizadas tras el ajuste: **527 aprobadas** en la selección de contratos/regresiones; se añadieron casos de general-only y combinación de páginas del mismo índice con rechazo al cambiar de índice. Backend salud200 y diff sin errores. Esto no acredita la aceptación semántica del propietario ni todos los escenarios del ERP.

### Repetición completa después de corregir

| Consulta | Salida observada | Tiempo E2E backend | Fuentes |
|---|---|---:|---:|
| Resumen de encargada Boutique |Answered, orientación general/example con aviso explícito, sin atribuirla a norma empresarial|34.453s|0|
| Cómo se confecciona un vestido |Answered, síntesis documental validada|48.328s|3|
| Cómo quedar fecha de PRIEMRA PRUEBA |Answered, síntesis documental validada|23.859s|1|

Las3 consultas pasaron el recorrido técnico completo sin el mensaje de fallo de síntesis. Son una repetición conocida con temperatura/configuración actuales, no estabilidad certificada, holdout ni aprobación humana. La encargada aún no tiene respuesta documental útil en esta ejecución: el cambio evita rechazar orientación permitida, pero no resuelve por sí solo la pertinencia/cobertura del cargo. No se declara que todo el RAG esté correcto. Las conversaciones se conservaron en el historial de su propietario; los informes privados distinguen la ejecución inicial de la ajustada.

Próximo paso: el propietario abre una conversación nueva por caso y revisa las seis preguntas del plan, citas/cargo/condiciones, seguimientos y abstención. Se correlacionarán sus resultados con historial/versiones de política y métricas, sin copiar contenido empresarial a informes públicos. El comando `rollback` restaura la configuración previa solo si su huella sigue coincidiendo, para no sobrescribir cambios posteriores.
