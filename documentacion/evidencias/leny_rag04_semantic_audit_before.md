# Auditoria semantica previa: casos sinteticos criticos

Solo lectura del codigo y evidencia congelada antes de modificar funciones. No es valoracion humana ni lectura empresarial. Gold sin cambios. La causa interna de una decision Qwen no se deduce de su JSON.

## rag04-acl-01

1. Pregunta e intencion: Consulta la tarifa como CAJA Leer la tarifa documental disponible bajo la identidad CAJA real.

2. Gold: {"route": "rag", "relevant_fragment_ids": ["price-1"], "authorized_fragment_ids": ["proc-1", "proc-2", "proc-3", "proc-4", "price-1", "sec-1", "conflict-1", "conflict-2"], "required_fact_ids": ["price-250", "advance-40", "balance-before-delivery"], "required_step_ids": [], "required_numbers": ["250.00", "40%"], "requires_capability_ack": false, "required_condition_ids": ["balance-before-delivery"], "required_quantities": [{"value": "250.00", "unit": "BOB", "meaning": "simple-alteration-price"}, {"value": "40", "unit": "percent", "meaning": "advance-of-price"}]}

Justificacion: price-1 contiene importe, anticipo y saldo; la ACL del fixture admite CAJA. Debe explicarse como tarifa ficticia, no como precio empresarial real.

3. SQL autorizado: ["price-1", "conflict-2", "proc-2", "proc-4", "conflict-1", "proc-1", "proc-3", "sec-1"]; None significa etapa no ejecutada. UUID/version/indice/rangos: ver JSON pareado.

4. Revisor: ["price-1", "conflict-2", "proc-1", "proc-2", "proc-3", "proc-4"]

5. Decision estructurada: [{"fragment_ids": ["price-1", "conflict-2", "proc-1", "proc-2", "proc-3", "proc-4"], "decision": {"relation": "absent", "sources": []}}]

6. Evidencia salida: []; ruta no_evidence; estado completed.

```text
No encontré información documental disponible para tu consulta. Puedes precisar la pregunta o solicitar al administrador que revise la documentación publicada.
```

7. Causa confirmada: Gold llega a SQL puesto1 y al pool; relation=absent contradice la disponibilidad documental. No hay razonamiento interno del modelo registrado; no se puede probar que la palabra ficticia sea su causa psicologica.

8. Duda para revision humana: El gold es razonable en este corpus de una tarifa; fuera del corpus la tarifa sin servicio identificado podria requerir aclaracion.

## rag04-acl-09

1. Pregunta e intencion: Consulta tarifa como ADMIN Leer la tarifa documental disponible con identidad ADMIN real.

2. Gold: {"route": "rag", "relevant_fragment_ids": ["price-1"], "authorized_fragment_ids": ["proc-1", "proc-2", "proc-3", "proc-4", "price-1", "stock-1", "work-1", "sec-1", "conflict-1", "conflict-2"], "required_fact_ids": ["price-250", "advance-40", "balance-before-delivery"], "required_step_ids": [], "required_numbers": ["250.00", "40%"], "requires_capability_ack": false, "required_condition_ids": ["balance-before-delivery"], "required_quantities": [{"value": "250.00", "unit": "BOB", "meaning": "simple-alteration-price"}, {"value": "40", "unit": "percent", "meaning": "advance-of-price"}]}

Justificacion: Mismo respaldo documental price-1; ADMIN puede leerlo.

3. SQL autorizado: ["price-1", "conflict-2", "proc-2", "conflict-1", "proc-4", "stock-1", "proc-1", "proc-3", "work-1", "sec-1"]; None significa etapa no ejecutada. UUID/version/indice/rangos: ver JSON pareado.

4. Revisor: ["price-1", "conflict-2", "proc-1", "proc-2", "proc-3", "proc-4"]

5. Decision estructurada: [{"fragment_ids": ["price-1", "conflict-2", "proc-1", "proc-2", "proc-3", "proc-4"], "decision": {"relation": "absent", "sources": []}}]

6. Evidencia salida: []; ruta no_evidence; estado completed.

```text
No encontré información documental disponible para tu consulta. Puedes precisar la pregunta o solicitar al administrador que revise la documentación publicada.
```

7. Causa confirmada: El gold llega a SQL puesto1 y al pool; el plan lo rechaza como absent. El problema confirmado es la decision de pertinencia, no un filtro ACL.

8. Duda para revision humana: Misma salvedad sobre contexto de una tarifa; sin discrepancia material en este fixture.

## rag04-formats-05

1. Pregunta e intencion: Explica la tarifa con cifras exactas y cita la fuente Explicar importe y condiciones de la tarifa, conservando cifras y citas.

2. Gold: {"route": "rag", "relevant_fragment_ids": ["price-1"], "authorized_fragment_ids": ["proc-1", "proc-2", "proc-3", "proc-4", "price-1", "stock-1", "work-1", "sec-1", "conflict-1", "conflict-2"], "required_fact_ids": ["price-250", "advance-40", "balance-before-delivery"], "required_step_ids": [], "required_numbers": ["250.00", "40%"], "requires_capability_ack": false, "required_condition_ids": ["balance-before-delivery"], "required_quantities": [{"value": "250.00", "unit": "BOB", "meaning": "simple-alteration-price"}, {"value": "40", "unit": "percent", "meaning": "advance-of-price"}]}

Justificacion: price-1 contiene Bs250.00, anticipo40% y saldo antes de entregar.

3. SQL autorizado: ["price-1", "conflict-2", "stock-1", "proc-2", "proc-4", "conflict-1", "proc-3", "proc-1", "work-1", "sec-1"]; None significa etapa no ejecutada. UUID/version/indice/rangos: ver JSON pareado.

4. Revisor: ["price-1", "conflict-2", "stock-1"]

5. Decision estructurada: [{"fragment_ids": ["price-1", "conflict-2", "stock-1"], "decision": {"relation": "absent", "sources": []}}]

6. Evidencia salida: []; ruta no_evidence; estado completed.

```text
No encontré información documental disponible para tu consulta. Puedes precisar la pregunta o solicitar al administrador que revise la documentación publicada.
```

7. Causa confirmada: Evidencia especifica presente SQL puesto1/pool; selector absent. La peticion de cifras exactas no exige datos externos ni cambiar la fuente.

8. Duda para revision humana: No usar la cifra como tarifa real de la empresa: el propio fixture la declara ficticia.

## rag04-synonyms-07

1. Pregunta e intencion: ¿Cuándo se hacen los retoques? Saber en que momento del proceso se realizan correcciones o retoques.

2. Gold: {"route": "rag", "relevant_fragment_ids": ["proc-3"], "authorized_fragment_ids": ["proc-1", "proc-2", "proc-3", "proc-4", "price-1", "stock-1", "work-1", "sec-1", "conflict-1", "conflict-2"], "required_fact_ids": ["fit", "correct-before-sewing"], "required_step_ids": ["step-6"], "required_numbers": [], "requires_capability_ack": false, "required_condition_ids": ["correct-differences-before-sewing"], "required_quantities": []}

Justificacion: proc-3 indica prueba de ajuste y corregir diferencias antes de coser. Respalda momento relativo y condicion, no fecha ni duracion.

3. SQL autorizado: ["proc-3", "proc-4", "proc-2", "work-1", "proc-1", "price-1", "stock-1", "conflict-2", "conflict-1", "sec-1"]; None significa etapa no ejecutada. UUID/version/indice/rangos: ver JSON pareado.

4. Revisor: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1", "price-1"]

5. Decision estructurada: [{"fragment_ids": ["proc-1", "proc-2", "proc-3", "proc-4", "work-1", "price-1"], "decision": {"relation": "absent", "sources": []}}]

6. Evidencia salida: []; ruta no_evidence; estado completed.

```text
No encontré información documental disponible para tu consulta. Puedes precisar la pregunta o solicitar al administrador que revise la documentación publicada.
```

7. Causa confirmada: proc-3 SQL puesto1/pool; selector absent. No falta un plazo numerico: la pregunta pide momento relativo.

8. Duda para revision humana: Retoques puede significar acabados posteriores; la equivalencia con corregir diferencias es razonable, pero debe reconocerse como interpretacion contextual y someterse a revision humana.

## rag04-multi_conflict-06

1. Pregunta e intencion: ¿Puedo omitir una condición al resumir el procedimiento? Saber si al resumir se pueden omitir condiciones del procedimiento.

2. Gold: {"route": "rag", "relevant_fragment_ids": ["proc-3", "proc-4"], "authorized_fragment_ids": ["proc-1", "proc-2", "proc-3", "proc-4", "price-1", "stock-1", "work-1", "sec-1", "conflict-1", "conflict-2"], "required_fact_ids": ["correct-before-sewing", "approval-before-delivery"], "required_step_ids": [], "required_numbers": [], "requires_capability_ack": false, "required_condition_ids": ["correct-differences-before-sewing", "final-approval-before-delivery"], "required_quantities": []}

Justificacion: proc-3 exige corregir antes de coser; proc-4 condiciona entrega a aprobacion. Permiten exponer esas condiciones, sin autorizar su omision.

3. SQL autorizado: ["proc-2", "proc-4", "stock-1", "conflict-2", "proc-1", "proc-3", "work-1", "price-1", "conflict-1", "sec-1"]; None significa etapa no ejecutada. UUID/version/indice/rangos: ver JSON pareado.

4. Revisor: ["proc-1", "proc-2", "proc-3", "proc-4", "stock-1", "conflict-2"]

5. Decision estructurada: [{"fragment_ids": ["proc-1", "proc-2", "proc-3", "proc-4", "stock-1", "conflict-2"], "decision": {"relation": "absent", "sources": []}}]

6. Evidencia salida: []; ruta no_evidence; estado completed.

```text
No encontré información documental disponible para tu consulta. Puedes precisar la pregunta o solicitar al administrador que revise la documentación publicada.
```

7. Causa confirmada: Gold llega al pool; absent en el plan. Hay respaldo parcial para condiciones concretas, pero no norma documental sobre como resumir.

8. Duda para revision humana: Los fragmentos no regulan literalmente el acto de resumir ni todas las condiciones posibles; exigir un NO absoluto excederia la fuente. Revisar si el gold debe evaluar exposicion fiel de condiciones como respuesta parcial. No se modifica.

## rag04-multi_conflict-07

1. Pregunta e intencion: Describe el proceso utilizando varios fragmentos Describir un proceso mediante varios fragmentos, sin identificar el proceso.

2. Gold: {"route": "rag", "relevant_fragment_ids": ["proc-1", "proc-2", "proc-3", "proc-4"], "authorized_fragment_ids": ["proc-1", "proc-2", "proc-3", "proc-4", "price-1", "stock-1", "work-1", "sec-1", "conflict-1", "conflict-2"], "required_fact_ids": ["design", "measure", "pattern", "cut", "baste", "fit", "correct-before-sewing", "sew", "quality", "approval-before-delivery", "delivery-record"], "required_step_ids": ["step-1", "step-2", "step-3", "step-4", "step-5", "step-6", "step-7", "step-8", "step-9"], "required_numbers": [], "requires_capability_ack": false, "required_condition_ids": ["approved-design", "measurement-consent", "pattern-before-cut", "identified-order-fabric", "correct-differences-before-sewing", "sew-approved-pieces", "final-approval-before-delivery"], "required_quantities": []}

Justificacion: El gold designa el procedimiento de confeccion proc1..4.

3. SQL autorizado: null; None significa etapa no ejecutada. UUID/version/indice/rangos: ver JSON pareado.

4. Revisor: null

5. Decision estructurada: null

6. Evidencia salida: []; ruta ambiguous; estado completed.

```text
¿Puedes precisar cómo se relaciona tu consulta con las actividades de BELLAARTE BOUTIQUE? Así podré orientarte con el contexto adecuado.
```

7. Causa confirmada: Clasificador contextual ambiguo; no se ejecuta SQL/revisor en API. SQL independiente puede recuperar textos si se fuerza, pero no prueba que la intencion sea confeccion.

8. Duda para revision humana: Discrepancia sustantiva: no hay pregunta previa ni entidad/proceso explicitado; el corpus contiene varios asuntos. Pedir aclaracion puede ser correcto. Solicitar anotacion humana independiente sin cambiar gold ni forzar ruta por la frase de prueba.

## rag04-no_evidence-01

1. Pregunta e intencion: ¿Qué procedimiento publicado regula bordados con hilo de oro? Encontrar regulacion publicada para una tecnica concreta y su material especializado.

2. Gold: {"route": "no_evidence", "relevant_fragment_ids": [], "authorized_fragment_ids": ["proc-1", "proc-2", "proc-3", "proc-4", "price-1", "stock-1", "work-1", "sec-1", "conflict-1", "conflict-2"], "required_fact_ids": [], "required_step_ids": [], "required_numbers": [], "requires_capability_ack": false, "required_condition_ids": [], "required_quantities": []}

Justificacion: Ningun fragmento describe bordado con hilo de oro. El procedimiento general solo describe confeccion.

3. SQL autorizado: ["proc-2", "proc-3", "proc-4", "proc-1", "stock-1", "work-1", "price-1", "conflict-2", "conflict-1", "sec-1"]; None significa etapa no ejecutada. UUID/version/indice/rangos: ver JSON pareado.

4. Revisor: ["proc-1", "proc-2", "proc-3", "proc-4", "stock-1", "work-1"]

5. Decision estructurada: [{"fragment_ids": ["proc-1", "proc-2", "proc-3", "proc-4", "stock-1", "work-1"], "decision": {"relation": "partial", "sources": [1, 2, 3, 4]}}]

6. Evidencia salida: ["proc-1", "proc-2", "proc-3", "proc-4"]; ruta rag; estado completed.

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

7. Causa confirmada: Plan partial elige proc1..4 sin respaldo de la especialidad; expansion de procedimiento y renderizado conservan literalmente contenido tangencial. El fallo confirmado esta en el alcance semantico del selector; la cita valida no lo corrige.

8. Duda para revision humana: Gold no_evidence tiene respaldo: coincidencia del sector no acredita especialidad.

## rag04-followup-07

1. Pregunta e intencion: ¿Sigue siendo válido después del cambio de permisos? Revisar lo explicado previamente de tarifa tras cambio efectivo de rol a MODISTA.

2. Gold: {"route": "no_evidence", "relevant_fragment_ids": [], "authorized_fragment_ids": ["proc-1", "proc-2", "proc-3", "proc-4", "work-1", "sec-1"], "required_fact_ids": [], "required_step_ids": [], "required_numbers": [], "requires_capability_ack": false, "required_condition_ids": [], "required_quantities": []}

Justificacion: El tema previo price-1 era legible como ADMIN; luego MODISTA no tiene ACL. Gold exige recuperar de nuevo y abstenerse sin texto anterior.

3. SQL autorizado: null; None significa etapa no ejecutada. UUID/version/indice/rangos: ver JSON pareado.

4. Revisor: null

5. Decision estructurada: null

6. Evidencia salida: []; ruta ambiguous; estado completed.

```text
¿Puedes precisar cómo se relaciona tu consulta con las actividades de BELLAARTE BOUTIQUE? Así podré orientarte con el contexto adecuado.
```

7. Causa confirmada: El journal muestra no_evidence en la pregunta previa. No se guarda ancla de ausencia por seguridad; objetivo posterior resulta followup_without_topic. No relajar memoria: corregir respuesta previa.

8. Duda para revision humana: Gold supone un ancla previa correcta. Si ese prerrequisito se abstiene, aclarar es seguro pero no demuestra prueba de revocacion ni satisface el escenario previsto. Mantener fallo y registrar dependencia.

## rag04-acl-07

1. Pregunta e intencion: Continúa la tarifa después de revocar la ACL Continuar la tarifa previa despues de revocar su ACL en la base aislada.

2. Gold: {"route": "no_evidence", "relevant_fragment_ids": [], "authorized_fragment_ids": ["proc-1", "proc-2", "proc-3", "proc-4", "sec-1", "conflict-1", "conflict-2"], "required_fact_ids": [], "required_step_ids": [], "required_numbers": [], "requires_capability_ack": false, "required_condition_ids": [], "required_quantities": []}

Justificacion: price-1 estaba publicado/autorizado para CAJA; se elimina ACL antes del seguimiento. Fuentes restantes no son sustituto de esa tarifa.

3. SQL autorizado: null; None significa etapa no ejecutada. UUID/version/indice/rangos: ver JSON pareado.

4. Revisor: null

5. Decision estructurada: null

6. Evidencia salida: []; ruta ambiguous; estado completed.

```text
¿Puedes precisar cómo se relaciona tu consulta con las actividades de BELLAARTE BOUTIQUE? Así podré orientarte con el contexto adecuado.
```

7. Causa confirmada: Prerrequisito de tarifa se abstuvo; topic_history vacio; objetivo ambiguo. No hay consulta SQL de seguimiento: la revocacion se aplica pero ese recorrido no se ejercio.

8. Duda para revision humana: Gold tambien presupone respuesta previa pertinente. La ausencia del ancla explica aclaracion segura sin validar el recorrido de revocacion.

