# Decisiones previas a la evaluación focalizada semántica

Auditoría de nueve escenarios documentada en `leny_rag04_semantic_audit_before.json`
y `.md` antes de editar funciones. No hubo lectura de documentos empresariales.
El corpus y sus gold permanecen congelados. Una segunda revisión técnica de solo
lectura coincide con la localización de los fallos y las dudas siguientes.

## Discrepancias reservadas para aprobación humana

- `multi_conflict-07`: sin historial ni proceso identificado, pedir aclaración
  es defendible. El gold espera confección completa, pero el identificador de
  familia no es contexto disponible para el agente. No forzar esa ruta ni
  cambiar el gold para mejorar una métrica.
- `multi_conflict-06`: las fuentes regulan ejecución, no cómo redactar resúmenes.
  Pueden exponerse las condiciones documentadas; no puede atribuirse una norma
  universal sobre resúmenes. Revisar también por qué el gold exige sólo dos de
  varias condiciones esenciales. La salida extractiva no añade una prohibición.
- `synonyms-07`: retoques puede significar correcciones de la prueba de ajuste
  o acabados posteriores. El gold es una paráfrasis contextual razonable, pero
  no demuestra que todo retoque se haga sólo antes de coser. La valoración humana
  debe considerar límites o aclaración, sin completar automáticamente la rúbrica.
- `followup-07`/`acl-07`: la respuesta de tarifa previa fue una falsa abstención.
  La aclaración posterior es segura, pero no acredita el recorrido de revocación
  sobre una fuente anteriormente utilizada. La nueva traza conservará la
  observación completa de cada turno sintético para comprobar el prerrequisito.
  Revocar acceso no demuestra que una tarifa haya perdido vigencia comercial.

## Corrección acotada y única

Selector `aspect-scope-evidence-plan-v1`: una clasificación conjunta con el mismo
Qwen, que declara aspecto solicitado y alcance antes de relación y referencias.
Los aspectos son categorías de intención, no funciones ni autorizaciones. El
backend no acepta IDs si el alcance declarado es más amplio, ausente o incierto.
Las fuentes ficticias se pueden explicar como ejemplos sin afirmar que sus cifras
sean precios empresariales reales. Tiempo relativo no exige una duración numérica.

Se conserva SQL ACL, publicación, versiones, modelo/digest, preselección acotada,
máximo5, contexto4096, reserva768, clasificador96, cuota5/60s, exclusión global1,
CPU para embeddings y los umbrales de memoria. El historial de políticas previas
no se reutiliza como contexto bajo `rag4-v4`; no se borra historia. No se cambia
enrutamiento para memorizar el enunciado ambiguo.

Aspecto y alcance siguen siendo juicios falibles del mismo modelo. El contrato
tipado comprueba coherencia, no demuestra por sí solo relevancia. Las respuestas
siguen siendo extractos backend de fuentes actuales y autorizadas. No se añade
un juez LLM, filtros por ID o respuestas del gold. No hay reintento semántico
oculto ni selección del mejor resultado.

## Criterios antes de ejecutar

1. Contratos deterministas e integración aislada aprobados, sin DDL ni modelos.
2. Ventana exclusiva Ollama solicitada después de esas comprobaciones.
3. Una única ronda focalizada de los mismos48 escenarios, incluidas14 naturales,
   errores prioritarios, fuentes autorizadas/revocadas, contradicciones y ausencia.
4. Comparar antes/después con el mismo evaluador y denominadores; conservar todos
   los errores. No ocultar discrepancias de gold ni quitar casos del denominador.
5. Mantener14/14 naturales, cero fuentes no autorizadas, referencias inexistentes
   o errores de contexto. Exigir corregir las tres tarifas y acreditar los
   prerrequisitos de revocación. Ninguna respuesta para una especialidad sin
   respaldo. La presencia de gold y las citas literales no acreditan todas las
   afirmaciones: revisión humana posterior sigue pendiente.
6. Si persiste cualquier falsa abstención o respuesta tangencial crítica, detener
   los ajustes. Documentar limitaciones, alternativas y costes para decisión de
   arquitectura. No ejecutar84, holdout36 ni activar `rag4_v1`.

Los criterios globales ya aprobados no se modifican. Estos son controles de
avance para una ronda focalizada, no una aceptación completa de SPEC04.
