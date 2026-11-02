# LENY SPEC04: revision humana por capas

Estado: pendiente. Datos exclusivamente sinteticos. Pareja de candidatos de desarrollo vistos; no es holdout ni documentacion empresarial real.

Revisar fidelidad, pertinencia, completitud, orden, cifras/unidades, condiciones, responsables y utilidad. Identificar afirmaciones sin respaldo y citas tangenciales incluso cuando el texto sea literal. No convertir completed, Hit@K o una fuente autorizada en una valoracion semantica.

Prioridad critica: no_evidence-01 (procedimiento general presentado para bordado especializado); formats-05, acl-01/09 (tarifa disponible rechazada); synonyms-07; multi_conflict-06; followup-07 y acl-07 (prerrequisito fallido semanticamente). Revisar tambien naturales con work-1 adicional, literal-08, synonyms-11 y todas las contradicciones.

Las etiquetas estan separadas en leny_rag04_layers_revision_clave.json. La plantilla conserva review=null; todas las valoraciones deben proceder de una revision humana efectiva. Los 36 reservados no se incluyen.

## Fuentes completas

### synthetic-procedure-v1

Roles del fixture: ADMIN, CAJA, INV_BOUTIQUE, INV_TALLER, MODISTA

#### proc-1

```text
Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte.
```

Hechos: design, measure, pattern
Pasos: step-1, step-2, step-3
Condiciones: approved-design, measurement-consent, pattern-before-cut

#### proc-2

```text
Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba.
```

Hechos: cut, baste
Pasos: step-4, step-5
Condiciones: identified-order-fabric

#### proc-3

```text
Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas.
```

Hechos: fit, correct-before-sewing, sew
Pasos: step-6, step-7
Condiciones: correct-differences-before-sewing, sew-approved-pieces

#### proc-4

```text
Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega.
```

Hechos: quality, approval-before-delivery, delivery-record
Pasos: step-8, step-9
Condiciones: final-approval-before-delivery

### synthetic-prices-v1

Roles del fixture: ADMIN, CAJA

#### price-1

```text
Tarifa ficticia para evaluación: arreglo simple Bs 250.00; anticipo 40%; saldo antes de entregar. No describe tarifas reales.
```

Hechos: price-250, advance-40, balance-before-delivery
Pasos: 
Condiciones: balance-before-delivery

### synthetic-stock-v1

Roles del fixture: ADMIN, INV_BOUTIQUE, INV_TALLER

#### stock-1

```text
Regla ficticia: contar unidades físicamente; mínimo 8 unidades; registrar diferencias con su motivo. No modificar existencias por conversación.
```

Hechos: physical-count, minimum-8, difference-reason
Pasos: 
Condiciones: difference-with-reason, no-conversational-stock-write

### synthetic-workshop-v1

Roles del fixture: ADMIN, MODISTA, INV_TALLER

#### work-1

```text
Organización ficticia: separar piezas por pedido, identificar cada paquete y revisar la disponibilidad del material antes de programar el corte.
```

Hechos: separate-order, identify-package, material-before-cut
Pasos: 
Condiciones: material-before-cut

### synthetic-security-v1

Roles del fixture: ADMIN, CAJA, INV_BOUTIQUE, INV_TALLER, MODISTA

#### sec-1

```text
Guía defensiva ficticia: usar cuentas individuales, comprobar permisos en el servidor y revisar registros sin compartir contraseñas.
```

Hechos: individual-account, server-permission, no-password-sharing
Pasos: 
Condiciones: no-password-sharing

### synthetic-disagreement-a

Roles del fixture: ADMIN, CAJA

#### conflict-1

```text
Circular ficticia A, vigente: reserva con anticipo del 30%. Ninguna circular indica prioridad.
```

Hechos: advance-30
Pasos: 
Condiciones: no-circular-priority

### synthetic-disagreement-b

Roles del fixture: ADMIN, CAJA

#### conflict-2

```text
Circular ficticia B, vigente: reserva con anticipo del 50%. Ninguna circular indica prioridad. Debe aclararse la contradicción.
```

Hechos: advance-50, unresolved-conflict
Pasos: 
Condiciones: no-circular-priority

## rag04-natural-01

Categoria: natural; rol autenticado: ADMIN

```text
¿Cómo se hacen los vestidos?
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [
    "design",
    "measure",
    "pattern",
    "cut",
    "baste",
    "fit",
    "correct-before-sewing",
    "sew",
    "quality",
    "approval-before-delivery",
    "delivery-record"
  ],
  "required_step_ids": [
    "step-1",
    "step-2",
    "step-3",
    "step-4",
    "step-5",
    "step-6",
    "step-7",
    "step-8",
    "step-9"
  ],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [
    "approved-design",
    "measurement-consent",
    "pattern-before-cut",
    "identified-order-fabric",
    "correct-differences-before-sewing",
    "sew-approved-pieces",
    "final-approval-before-delivery"
  ],
  "required_quantities": []
}
```

### Panel A

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4"]

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

### Panel B

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]

---

> Organización ficticia: separar piezas por pedido, identificar cada paquete y revisar la disponibilidad del material antes de programar el corte. [S5]
```

## rag04-natural-02

Categoria: natural; rol autenticado: ADMIN

```text
¿Cómo confeccionan un vestido?
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [
    "design",
    "measure",
    "pattern",
    "cut",
    "baste",
    "fit",
    "correct-before-sewing",
    "sew",
    "quality",
    "approval-before-delivery",
    "delivery-record"
  ],
  "required_step_ids": [
    "step-1",
    "step-2",
    "step-3",
    "step-4",
    "step-5",
    "step-6",
    "step-7",
    "step-8",
    "step-9"
  ],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [
    "approved-design",
    "measurement-consent",
    "pattern-before-cut",
    "identified-order-fabric",
    "correct-differences-before-sewing",
    "sew-approved-pieces",
    "final-approval-before-delivery"
  ],
  "required_quantities": []
}
```

### Panel A

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]

---

> Organización ficticia: separar piezas por pedido, identificar cada paquete y revisar la disponibilidad del material antes de programar el corte. [S5]
```

### Panel B

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4"]

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

## rag04-natural-03

Categoria: natural; rol autenticado: ADMIN

```text
Explícame cómo se hace un vestido
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [
    "design",
    "measure",
    "pattern",
    "cut",
    "baste",
    "fit",
    "correct-before-sewing",
    "sew",
    "quality",
    "approval-before-delivery",
    "delivery-record"
  ],
  "required_step_ids": [
    "step-1",
    "step-2",
    "step-3",
    "step-4",
    "step-5",
    "step-6",
    "step-7",
    "step-8",
    "step-9"
  ],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [
    "approved-design",
    "measurement-consent",
    "pattern-before-cut",
    "identified-order-fabric",
    "correct-differences-before-sewing",
    "sew-approved-pieces",
    "final-approval-before-delivery"
  ],
  "required_quantities": []
}
```

### Panel A

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

### Panel B

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

## rag04-natural-04

Categoria: natural; rol autenticado: ADMIN

```text
¿Cuál es el proceso para hacer vestidos?
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [
    "design",
    "measure",
    "pattern",
    "cut",
    "baste",
    "fit",
    "correct-before-sewing",
    "sew",
    "quality",
    "approval-before-delivery",
    "delivery-record"
  ],
  "required_step_ids": [
    "step-1",
    "step-2",
    "step-3",
    "step-4",
    "step-5",
    "step-6",
    "step-7",
    "step-8",
    "step-9"
  ],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [
    "approved-design",
    "measurement-consent",
    "pattern-before-cut",
    "identified-order-fabric",
    "correct-differences-before-sewing",
    "sew-approved-pieces",
    "final-approval-before-delivery"
  ],
  "required_quantities": []
}
```

### Panel A

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4"]

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

### Panel B

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1"]

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]

---

> Organización ficticia: separar piezas por pedido, identificar cada paquete y revisar la disponibilidad del material antes de programar el corte. [S5]
```

## rag04-natural-05

Categoria: natural; rol autenticado: ADMIN

```text
¿Cómo elaboramos vestidos?
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [
    "design",
    "measure",
    "pattern",
    "cut",
    "baste",
    "fit",
    "correct-before-sewing",
    "sew",
    "quality",
    "approval-before-delivery",
    "delivery-record"
  ],
  "required_step_ids": [
    "step-1",
    "step-2",
    "step-3",
    "step-4",
    "step-5",
    "step-6",
    "step-7",
    "step-8",
    "step-9"
  ],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [
    "approved-design",
    "measurement-consent",
    "pattern-before-cut",
    "identified-order-fabric",
    "correct-differences-before-sewing",
    "sew-approved-pieces",
    "final-approval-before-delivery"
  ],
  "required_quantities": []
}
```

### Panel A

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1"]

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]

---

> Organización ficticia: separar piezas por pedido, identificar cada paquete y revisar la disponibilidad del material antes de programar el corte. [S5]
```

### Panel B

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4"]

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

## rag04-natural-06

Categoria: natural; rol autenticado: ADMIN

```text
¿Qué pasos lleva confeccionar un vestido?
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [
    "design",
    "measure",
    "pattern",
    "cut",
    "baste",
    "fit",
    "correct-before-sewing",
    "sew",
    "quality",
    "approval-before-delivery",
    "delivery-record"
  ],
  "required_step_ids": [
    "step-1",
    "step-2",
    "step-3",
    "step-4",
    "step-5",
    "step-6",
    "step-7",
    "step-8",
    "step-9"
  ],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [
    "approved-design",
    "measurement-consent",
    "pattern-before-cut",
    "identified-order-fabric",
    "correct-differences-before-sewing",
    "sew-approved-pieces",
    "final-approval-before-delivery"
  ],
  "required_quantities": []
}
```

### Panel A

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4"]

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

### Panel B

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4"]

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

## rag04-natural-07

Categoria: natural; rol autenticado: ADMIN

```text
¿Cómo hacemos una prenda de principio a fin?
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [
    "design",
    "measure",
    "pattern",
    "cut",
    "baste",
    "fit",
    "correct-before-sewing",
    "sew",
    "quality",
    "approval-before-delivery",
    "delivery-record"
  ],
  "required_step_ids": [
    "step-1",
    "step-2",
    "step-3",
    "step-4",
    "step-5",
    "step-6",
    "step-7",
    "step-8",
    "step-9"
  ],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [
    "approved-design",
    "measurement-consent",
    "pattern-before-cut",
    "identified-order-fabric",
    "correct-differences-before-sewing",
    "sew-approved-pieces",
    "final-approval-before-delivery"
  ],
  "required_quantities": []
}
```

### Panel A

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4"]

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

### Panel B

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]

---

> Organización ficticia: separar piezas por pedido, identificar cada paquete y revisar la disponibilidad del material antes de programar el corte. [S5]
```

## rag04-natural-08

Categoria: natural; rol autenticado: ADMIN

```text
Necesito entender cómo fabricamos un vestido
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [
    "design",
    "measure",
    "pattern",
    "cut",
    "baste",
    "fit",
    "correct-before-sewing",
    "sew",
    "quality",
    "approval-before-delivery",
    "delivery-record"
  ],
  "required_step_ids": [
    "step-1",
    "step-2",
    "step-3",
    "step-4",
    "step-5",
    "step-6",
    "step-7",
    "step-8",
    "step-9"
  ],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [
    "approved-design",
    "measurement-consent",
    "pattern-before-cut",
    "identified-order-fabric",
    "correct-differences-before-sewing",
    "sew-approved-pieces",
    "final-approval-before-delivery"
  ],
  "required_quantities": []
}
```

### Panel A

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]

---

> Organización ficticia: separar piezas por pedido, identificar cada paquete y revisar la disponibilidad del material antes de programar el corte. [S5]
```

### Panel B

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4"]

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

## rag04-natural-09

Categoria: natural; rol autenticado: ADMIN

```text
¿Cómo se transforma la tela en un vestido?
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [
    "design",
    "measure",
    "pattern",
    "cut",
    "baste",
    "fit",
    "correct-before-sewing",
    "sew",
    "quality",
    "approval-before-delivery",
    "delivery-record"
  ],
  "required_step_ids": [
    "step-1",
    "step-2",
    "step-3",
    "step-4",
    "step-5",
    "step-6",
    "step-7",
    "step-8",
    "step-9"
  ],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [
    "approved-design",
    "measurement-consent",
    "pattern-before-cut",
    "identified-order-fabric",
    "correct-differences-before-sewing",
    "sew-approved-pieces",
    "final-approval-before-delivery"
  ],
  "required_quantities": []
}
```

### Panel A

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4"]

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

### Panel B

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

## rag04-natural-10

Categoria: natural; rol autenticado: ADMIN

```text
Descríbeme el proceso de confección
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [
    "design",
    "measure",
    "pattern",
    "cut",
    "baste",
    "fit",
    "correct-before-sewing",
    "sew",
    "quality",
    "approval-before-delivery",
    "delivery-record"
  ],
  "required_step_ids": [
    "step-1",
    "step-2",
    "step-3",
    "step-4",
    "step-5",
    "step-6",
    "step-7",
    "step-8",
    "step-9"
  ],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [
    "approved-design",
    "measurement-consent",
    "pattern-before-cut",
    "identified-order-fabric",
    "correct-differences-before-sewing",
    "sew-approved-pieces",
    "final-approval-before-delivery"
  ],
  "required_quantities": []
}
```

### Panel A

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4"]

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

### Panel B

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]

---

> Organización ficticia: separar piezas por pedido, identificar cada paquete y revisar la disponibilidad del material antes de programar el corte. [S5]
```

## rag04-natural-11

Categoria: natural; rol autenticado: ADMIN

```text
¿Qué se hace antes de cortar la tela?
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "proc-1"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [
    "design",
    "measure",
    "pattern"
  ],
  "required_step_ids": [
    "step-1",
    "step-2",
    "step-3"
  ],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [
    "approved-design",
    "measurement-consent",
    "pattern-before-cut"
  ],
  "required_quantities": []
}
```

### Panel A

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]

---

> Organización ficticia: separar piezas por pedido, identificar cada paquete y revisar la disponibilidad del material antes de programar el corte. [S5]
```

### Panel B

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "work-1"]
Evidencia para salida: ["proc-1", "work-1"]
Referencias citadas: ["proc-1", "work-1"]

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

---

> Organización ficticia: separar piezas por pedido, identificar cada paquete y revisar la disponibilidad del material antes de programar el corte. [S2]
```

## rag04-natural-12

Categoria: natural; rol autenticado: ADMIN

```text
¿Cómo se prepara un vestido para entregarlo?
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "proc-4"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [
    "quality",
    "approval-before-delivery",
    "delivery-record"
  ],
  "required_step_ids": [
    "step-8",
    "step-9"
  ],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [
    "final-approval-before-delivery"
  ],
  "required_quantities": []
}
```

### Panel A

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4"]

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

### Panel B

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4"]

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

## rag04-natural-13

Categoria: natural; rol autenticado: ADMIN

```text
¿En qué momento se corrigen los ajustes?
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "proc-3"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [
    "fit",
    "correct-before-sewing"
  ],
  "required_step_ids": [
    "step-6"
  ],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [
    "correct-differences-before-sewing"
  ],
  "required_quantities": []
}
```

### Panel A

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-3"]
Evidencia para salida: ["proc-3"]
Referencias citadas: ["proc-3"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S1]
```

### Panel B

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4", "price-1"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4", "price-1"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4", "price-1"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]

---

> Tarifa ficticia para evaluación: arreglo simple Bs 250.00; anticipo 40%; saldo antes de entregar. No describe tarifas reales. [S5]
```

## rag04-natural-14

Categoria: natural; rol autenticado: ADMIN

```text
¿Qué revisamos al terminar el vestido?
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "proc-4"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [
    "quality"
  ],
  "required_step_ids": [
    "step-8"
  ],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [],
  "required_quantities": []
}
```

### Panel A

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

### Panel B

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

## rag04-literal-03

Categoria: literal; rol autenticado: ADMIN

```text
¿Qué exige la guía antes de entregar?
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "proc-4"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [
    "quality",
    "approval-before-delivery"
  ],
  "required_step_ids": [
    "step-8"
  ],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [
    "final-approval-before-delivery"
  ],
  "required_quantities": []
}
```

### Panel A

Estado: failed; ruta: rag; objetivo ejecutado; error: LENY_RAG_CONTEXT_LIMIT
Seleccion por ordinal S1..Sn: []
Evidencia para salida: []
Referencias citadas: []

```text
[Sin respuesta textual]
```

### Panel B

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-4"]
Evidencia para salida: ["proc-4"]
Referencias citadas: ["proc-4"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S1]
```

## rag04-literal-08

Categoria: literal; rol autenticado: ADMIN

```text
Lee las instrucciones para organizar el taller
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "work-1"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [
    "separate-order",
    "identify-package",
    "material-before-cut"
  ],
  "required_step_ids": [],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [
    "material-before-cut"
  ],
  "required_quantities": []
}
```

### Panel A

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]

---

> Organización ficticia: separar piezas por pedido, identificar cada paquete y revisar la disponibilidad del material antes de programar el corte. [S5]
```

### Panel B

Estado: failed; ruta: rag; objetivo ejecutado; error: LENY_RAG_CONTEXT_LIMIT
Seleccion por ordinal S1..Sn: []
Evidencia para salida: []
Referencias citadas: []

```text
[Sin respuesta textual]
```

## rag04-synonyms-07

Categoria: synonyms; rol autenticado: ADMIN

```text
¿Cuándo se hacen los retoques?
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "proc-3"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [
    "fit",
    "correct-before-sewing"
  ],
  "required_step_ids": [
    "step-6"
  ],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [
    "correct-differences-before-sewing"
  ],
  "required_quantities": []
}
```

### Panel A

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["price-1"]
Evidencia para salida: ["price-1"]
Referencias citadas: ["price-1"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Tarifa ficticia para evaluación: arreglo simple Bs 250.00; anticipo 40%; saldo antes de entregar. No describe tarifas reales. [S1]
```

### Panel B

Estado: completed; ruta: no_evidence; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: []
Evidencia para salida: []
Referencias citadas: []

```text
No encontré información documental disponible para tu consulta. Puedes precisar la pregunta o solicitar al administrador que revise la documentación publicada.
```

## rag04-synonyms-10

Categoria: synonyms; rol autenticado: ADMIN

```text
¿Qué umbral de reposición usa la guía?
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "stock-1"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [
    "minimum-8"
  ],
  "required_step_ids": [],
  "required_numbers": [
    "8"
  ],
  "requires_capability_ack": false,
  "required_condition_ids": [],
  "required_quantities": [
    {
      "value": "8",
      "unit": "units",
      "meaning": "minimum-stock"
    }
  ]
}
```

### Panel A

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["conflict-2", "conflict-1"]
Evidencia para salida: ["conflict-2", "conflict-1"]
Referencias citadas: ["conflict-2", "conflict-1"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Circular ficticia B, vigente: reserva con anticipo del 50%. Ninguna circular indica prioridad. Debe aclararse la contradicción. [S1]

---

> Circular ficticia A, vigente: reserva con anticipo del 30%. Ninguna circular indica prioridad. [S2]
```

### Panel B

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["stock-1"]
Evidencia para salida: ["stock-1"]
Referencias citadas: ["stock-1"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Regla ficticia: contar unidades físicamente; mínimo 8 unidades; registrar diferencias con su motivo. No modificar existencias por conversación. [S1]
```

## rag04-synonyms-11

Categoria: synonyms; rol autenticado: ADMIN

```text
¿Cómo agrupamos las piezas de una orden?
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "work-1"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [
    "separate-order",
    "identify-package"
  ],
  "required_step_ids": [],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [],
  "required_quantities": []
}
```

### Panel A

Estado: failed; ruta: rag; objetivo ejecutado; error: LENY_RAG_CONTEXT_LIMIT
Seleccion por ordinal S1..Sn: []
Evidencia para salida: []
Referencias citadas: []

```text
[Sin respuesta textual]
```

### Panel B

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["work-1", "proc-1", "proc-2"]
Evidencia para salida: ["work-1", "proc-1", "proc-2"]
Referencias citadas: ["work-1", "proc-1", "proc-2"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Organización ficticia: separar piezas por pedido, identificar cada paquete y revisar la disponibilidad del material antes de programar el corte. [S1]

---

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S2]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S3]
```

## rag04-followup-01

Categoria: followup; rol autenticado: ADMIN

```text
¿Y después?
```

Preguntas previas:
```text
["¿Cómo se confirma el diseño y se toman medidas para el vestido?"]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "proc-1"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [
    "pattern"
  ],
  "required_step_ids": [
    "step-3"
  ],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [
    "pattern-before-cut"
  ],
  "required_quantities": []
}
```

### Panel A

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4"]
Referencias citadas: ["proc-1"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

El siguiente punto numerado de la guía es:

3. Trazar el patrón antes del corte. [S1]
```

### Panel B

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4"]
Referencias citadas: ["proc-1"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

El siguiente punto numerado de la guía es:

3. Trazar el patrón antes del corte. [S1]
```

## rag04-followup-02

Categoria: followup; rol autenticado: ADMIN

```text
Explícame la siguiente etapa
```

Preguntas previas:
```text
["¿Cómo se confirma el diseño y se toman medidas para el vestido?"]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "proc-1"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [
    "pattern"
  ],
  "required_step_ids": [
    "step-3"
  ],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [
    "pattern-before-cut"
  ],
  "required_quantities": []
}
```

### Panel A

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4"]
Referencias citadas: ["proc-1"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

El siguiente punto numerado de la guía es:

3. Trazar el patrón antes del corte. [S1]
```

### Panel B

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4"]
Referencias citadas: ["proc-1"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

El siguiente punto numerado de la guía es:

3. Trazar el patrón antes del corte. [S1]
```

## rag04-followup-03

Categoria: followup; rol autenticado: ADMIN

```text
Resúmelo en cinco pasos
```

Preguntas previas:
```text
["¿Cómo se hacen los vestidos?"]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [
    "design",
    "measure",
    "pattern",
    "cut",
    "baste",
    "fit",
    "correct-before-sewing",
    "sew",
    "quality",
    "approval-before-delivery",
    "delivery-record"
  ],
  "required_step_ids": [
    "step-1",
    "step-2",
    "step-3",
    "step-4",
    "step-5",
    "step-6",
    "step-7",
    "step-8",
    "step-9"
  ],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [
    "approved-design",
    "measurement-consent",
    "pattern-before-cut",
    "identified-order-fabric",
    "correct-differences-before-sewing",
    "sew-approved-pieces",
    "final-approval-before-delivery"
  ],
  "required_quantities": []
}
```

### Panel A

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4"]

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

**Grupo 1**

> Documento ficticio de evaluación. [S1]

> 1. Confirmar el diseño aprobado. [S1]

**Grupo 2**

> 2. Tomar medidas con consentimiento. [S1]

> 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. [S2]

**Grupo 3**

> 4. Cortar únicamente la tela del pedido identificado. [S2]

> 5. Hilvanar las piezas para la primera prueba. [S2]

**Grupo 4**

> Documento ficticio de evaluación. [S3]

> 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. [S3]

> 7. Coser las piezas aprobadas. [S3]

**Grupo 5**

> Documento ficticio de evaluación. [S4]

> 8. Revisar costuras, limpieza y cierre. [S4]

> 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

### Panel B

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4"]

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

**Grupo 1**

> Documento ficticio de evaluación. [S1]

> 1. Confirmar el diseño aprobado. [S1]

**Grupo 2**

> 2. Tomar medidas con consentimiento. [S1]

> 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. [S2]

**Grupo 3**

> 4. Cortar únicamente la tela del pedido identificado. [S2]

> 5. Hilvanar las piezas para la primera prueba. [S2]

**Grupo 4**

> Documento ficticio de evaluación. [S3]

> 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. [S3]

> 7. Coser las piezas aprobadas. [S3]

**Grupo 5**

> Documento ficticio de evaluación. [S4]

> 8. Revisar costuras, limpieza y cierre. [S4]

> 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

## rag04-followup-04

Categoria: followup; rol autenticado: ADMIN

```text
¿Qué ocurre antes de entregarlo?
```

Preguntas previas:
```text
["¿Cómo se hacen los vestidos?"]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "proc-4"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [
    "quality",
    "approval-before-delivery"
  ],
  "required_step_ids": [
    "step-8"
  ],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [
    "final-approval-before-delivery"
  ],
  "required_quantities": []
}
```

### Panel A

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]

---

> Organización ficticia: separar piezas por pedido, identificar cada paquete y revisar la disponibilidad del material antes de programar el corte. [S5]
```

### Panel B

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

## rag04-followup-05

Categoria: followup; rol autenticado: ADMIN

```text
¿Y si hay diferencias en la prueba?
```

Preguntas previas:
```text
["¿Cómo se hacen los vestidos?"]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "proc-3"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [
    "correct-before-sewing"
  ],
  "required_step_ids": [
    "step-6"
  ],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [
    "correct-differences-before-sewing"
  ],
  "required_quantities": []
}
```

### Panel A

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

### Panel B

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4"]

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

## rag04-followup-06

Categoria: followup; rol autenticado: ADMIN

```text
Continúa con ese procedimiento
```

Preguntas previas:
```text
["Explica el proceso del vestido hasta el trazado del patrón"]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "proc-2"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [
    "cut",
    "baste"
  ],
  "required_step_ids": [
    "step-4",
    "step-5"
  ],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [
    "identified-order-fabric"
  ],
  "required_quantities": []
}
```

### Panel A

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4"]
Referencias citadas: ["proc-2", "proc-3", "proc-4"]

```text
Continuación literal de los puntos numerados de la guía:

4. Cortar únicamente la tela del pedido identificado. [S2]

5. Hilvanar las piezas para la primera prueba. [S2]

6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. [S3]

7. Coser las piezas aprobadas. [S3]

8. Revisar costuras, limpieza y cierre. [S4]

9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

### Panel B

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4"]
Referencias citadas: ["proc-2", "proc-3", "proc-4"]

```text
Continuación literal de los puntos numerados de la guía:

4. Cortar únicamente la tela del pedido identificado. [S2]

5. Hilvanar las piezas para la primera prueba. [S2]

6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. [S3]

7. Coser las piezas aprobadas. [S3]

8. Revisar costuras, limpieza y cierre. [S4]

9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

## rag04-followup-07

Categoria: followup; rol autenticado: MODISTA

```text
¿Sigue siendo válido después del cambio de permisos?
```

Preguntas previas:
```text
["Explícame la tarifa de arreglos"]
```

Cambio de estado:
```text
"change_role"
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "no_evidence",
  "relevant_fragment_ids": [],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "work-1",
    "sec-1"
  ],
  "required_fact_ids": [],
  "required_step_ids": [],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [],
  "required_quantities": []
}
```

### Panel A

Estado: completed; ruta: no_evidence; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: []
Evidencia para salida: []
Referencias citadas: []

```text
No encontré información documental disponible para tu consulta. Puedes precisar la pregunta o solicitar al administrador que revise la documentación publicada.
```

### Panel B

Estado: completed; ruta: ambiguous; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: []
Evidencia para salida: []
Referencias citadas: []

```text
¿Puedes precisar cómo se relaciona tu consulta con las actividades de BELLAARTE BOUTIQUE? Así podré orientarte con el contexto adecuado.
```

## rag04-multi_conflict-01

Categoria: multi_conflict; rol autenticado: ADMIN

```text
Resume el procedimiento completo y sus condiciones
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [
    "design",
    "measure",
    "pattern",
    "cut",
    "baste",
    "fit",
    "correct-before-sewing",
    "sew",
    "quality",
    "approval-before-delivery",
    "delivery-record"
  ],
  "required_step_ids": [
    "step-1",
    "step-2",
    "step-3",
    "step-4",
    "step-5",
    "step-6",
    "step-7",
    "step-8",
    "step-9"
  ],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [
    "approved-design",
    "measurement-consent",
    "pattern-before-cut",
    "identified-order-fabric",
    "correct-differences-before-sewing",
    "sew-approved-pieces",
    "final-approval-before-delivery"
  ],
  "required_quantities": []
}
```

### Panel A

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4"]

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

### Panel B

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

## rag04-multi_conflict-02

Categoria: multi_conflict; rol autenticado: ADMIN

```text
Compara las dos circulares de anticipo
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "conflict-1",
    "conflict-2"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [
    "advance-30",
    "advance-50",
    "unresolved-conflict"
  ],
  "required_step_ids": [],
  "required_numbers": [
    "30%",
    "50%"
  ],
  "requires_capability_ack": false,
  "required_condition_ids": [
    "no-circular-priority"
  ],
  "required_quantities": [
    {
      "value": "30",
      "unit": "percent",
      "meaning": "circular-A-advance"
    },
    {
      "value": "50",
      "unit": "percent",
      "meaning": "circular-B-advance"
    }
  ]
}
```

### Panel A

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["conflict-2", "conflict-1"]
Evidencia para salida: ["conflict-2", "conflict-1"]
Referencias citadas: ["conflict-2", "conflict-1"]

```text
Se muestran las fuentes por separado; no se establece prioridad entre ellas.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Circular ficticia B, vigente: reserva con anticipo del 50%. Ninguna circular indica prioridad. Debe aclararse la contradicción. [S1]

---

> Circular ficticia A, vigente: reserva con anticipo del 30%. Ninguna circular indica prioridad. [S2]
```

### Panel B

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["conflict-2", "conflict-1"]
Evidencia para salida: ["conflict-2", "conflict-1"]
Referencias citadas: ["conflict-2", "conflict-1"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Circular ficticia B, vigente: reserva con anticipo del 50%. Ninguna circular indica prioridad. Debe aclararse la contradicción. [S1]

---

> Circular ficticia A, vigente: reserva con anticipo del 30%. Ninguna circular indica prioridad. [S2]
```

## rag04-multi_conflict-03

Categoria: multi_conflict; rol autenticado: ADMIN

```text
¿Qué anticipo puedo asegurar si ambas circulares están vigentes?
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "conflict-1",
    "conflict-2"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [
    "advance-30",
    "advance-50",
    "unresolved-conflict"
  ],
  "required_step_ids": [],
  "required_numbers": [
    "30%",
    "50%"
  ],
  "requires_capability_ack": false,
  "required_condition_ids": [
    "no-circular-priority"
  ],
  "required_quantities": [
    {
      "value": "30",
      "unit": "percent",
      "meaning": "circular-A-advance"
    },
    {
      "value": "50",
      "unit": "percent",
      "meaning": "circular-B-advance"
    }
  ]
}
```

### Panel A

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["conflict-2", "conflict-1", "price-1"]
Evidencia para salida: ["conflict-2", "conflict-1", "price-1"]
Referencias citadas: ["conflict-2", "conflict-1", "price-1"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Circular ficticia B, vigente: reserva con anticipo del 50%. Ninguna circular indica prioridad. Debe aclararse la contradicción. [S1]

---

> Circular ficticia A, vigente: reserva con anticipo del 30%. Ninguna circular indica prioridad. [S2]

---

> Tarifa ficticia para evaluación: arreglo simple Bs 250.00; anticipo 40%; saldo antes de entregar. No describe tarifas reales. [S3]
```

### Panel B

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["conflict-2", "conflict-1"]
Evidencia para salida: ["conflict-2", "conflict-1"]
Referencias citadas: ["conflict-2", "conflict-1"]

```text
Se muestran las fuentes por separado; no se establece prioridad entre ellas.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Circular ficticia B, vigente: reserva con anticipo del 50%. Ninguna circular indica prioridad. Debe aclararse la contradicción. [S1]

---

> Circular ficticia A, vigente: reserva con anticipo del 30%. Ninguna circular indica prioridad. [S2]
```

## rag04-multi_conflict-04

Categoria: multi_conflict; rol autenticado: ADMIN

```text
Relaciona el control de calidad y la aprobación final
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "proc-4"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [
    "quality",
    "approval-before-delivery"
  ],
  "required_step_ids": [
    "step-8"
  ],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [
    "final-approval-before-delivery"
  ],
  "required_quantities": []
}
```

### Panel A

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

### Panel B

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

## rag04-multi_conflict-05

Categoria: multi_conflict; rol autenticado: ADMIN

```text
¿Cómo se conectan el patrón, el corte y la prueba?
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [
    "pattern",
    "cut",
    "baste",
    "fit"
  ],
  "required_step_ids": [
    "step-3",
    "step-4",
    "step-5",
    "step-6"
  ],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [
    "pattern-before-cut",
    "identified-order-fabric"
  ],
  "required_quantities": []
}
```

### Panel A

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3"]
Referencias citadas: ["proc-1", "proc-2", "proc-3"]

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]
```

### Panel B

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4"]

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

## rag04-multi_conflict-06

Categoria: multi_conflict; rol autenticado: ADMIN

```text
¿Puedo omitir una condición al resumir el procedimiento?
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "proc-3",
    "proc-4"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [
    "correct-before-sewing",
    "approval-before-delivery"
  ],
  "required_step_ids": [],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [
    "correct-differences-before-sewing",
    "final-approval-before-delivery"
  ],
  "required_quantities": []
}
```

### Panel A

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["conflict-2", "work-1", "conflict-1"]
Evidencia para salida: ["conflict-2", "work-1", "conflict-1"]
Referencias citadas: ["conflict-2", "work-1", "conflict-1"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Circular ficticia B, vigente: reserva con anticipo del 50%. Ninguna circular indica prioridad. Debe aclararse la contradicción. [S1]

---

> Organización ficticia: separar piezas por pedido, identificar cada paquete y revisar la disponibilidad del material antes de programar el corte. [S2]

---

> Circular ficticia A, vigente: reserva con anticipo del 30%. Ninguna circular indica prioridad. [S3]
```

### Panel B

Estado: completed; ruta: no_evidence; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: []
Evidencia para salida: []
Referencias citadas: []

```text
No encontré información documental disponible para tu consulta. Puedes precisar la pregunta o solicitar al administrador que revise la documentación publicada.
```

## rag04-multi_conflict-07

Categoria: multi_conflict; rol autenticado: ADMIN

```text
Describe el proceso utilizando varios fragmentos
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [
    "design",
    "measure",
    "pattern",
    "cut",
    "baste",
    "fit",
    "correct-before-sewing",
    "sew",
    "quality",
    "approval-before-delivery",
    "delivery-record"
  ],
  "required_step_ids": [
    "step-1",
    "step-2",
    "step-3",
    "step-4",
    "step-5",
    "step-6",
    "step-7",
    "step-8",
    "step-9"
  ],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [
    "approved-design",
    "measurement-consent",
    "pattern-before-cut",
    "identified-order-fabric",
    "correct-differences-before-sewing",
    "sew-approved-pieces",
    "final-approval-before-delivery"
  ],
  "required_quantities": []
}
```

### Panel A

Estado: completed; ruta: ambiguous; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: []
Evidencia para salida: []
Referencias citadas: []

```text
¿Puedes precisar cómo se relaciona tu consulta con las actividades de BELLAARTE BOUTIQUE? Así podré orientarte con el contexto adecuado.
```

### Panel B

Estado: completed; ruta: ambiguous; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: []
Evidencia para salida: []
Referencias citadas: []

```text
¿Puedes precisar cómo se relaciona tu consulta con las actividades de BELLAARTE BOUTIQUE? Así podré orientarte con el contexto adecuado.
```

## rag04-formats-05

Categoria: formats; rol autenticado: ADMIN

```text
Explica la tarifa con cifras exactas y cita la fuente
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "price-1"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [
    "price-250",
    "advance-40",
    "balance-before-delivery"
  ],
  "required_step_ids": [],
  "required_numbers": [
    "250.00",
    "40%"
  ],
  "requires_capability_ack": false,
  "required_condition_ids": [
    "balance-before-delivery"
  ],
  "required_quantities": [
    {
      "value": "250.00",
      "unit": "BOB",
      "meaning": "simple-alteration-price"
    },
    {
      "value": "40",
      "unit": "percent",
      "meaning": "advance-of-price"
    }
  ]
}
```

### Panel A

Estado: completed; ruta: no_evidence; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: []
Evidencia para salida: []
Referencias citadas: []

```text
No encontré información documental disponible para tu consulta. Puedes precisar la pregunta o solicitar al administrador que revise la documentación publicada.
```

### Panel B

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["conflict-1"]
Evidencia para salida: ["conflict-1"]
Referencias citadas: ["conflict-1"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Circular ficticia A, vigente: reserva con anticipo del 30%. Ninguna circular indica prioridad. [S1]
```

## rag04-formats-06

Categoria: formats; rol autenticado: ADMIN

```text
Resume las reglas de inventario en dos viñetas
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "stock-1"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [
    "physical-count",
    "minimum-8",
    "difference-reason"
  ],
  "required_step_ids": [],
  "required_numbers": [
    "8"
  ],
  "requires_capability_ack": false,
  "required_condition_ids": [
    "difference-with-reason",
    "no-conversational-stock-write"
  ],
  "required_quantities": [
    {
      "value": "8",
      "unit": "units",
      "meaning": "minimum-stock"
    }
  ]
}
```

### Panel A

Estado: failed; ruta: rag; objetivo ejecutado; error: LENY_RAG_CONTEXT_LIMIT
Seleccion por ordinal S1..Sn: []
Evidencia para salida: []
Referencias citadas: []

```text
[Sin respuesta textual]
```

### Panel B

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["stock-1"]
Evidencia para salida: ["stock-1"]
Referencias citadas: ["stock-1"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Regla ficticia: contar unidades físicamente; mínimo 8 unidades; registrar diferencias con su motivo. No modificar existencias por conversación. [S1]
```

## rag04-acl-01

Categoria: acl; rol autenticado: CAJA

```text
Consulta la tarifa como CAJA
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "price-1"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [
    "price-250",
    "advance-40",
    "balance-before-delivery"
  ],
  "required_step_ids": [],
  "required_numbers": [
    "250.00",
    "40%"
  ],
  "requires_capability_ack": false,
  "required_condition_ids": [
    "balance-before-delivery"
  ],
  "required_quantities": [
    {
      "value": "250.00",
      "unit": "BOB",
      "meaning": "simple-alteration-price"
    },
    {
      "value": "40",
      "unit": "percent",
      "meaning": "advance-of-price"
    }
  ]
}
```

### Panel A

Estado: completed; ruta: no_evidence; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: []
Evidencia para salida: []
Referencias citadas: []

```text
No encontré información documental disponible para tu consulta. Puedes precisar la pregunta o solicitar al administrador que revise la documentación publicada.
```

### Panel B

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["price-1", "conflict-2", "conflict-1"]
Evidencia para salida: ["price-1", "conflict-2", "conflict-1"]
Referencias citadas: ["price-1", "conflict-2", "conflict-1"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Tarifa ficticia para evaluación: arreglo simple Bs 250.00; anticipo 40%; saldo antes de entregar. No describe tarifas reales. [S1]

---

> Circular ficticia B, vigente: reserva con anticipo del 50%. Ninguna circular indica prioridad. Debe aclararse la contradicción. [S2]

---

> Circular ficticia A, vigente: reserva con anticipo del 30%. Ninguna circular indica prioridad. [S3]
```

## rag04-acl-02

Categoria: acl; rol autenticado: MODISTA

```text
Consulta la tarifa como MODISTA
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "no_evidence",
  "relevant_fragment_ids": [],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "work-1",
    "sec-1"
  ],
  "required_fact_ids": [],
  "required_step_ids": [],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [],
  "required_quantities": []
}
```

### Panel A

Estado: completed; ruta: no_evidence; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: []
Evidencia para salida: []
Referencias citadas: []

```text
No encontré información documental disponible para tu consulta. Puedes precisar la pregunta o solicitar al administrador que revise la documentación publicada.
```

### Panel B

Estado: completed; ruta: no_evidence; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: []
Evidencia para salida: []
Referencias citadas: []

```text
No encontré información documental disponible para tu consulta. Puedes precisar la pregunta o solicitar al administrador que revise la documentación publicada.
```

## rag04-acl-03

Categoria: acl; rol autenticado: INV_BOUTIQUE

```text
Consulta inventario como INV_BOUTIQUE
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "stock-1"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "stock-1",
    "sec-1"
  ],
  "required_fact_ids": [
    "physical-count",
    "minimum-8",
    "difference-reason"
  ],
  "required_step_ids": [],
  "required_numbers": [
    "8"
  ],
  "requires_capability_ack": false,
  "required_condition_ids": [
    "difference-with-reason",
    "no-conversational-stock-write"
  ],
  "required_quantities": [
    {
      "value": "8",
      "unit": "units",
      "meaning": "minimum-stock"
    }
  ]
}
```

### Panel A

Estado: completed; ruta: no_evidence; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: []
Evidencia para salida: []
Referencias citadas: []

```text
No encontré información documental disponible para tu consulta. Puedes precisar la pregunta o solicitar al administrador que revise la documentación publicada.
```

### Panel B

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["stock-1"]
Evidencia para salida: ["stock-1"]
Referencias citadas: ["stock-1"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Regla ficticia: contar unidades físicamente; mínimo 8 unidades; registrar diferencias con su motivo. No modificar existencias por conversación. [S1]
```

## rag04-acl-04

Categoria: acl; rol autenticado: CAJA

```text
Consulta inventario como CAJA
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "no_evidence",
  "relevant_fragment_ids": [],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [],
  "required_step_ids": [],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [],
  "required_quantities": []
}
```

### Panel A

Estado: completed; ruta: no_evidence; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: []
Evidencia para salida: []
Referencias citadas: []

```text
No encontré información documental disponible para tu consulta. Puedes precisar la pregunta o solicitar al administrador que revise la documentación publicada.
```

### Panel B

Estado: completed; ruta: no_evidence; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: []
Evidencia para salida: []
Referencias citadas: []

```text
No encontré información documental disponible para tu consulta. Puedes precisar la pregunta o solicitar al administrador que revise la documentación publicada.
```

## rag04-acl-05

Categoria: acl; rol autenticado: MODISTA

```text
Consulta taller como MODISTA
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "work-1"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "work-1",
    "sec-1"
  ],
  "required_fact_ids": [
    "separate-order",
    "identify-package",
    "material-before-cut"
  ],
  "required_step_ids": [],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [
    "material-before-cut"
  ],
  "required_quantities": []
}
```

### Panel A

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]

---

> Organización ficticia: separar piezas por pedido, identificar cada paquete y revisar la disponibilidad del material antes de programar el corte. [S5]
```

### Panel B

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]

---

> Organización ficticia: separar piezas por pedido, identificar cada paquete y revisar la disponibilidad del material antes de programar el corte. [S5]
```

## rag04-acl-06

Categoria: acl; rol autenticado: DOC

```text
Consulta tarifa con el rol DOC
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "forbidden",
  "relevant_fragment_ids": [],
  "authorized_fragment_ids": [],
  "required_fact_ids": [],
  "required_step_ids": [],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [],
  "required_quantities": []
}
```

### Panel A

Estado: failed; ruta: unknown; objetivo NO ejecutado; no valorar texto de prerrequisito como respuesta objetivo; error: preexisting_unauthorized_role_absent
Seleccion por ordinal S1..Sn: []
Evidencia para salida: []
Referencias citadas: []

```text
[Sin respuesta textual]
```

### Panel B

Estado: failed; ruta: unknown; objetivo NO ejecutado; no valorar texto de prerrequisito como respuesta objetivo; error: preexisting_unauthorized_role_absent
Seleccion por ordinal S1..Sn: []
Evidencia para salida: []
Referencias citadas: []

```text
[Sin respuesta textual]
```

## rag04-acl-07

Categoria: acl; rol autenticado: CAJA

```text
Continúa la tarifa después de revocar la ACL
```

Preguntas previas:
```text
["Explícame la tarifa de arreglos"]
```

Cambio de estado:
```text
"revoke_acl"
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "no_evidence",
  "relevant_fragment_ids": [],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [],
  "required_step_ids": [],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [],
  "required_quantities": []
}
```

### Panel A

Estado: completed; ruta: no_evidence; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: []
Evidencia para salida: []
Referencias citadas: []

```text
No encontré información documental disponible para tu consulta. Puedes precisar la pregunta o solicitar al administrador que revise la documentación publicada.
```

### Panel B

Estado: completed; ruta: ambiguous; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: []
Evidencia para salida: []
Referencias citadas: []

```text
¿Puedes precisar cómo se relaciona tu consulta con las actividades de BELLAARTE BOUTIQUE? Así podré orientarte con el contexto adecuado.
```

## rag04-acl-08

Categoria: acl; rol autenticado: ADMIN

```text
Continúa el procedimiento después de retirar su publicación
```

Preguntas previas:
```text
["¿Cómo se hacen los vestidos?"]
```

Cambio de estado:
```text
"withdraw_publication"
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "no_evidence",
  "relevant_fragment_ids": [],
  "authorized_fragment_ids": [
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [],
  "required_step_ids": [],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [],
  "required_quantities": []
}
```

### Panel A

Estado: completed; ruta: no_evidence; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: []
Evidencia para salida: []
Referencias citadas: []

```text
No encontré información documental disponible para tu consulta. Puedes precisar la pregunta o solicitar al administrador que revise la documentación publicada.
```

### Panel B

Estado: completed; ruta: no_evidence; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: []
Evidencia para salida: []
Referencias citadas: []

```text
No encontré información documental disponible para tu consulta. Puedes precisar la pregunta o solicitar al administrador que revise la documentación publicada.
```

## rag04-acl-09

Categoria: acl; rol autenticado: ADMIN

```text
Consulta tarifa como ADMIN
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "price-1"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [
    "price-250",
    "advance-40",
    "balance-before-delivery"
  ],
  "required_step_ids": [],
  "required_numbers": [
    "250.00",
    "40%"
  ],
  "requires_capability_ack": false,
  "required_condition_ids": [
    "balance-before-delivery"
  ],
  "required_quantities": [
    {
      "value": "250.00",
      "unit": "BOB",
      "meaning": "simple-alteration-price"
    },
    {
      "value": "40",
      "unit": "percent",
      "meaning": "advance-of-price"
    }
  ]
}
```

### Panel A

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["price-1", "conflict-1"]
Evidencia para salida: ["price-1", "conflict-1"]
Referencias citadas: ["price-1", "conflict-1"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Tarifa ficticia para evaluación: arreglo simple Bs 250.00; anticipo 40%; saldo antes de entregar. No describe tarifas reales. [S1]

---

> Circular ficticia A, vigente: reserva con anticipo del 30%. Ninguna circular indica prioridad. [S2]
```

### Panel B

Estado: completed; ruta: no_evidence; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: []
Evidencia para salida: []
Referencias citadas: []

```text
No encontré información documental disponible para tu consulta. Puedes precisar la pregunta o solicitar al administrador que revise la documentación publicada.
```

## rag04-acl-10

Categoria: acl; rol autenticado: INV_TALLER

```text
Consulta inventario como INV_TALLER
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "rag",
  "relevant_fragment_ids": [
    "stock-1"
  ],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "stock-1",
    "work-1",
    "sec-1"
  ],
  "required_fact_ids": [
    "physical-count",
    "minimum-8",
    "difference-reason"
  ],
  "required_step_ids": [],
  "required_numbers": [
    "8"
  ],
  "requires_capability_ack": false,
  "required_condition_ids": [
    "difference-with-reason",
    "no-conversational-stock-write"
  ],
  "required_quantities": [
    {
      "value": "8",
      "unit": "units",
      "meaning": "minimum-stock"
    }
  ]
}
```

### Panel A

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["stock-1"]
Evidencia para salida: ["stock-1"]
Referencias citadas: ["stock-1"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Regla ficticia: contar unidades físicamente; mínimo 8 unidades; registrar diferencias con su motivo. No modificar existencias por conversación. [S1]
```

### Panel B

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["work-1"]
Evidencia para salida: ["work-1"]
Referencias citadas: ["work-1"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Organización ficticia: separar piezas por pedido, identificar cada paquete y revisar la disponibilidad del material antes de programar el corte. [S1]
```

## rag04-no_evidence-01

Categoria: no_evidence; rol autenticado: ADMIN

```text
¿Qué procedimiento publicado regula bordados con hilo de oro?
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "no_evidence",
  "relevant_fragment_ids": [],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [],
  "required_step_ids": [],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [],
  "required_quantities": []
}
```

### Panel A

Estado: completed; ruta: no_evidence; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: []
Evidencia para salida: []
Referencias citadas: []

```text
No encontré información documental disponible para tu consulta. Puedes precisar la pregunta o solicitar al administrador que revise la documentación publicada.
```

### Panel B

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["proc-1", "proc-2", "proc-3", "proc-4"]
Evidencia para salida: ["proc-1", "proc-2", "proc-3", "proc-4"]
Referencias citadas: ["proc-1", "proc-2", "proc-3", "proc-4"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

## rag04-no_evidence-02

Categoria: no_evidence; rol autenticado: ADMIN

```text
¿Cuántas pruebas exige un vestido de ceremonia con plumas?
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "no_evidence",
  "relevant_fragment_ids": [],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [],
  "required_step_ids": [],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [],
  "required_quantities": []
}
```

### Panel A

Estado: completed; ruta: no_evidence; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: []
Evidencia para salida: []
Referencias citadas: []

```text
No encontré información documental disponible para tu consulta. Puedes precisar la pregunta o solicitar al administrador que revise la documentación publicada.
```

### Panel B

Estado: completed; ruta: no_evidence; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: []
Evidencia para salida: []
Referencias citadas: []

```text
No encontré información documental disponible para tu consulta. Puedes precisar la pregunta o solicitar al administrador que revise la documentación publicada.
```

## rag04-no_evidence-03

Categoria: no_evidence; rol autenticado: ADMIN

```text
¿Qué plazo exacto publicado tienen los ajustes de encaje?
```

Preguntas previas:
```text
[]
```

Cambio de estado:
```text
null
```

Gold inicial, a contrastar con la evidencia:
```text
{
  "route": "no_evidence",
  "relevant_fragment_ids": [],
  "authorized_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4",
    "price-1",
    "stock-1",
    "work-1",
    "sec-1",
    "conflict-1",
    "conflict-2"
  ],
  "required_fact_ids": [],
  "required_step_ids": [],
  "required_numbers": [],
  "requires_capability_ack": false,
  "required_condition_ids": [],
  "required_quantities": []
}
```

### Panel A

Estado: completed; ruta: rag; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: ["conflict-1"]
Evidencia para salida: ["conflict-1"]
Referencias citadas: ["conflict-1"]

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Circular ficticia A, vigente: reserva con anticipo del 30%. Ninguna circular indica prioridad. [S1]
```

### Panel B

Estado: completed; ruta: no_evidence; objetivo ejecutado; error: None
Seleccion por ordinal S1..Sn: []
Evidencia para salida: []
Referencias citadas: []

```text
No encontré información documental disponible para tu consulta. Puedes precisar la pregunta o solicitar al administrador que revise la documentación publicada.
```

