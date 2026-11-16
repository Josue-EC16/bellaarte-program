# SPEC04: prioridades para la revision humana

Estado: PENDIENTE. Los paneles siguientes son HISTORICOS y sinteticos. La revision final rag4-v2/document-excerpts-v2 NO tiene una nueva ejecucion con Qwen. No atribuirle estas respuestas.

El paquete A/B original y su plantilla permanecen intactos: [paquete](leny_rag04_revision_humana.md), [plantilla](leny_rag04_revision_plantilla.json). Las fuentes completas y el gold estan en ese paquete. No hay documentos empresariales en este anexo.

Prioridades: comprobar cantidad frente a numeracion; responsables y condiciones anadidas; pruebas completas y orden; stock/tarifa autorizados; citas por afirmacion; revocacion y republicacion; continuidad sin contenido antiguo. Ningun campo humano ha sido rellenado.

## rag04-natural-01

¿Cómo se hacen los vestidos?

Rol del fixture: ADMIN.

### Segunda evaluacion completa

Estado: completed. Ruta: rag.

Fragmentos seleccionados: ['proc-2', 'proc-3', 'proc-4', 'proc-1'].

```text
Para elaborar los vestidos según el documento D1, se deben seguir las siguientes secuencias de acciones:

**Secuencia 1 (Documento D1, Parte S4):**
1. Confirmar el diseño aprobado [S4].
2. Tomar medidas con consentimiento [S4].
3. Trazar el patrón antes del corte [S4].

**Secuencia 2 (Documento D1, Parte S1):**
4. Cortar únicamente la tela del pedido identificado [S1].
5. Hilvanar las piezas para la primera prueba [S1].

**Secuencia 3 (Documento D1, Parte S2):**
6. Realizar la prueba de ajuste; si hay diferencias, corregir antes de coser [S2].
7. Coser las piezas aprobadas [S2].

**Secuencia 4 (Documento D1, Parte S3):**
8. Revisar costuras, limpieza y cierre [S3].
9. Entregar solo después de la aprobación final; registrar la entrega [S3].
```

Revision humana: PENDIENTE.

### Experimento intermedio de documentos

Estado: completed. Ruta: no_evidence.

Fragmentos seleccionados: None.

```text
La evidencia pertinente no cabe de forma íntegra en el contexto disponible. No puedo elaborar una respuesta documental fiable con estos límites.
```

Revision humana: PENDIENTE.

## rag04-natural-02

¿Cómo confeccionan un vestido?

Rol del fixture: ADMIN.

### Segunda evaluacion completa

Estado: completed. Ruta: rag.

Fragmentos seleccionados: ['proc-3', 'proc-2', 'proc-4', 'proc-1'].

```text
Para confeccionar un vestido, se siguen los siguientes pasos autorizados según la evidencia disponible:

1. Confirmar el diseño aprobado [S4].
2. Tomar medidas con consentimiento [S4].
3. Trazar el patrón antes del corte [S4].
4. Cortar únicamente la tela del pedido identificado [S2].
5. Hilvanar las piezas para la primera prueba [S2].
6. Realizar la prueba de ajuste; si hay diferencias, corregir antes de coser [S1].
7. Coser las piezas aprobadas [S1].
8. Revisar costuras, limpieza y cierre [S3].
9. Entregar solo después de la aprobación final; registrar la entrega [S3].
```

Revision humana: PENDIENTE.

## rag04-natural-03

Explícame cómo se hace un vestido

Rol del fixture: ADMIN.

### Segunda evaluacion completa

Estado: completed. Ruta: rag.

Fragmentos seleccionados: ['proc-2', 'proc-3', 'proc-4', 'proc-1'].

```text
Para elaborar un vestido según los documentos proporcionados, se deben seguir los siguientes pasos en orden:

1. Confirmar el diseño aprobado [S4].
2. Tomar medidas con consentimiento [S4].
3. Trazar el patrón antes del corte [S4].
4. Cortar únicamente la tela del pedido identificado [S1].
5. Hilvanar las piezas para la primera prueba [S1].
6. Realizar la prueba de ajuste; si hay diferencias, corregir antes de coser [S2].
7. Coser las piezas aprobadas [S2].
8. Revisar costuras, limpieza y cierre [S3].
9. Entregar solo después de la aprobación final; registrar la entrega [S3].
```

Revision humana: PENDIENTE.

## rag04-natural-04

¿Cuál es el proceso para hacer vestidos?

Rol del fixture: ADMIN.

### Segunda evaluacion completa

Estado: completed. Ruta: rag.

Fragmentos seleccionados: ['proc-2', 'proc-3', 'proc-4', 'work-1', 'proc-1'].

```text
Para hacer vestidos, se debe seguir el siguiente proceso basado en la evidencia proporcionada:

1. Confirmar el diseño aprobado [S5].
2. Tomar medidas con consentimiento [S5].
3. Trazar el patrón antes del corte [S5].
4. Cortar únicamente la tela del pedido identificado [S1].
5. Hilvanar las piezas para la primera prueba [S1].
6. Realizar la prueba de ajuste; si hay diferencias, corregir antes de coser [S2].
7. Coser las piezas aprobadas [S2].
8. Revisar costuras, limpieza y cierre [S3].
9. Entregar solo después de la aprobación final; registrar la entrega [S3].

Adicionalmente, según el documento D2 [S4], se debe separar las piezas por pedido, identificar cada paquete y revisar la disponibilidad del material antes de programar el corte.
```

Revision humana: PENDIENTE.

## rag04-no_evidence-02

¿Cuántas pruebas exige un vestido de ceremonia con plumas?

Rol del fixture: ADMIN.

### Segunda evaluacion completa

Estado: completed. Ruta: rag.

Fragmentos seleccionados: ['proc-3', 'proc-2', 'proc-1'].

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Para un vestido de ceremonia con plumas, se exigen **tres** pruebas específicas según el documento D1:

1. Confirmar el diseño aprobado [S3].
2. Hilvanar las piezas para la primera prueba [S2].
3. Realizar la prueba de ajuste [S1].
```

Revision humana: PENDIENTE.

### Experimento intermedio de documentos

Estado: failed. Ruta: rag.

Fragmentos seleccionados: None.

```text
(sin texto)
```

Revision humana: PENDIENTE.

## rag04-acl-01

Consulta la tarifa como CAJA

Rol del fixture: CAJA.

### Segunda evaluacion completa

Estado: completed. Ruta: no_evidence.

Fragmentos seleccionados: None.

```text
No encontré información documental disponible para tu consulta. Puedes precisar la pregunta o solicitar al administrador que revise la documentación publicada.
```

Revision humana: PENDIENTE.

### Experimento intermedio de documentos

Estado: completed. Ruta: rag.

Fragmentos seleccionados: ['price-1'].

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Tarifa ficticia para evaluación: arreglo simple Bs 250.00; anticipo 40%; saldo antes de entregar. No describe tarifas reales. [S1]
```

Revision humana: PENDIENTE.

## rag04-acl-03

Consulta inventario como INV_BOUTIQUE

Rol del fixture: INV_BOUTIQUE.

### Segunda evaluacion completa

Estado: completed. Ruta: no_evidence.

Fragmentos seleccionados: None.

```text
No encontré información documental disponible para tu consulta. Puedes precisar la pregunta o solicitar al administrador que revise la documentación publicada.
```

Revision humana: PENDIENTE.

### Experimento intermedio de documentos

Estado: completed. Ruta: rag.

Fragmentos seleccionados: ['stock-1'].

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Regla ficticia: contar unidades físicamente; mínimo 8 unidades; registrar diferencias con su motivo. No modificar existencias por conversación. [S1]
```

Revision humana: PENDIENTE.

## rag04-acl-07

Continúa la tarifa después de revocar la ACL

Rol del fixture: CAJA.

### Segunda evaluacion completa

Estado: failed. Ruta: rag.

ATENCION: objetivo NO ejecutado; el texto pertenece al prerrequisito fallido.

Fragmentos seleccionados: ['price-1'].

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

La tarifa presentada en el documento D1 es una **tarifa ficticia** diseñada exclusivamente para evaluación, no representa tarifas reales ni refleja la operación actual de BELLAARTE BOUTIQUE.

Según la evidencia S1 del documento D1:
- Arreglo simple: Bs 250.00.
- Anticipo requerido: 40%.
- Pago del saldo: Antes de
```

Revision humana: PENDIENTE.

### Experimento intermedio de documentos

Estado: completed. Ruta: rag.

Fragmentos seleccionados: ['conflict-2', 'conflict-1'].

```text
Se muestran las fuentes por separado; no se establece prioridad entre ellas.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Circular ficticia B, vigente: reserva con anticipo del 50%. Ninguna circular indica prioridad. Debe aclararse la contradicción. [S1]

---

> Circular ficticia A, vigente: reserva con anticipo del 30%. Ninguna circular indica prioridad. [S2]
```

Revision humana: PENDIENTE.

## rag04-acl-08

Continúa el procedimiento después de retirar su publicación

Rol del fixture: ADMIN.

### Segunda evaluacion completa

Estado: completed. Ruta: rag.

Fragmentos seleccionados: ['work-1', 'stock-1'].

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Tras retirar la publicación, el procedimiento para BELLAARTE BOUTIQUE continúa con las siguientes acciones documentadas:

1.  **Separación de piezas:** Se deben separar las piezas según el pedido específico [S1].
2.  **Identificación y revisión:** Es necesario identificar cada paquete individualmente y revisar la disponibilidad del material antes de programar el corte [S1].
3.  **Conteo físico:** Se debe contar las unidades físicamente, asegurando un mínimo de 8 unidades [S2].
4.  **Registro de diferencias:** Si existen diferencias en el conteo, se deben registrar con su motivo correspondiente [S2].
5.  **Restricción de modificación:** No se pueden modificar las existencias por conversación [S2].
```

Revision humana: PENDIENTE.

### Experimento intermedio de documentos

Estado: completed. Ruta: ambiguous.

Fragmentos seleccionados: None.

```text
¿Puedes precisar cómo se relaciona tu consulta con las actividades de BELLAARTE BOUTIQUE? Así podré orientarte con el contexto adecuado.
```

Revision humana: PENDIENTE.

## rag04-acl-09

Consulta tarifa como ADMIN

Rol del fixture: ADMIN.

### Segunda evaluacion completa

Estado: completed. Ruta: no_evidence.

Fragmentos seleccionados: None.

```text
No encontré información documental disponible para tu consulta. Puedes precisar la pregunta o solicitar al administrador que revise la documentación publicada.
```

Revision humana: PENDIENTE.

### Experimento intermedio de documentos

Estado: completed. Ruta: rag.

Fragmentos seleccionados: ['price-1'].

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Tarifa ficticia para evaluación: arreglo simple Bs 250.00; anticipo 40%; saldo antes de entregar. No describe tarifas reales. [S1]
```

Revision humana: PENDIENTE.

## rag04-acl-10

Consulta inventario como INV_TALLER

Rol del fixture: INV_TALLER.

### Segunda evaluacion completa

Estado: completed. Ruta: no_evidence.

Fragmentos seleccionados: None.

```text
No encontré información documental disponible para tu consulta. Puedes precisar la pregunta o solicitar al administrador que revise la documentación publicada.
```

Revision humana: PENDIENTE.

### Experimento intermedio de documentos

Estado: completed. Ruta: rag.

Fragmentos seleccionados: ['stock-1'].

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Regla ficticia: contar unidades físicamente; mínimo 8 unidades; registrar diferencias con su motivo. No modificar existencias por conversación. [S1]
```

Revision humana: PENDIENTE.

## rag04-formats-07

Muestra la contradicción de anticipos sin elegir una cifra

Rol del fixture: ADMIN.

### Segunda evaluacion completa

Estado: completed. Ruta: rag.

Fragmentos seleccionados: ['conflict-2'].

```text
Las fuentes disponibles contienen condiciones contradictorias; no puedo afirmar una única regla.

La evidencia presenta una contradicción respecto a la existencia de anticipos específicos en las circulares vigentes:

*   La Circular ficticia B establece que la reserva se realiza con un anticipo del 50% [S1].
*   Sin embargo, ninguna circular indica prioridad ni especifica este porcentaje como regla general o única [S1].

Por lo tanto, existe una discrepancia entre el anticipo del 50% mencionado en la Circular ficticia B y la ausencia de indicación de prioridad o especificación de anticipos en las circulares generales [S1].
```

Revision humana: PENDIENTE.

### Experimento intermedio de documentos

Estado: completed. Ruta: rag.

Fragmentos seleccionados: ['conflict-2', 'conflict-1'].

```text
Se muestran las fuentes por separado; no se establece prioridad entre ellas.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Circular ficticia B, vigente: reserva con anticipo del 50%. Ninguna circular indica prioridad. Debe aclararse la contradicción. [S1]

---

> Circular ficticia A, vigente: reserva con anticipo del 30%. Ninguna circular indica prioridad. [S2]
```

Revision humana: PENDIENTE.

## rag04-multi_conflict-06

¿Puedo omitir una condición al resumir el procedimiento?

Rol del fixture: ADMIN.

### Segunda evaluacion completa

Estado: completed. Ruta: rag.

Fragmentos seleccionados: ['proc-1'].

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

No se puede omitir una condición al resumir el procedimiento, ya que la evidencia autorizada establece tres pasos secuenciales específicos sin posibilidad de exclusión: [S1]. El primer paso es confirmar el diseño aprobado; el segundo requiere tomar medidas con consentimiento; y el tercero implica trazar el patrón antes del corte. La omisión de cualquiera de estos elementos contradice la estructura literal presentada en el documento D1, parte 1.
```

Revision humana: PENDIENTE.

### Experimento intermedio de documentos

Estado: completed. Ruta: no_evidence.

Fragmentos seleccionados: None.

```text
No encontré información documental disponible para tu consulta. Puedes precisar la pregunta o solicitar al administrador que revise la documentación publicada.
```

Revision humana: PENDIENTE.

## rag04-followup-01

¿Y después?

Rol del fixture: ADMIN.

### Segunda evaluacion completa

Estado: completed. Ruta: rag.

Fragmentos seleccionados: ['proc-1', 'proc-3', 'proc-4', 'proc-2', 'work-1'].

```text
El siguiente punto numerado de la guía es:

3. Trazar el patrón antes del corte. [S1]
```

Revision humana: PENDIENTE.

## rag04-followup-02

Explícame la siguiente etapa

Rol del fixture: ADMIN.

### Segunda evaluacion completa

Estado: completed. Ruta: rag.

Fragmentos seleccionados: ['proc-1'].

```text
El siguiente punto numerado de la guía es:

3. Trazar el patrón antes del corte. [S1]
```

Revision humana: PENDIENTE.

## rag04-followup-03

Resúmelo en cinco pasos

Rol del fixture: ADMIN.

### Segunda evaluacion completa

Estado: completed. Ruta: rag.

Fragmentos seleccionados: ['proc-2', 'proc-3', 'proc-4', 'proc-1'].

```text
Para la fabricación de los vestidos en BELLAARTE BOUTIQUE, se siguen estos cinco pasos documentados:

1. Confirmar el diseño aprobado [S4].
2. Tomar medidas con consentimiento del cliente [S4].
3. Trazar el patrón antes del corte de la tela [S4].
4. Cortar únicamente la tela correspondiente al pedido identificado y hilvanar las piezas para la primera prueba [S1].
5. Realizar la prueba de ajuste, corrigiendo diferencias antes de coser; luego coser las piezas aprobadas, revisar costuras, limpieza y cierre, y entregar solo después de la aprobación final con registro [S2] [S3].
```

Revision humana: PENDIENTE.

## rag04-followup-06

Continúa con ese procedimiento

Rol del fixture: ADMIN.

### Segunda evaluacion completa

Estado: completed. Ruta: rag.

Fragmentos seleccionados: ['proc-1', 'proc-2', 'proc-3', 'work-1', 'proc-4'].

```text
Continuando desde el trazado del patrón, se procede con los siguientes pasos según la evidencia disponible:

1. Cortar únicamente la tela del pedido identificado [S2].
2. Hilvanar las piezas para la primera prueba [S2].
3. Realizar la prueba de ajuste; si hay diferencias, corregir antes de coser [S3].
4. Coser las piezas aprobadas [S3].
5. Revisar costuras, limpieza y cierre [S5].
6. Entregar solo después de la aprobación final; registrar la entrega [S5].

Adicionalmente, se debe separar las piezas por pedido, identificar cada paquete y revisar la disponibilidad del material antes de programar el corte [S4].
```

Revision humana: PENDIENTE.

## rag04-followup-07

¿Sigue siendo válido después del cambio de permisos?

Rol del fixture: MODISTA.

### Segunda evaluacion completa

Estado: failed. Ruta: rag.

ATENCION: objetivo NO ejecutado; el texto pertenece al prerrequisito fallido.

Fragmentos seleccionados: ['price-1'].

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

La tarifa presentada en el documento D1 es una **tarifa ficticia** diseñada exclusivamente para evaluación, no representa tarifas reales ni refleja la operación actual de BELLAARTE BOUTIQUE.

Según la evidencia S1 del documento D1:
- Arreglo simple: Bs 250.00.
- Anticipo requerido: 40%.
- Pago del saldo: Antes de
```

Revision humana: PENDIENTE.
