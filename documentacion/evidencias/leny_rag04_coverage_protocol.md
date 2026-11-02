# Protocolo previo: prototipo de cobertura independiente

Implementación autorizada del plan arquitectónico. Esta ronda no usa Ollama,
no migra ni conecta la base empresarial y no activa el candidato.

Se conserva como baseline `leny_rag04_semantic_focused.json`:48 registros,
47 objetivos ejecutados,14 naturales,39 esperados RAG y dos fallos críticos.
Corpus, gold, capturas y manifiestos históricos no se modifican.

Se implementará un verificador puro y una integración inyectable desactivada
por defecto. Interpretará la consulta original mediante un vocabulario
conceptual versionado; no recibe gold ni etiquetas del selector. Revisará
identidad, hashes, ámbito, aspectos, calificadores y dependencias del contenido
final. Ausencia, ambigüedad e incidencia operacional conservarán motivos distintos.

Las anotaciones producidas por agentes son **borradores**. La orden de implementar
no equivale a revisión humana de su contenido. Se entregarán para revisión; la
ejecución estricta no permitirá usarlas como cobertura aprobada. Un replay
exploratorio separado podrá simular su aprobación, siempre marcado como no
autoritativo y sin habilitar emisión documental en el servicio.

El experimento comprende los48 registros y12 controles adicionales propuestos
por otro agente, con expectativas humanas pendientes. No se afinan preguntas,
gold, vocabulario o manifiestos después de observar el replay para mejorar
resultados. Corregir errores de implementación antes de congelar se distingue
de ajustar el clasificador contra resultados.

Puertas del plan:0/2 aceptaciones críticas,14/14 naturales conservadas,
38/38 selecciones útiles conservadas, evidencia no inferior a38/39,3/3 abstenciones
en su categoría,6/6 positivos y6/6 negativos adicionales, cero violaciones ACL,
fuentes incorrectas, alteraciones de cifras/condiciones o errores de contexto.
Objetivos de coste del control: p95<=250ms e incremento de memoria<=128MiB,
sin inferencias nuevas ni VRAM adicional. Son objetivos, no mediciones.

Un replay de capturas no acredita recuperación nueva ni E2E. Mientras falte
aprobación de manifiestos/controles o una puerta falle, no se considera validado
el prototipo. No se implementa persistencia, UI ADMIN o migración de cobertura,
ni NLI o síntesis libre; requieren el resultado favorable y autorización posterior.
