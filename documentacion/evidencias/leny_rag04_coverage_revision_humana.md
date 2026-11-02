# Revision tecnica/humana pendiente: prototipo de cobertura

Una sola ejecucion offline. Ninguna respuesta nueva de Qwen ni consulta SQL nueva. Las decisiones posteriores son simuladas con borradores, no respuestas emitidas por el ERP. La autoridad estricta permite cero respuestas hasta revisar los manifiestos.

Resultado bloqueante:2/2 criticos rechazados especificamente, pero solo4/14 naturales y12/39 con evidencia;26/38 perdidas nuevas. No promover.

Revisar primero natural-04 (palabra funcional), natural-05/08/09/10/13/14 (variacion linguistica), natural-11 (relacion anterioridad), seguimientos y los dos criticos. Aprobar metadatos no basta para reparar estas perdidas.

Fuentes y vocabulario: [borradores completos](leny_rag04_coverage_manifests_revision.md). Controles: [doce escenarios](leny_rag04_coverage_controls_revision.md). La plantilla esta sin completar.

## rag04-natural-01

Pregunta: ¿Cómo se hacen los vestidos?

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["proc-1", "proc-2", "proc-3", "proc-4"]; retenidos simulados: ["proc-1", "proc-2", "proc-3", "proc-4"].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "approved",
  "reason": "coverage_verified",
  "signature": {
    "topics": [
      "garment"
    ],
    "aspects": [
      "procedure"
    ],
    "qualifiers": [],
    "spans": [
      {
        "concept": "procedure",
        "kind": "aspect",
        "start": 1,
        "end": 5,
        "origin": "current_user"
      },
      {
        "concept": "garment",
        "kind": "topic",
        "start": 19,
        "end": 27,
        "origin": "current_user"
      }
    ],
    "unknown": [],
    "complete": true,
    "compare": false,
    "reason": "coverage_intent_resolved"
  },
  "proposed_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4"
  ],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": [
    "430c6426a758b8cf9a39078a6264e98fcd73c52d8778e1afddcd8e1fb70d3a40",
    "bd49c93e0a711e075e29f5f4e8877f3605eaf4158b11601442dfecb25caff33e"
  ]
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

Valoracion humana: pendiente.

## rag04-natural-02

Pregunta: ¿Cómo confeccionan un vestido?

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["proc-1", "proc-2", "proc-3", "proc-4"]; retenidos simulados: ["proc-1", "proc-2", "proc-3", "proc-4"].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "approved",
  "reason": "coverage_verified",
  "signature": {
    "topics": [
      "garment"
    ],
    "aspects": [
      "procedure"
    ],
    "qualifiers": [],
    "spans": [
      {
        "concept": "procedure",
        "kind": "aspect",
        "start": 1,
        "end": 5,
        "origin": "current_user"
      },
      {
        "concept": "garment",
        "kind": "topic",
        "start": 6,
        "end": 18,
        "origin": "current_user"
      },
      {
        "concept": "garment",
        "kind": "topic",
        "start": 22,
        "end": 29,
        "origin": "current_user"
      }
    ],
    "unknown": [],
    "complete": false,
    "compare": false,
    "reason": "coverage_intent_resolved"
  },
  "proposed_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4"
  ],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": [
    "430c6426a758b8cf9a39078a6264e98fcd73c52d8778e1afddcd8e1fb70d3a40",
    "bd49c93e0a711e075e29f5f4e8877f3605eaf4158b11601442dfecb25caff33e"
  ]
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

Valoracion humana: pendiente.

## rag04-natural-03

Pregunta: Explícame cómo se hace un vestido

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["proc-1", "proc-2", "proc-3", "proc-4"]; retenidos simulados: ["proc-1", "proc-2", "proc-3", "proc-4"].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "approved",
  "reason": "coverage_verified",
  "signature": {
    "topics": [
      "garment"
    ],
    "aspects": [
      "procedure"
    ],
    "qualifiers": [],
    "spans": [
      {
        "concept": "procedure",
        "kind": "aspect",
        "start": 10,
        "end": 14,
        "origin": "current_user"
      },
      {
        "concept": "garment",
        "kind": "topic",
        "start": 26,
        "end": 33,
        "origin": "current_user"
      }
    ],
    "unknown": [],
    "complete": false,
    "compare": false,
    "reason": "coverage_intent_resolved"
  },
  "proposed_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4"
  ],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": [
    "430c6426a758b8cf9a39078a6264e98fcd73c52d8778e1afddcd8e1fb70d3a40",
    "bd49c93e0a711e075e29f5f4e8877f3605eaf4158b11601442dfecb25caff33e"
  ]
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

Valoracion humana: pendiente.

## rag04-natural-04

Pregunta: ¿Cuál es el proceso para hacer vestidos?

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["proc-1", "proc-2", "proc-3", "proc-4"]; retenidos simulados: [].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "uncertain",
  "reason": "coverage_terms_uncertain",
  "signature": {
    "topics": [
      "garment"
    ],
    "aspects": [
      "procedure"
    ],
    "qualifiers": [],
    "spans": [
      {
        "concept": "procedure",
        "kind": "aspect",
        "start": 12,
        "end": 19,
        "origin": "current_user"
      },
      {
        "concept": "garment",
        "kind": "topic",
        "start": 31,
        "end": 39,
        "origin": "current_user"
      }
    ],
    "unknown": [
      {
        "token": "es",
        "start": 6,
        "end": 8
      }
    ],
    "complete": false,
    "compare": false,
    "reason": "coverage_terms_uncertain"
  },
  "proposed_fragment_ids": [],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": []
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

Valoracion humana: pendiente.

## rag04-natural-05

Pregunta: ¿Cómo elaboramos vestidos?

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["proc-1", "proc-2", "proc-3", "proc-4"]; retenidos simulados: [].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "uncertain",
  "reason": "coverage_terms_uncertain",
  "signature": {
    "topics": [
      "garment"
    ],
    "aspects": [
      "procedure"
    ],
    "qualifiers": [],
    "spans": [
      {
        "concept": "procedure",
        "kind": "aspect",
        "start": 1,
        "end": 5,
        "origin": "current_user"
      },
      {
        "concept": "garment",
        "kind": "topic",
        "start": 17,
        "end": 25,
        "origin": "current_user"
      }
    ],
    "unknown": [
      {
        "token": "elaboramos",
        "start": 6,
        "end": 16
      }
    ],
    "complete": false,
    "compare": false,
    "reason": "coverage_terms_uncertain"
  },
  "proposed_fragment_ids": [],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": []
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

Valoracion humana: pendiente.

## rag04-natural-06

Pregunta: ¿Qué pasos lleva confeccionar un vestido?

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["proc-1", "proc-2", "proc-3", "proc-4"]; retenidos simulados: [].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "uncertain",
  "reason": "coverage_terms_uncertain",
  "signature": {
    "topics": [
      "garment"
    ],
    "aspects": [
      "procedure"
    ],
    "qualifiers": [],
    "spans": [
      {
        "concept": "procedure",
        "kind": "aspect",
        "start": 5,
        "end": 10,
        "origin": "current_user"
      },
      {
        "concept": "garment",
        "kind": "topic",
        "start": 17,
        "end": 29,
        "origin": "current_user"
      },
      {
        "concept": "garment",
        "kind": "topic",
        "start": 33,
        "end": 40,
        "origin": "current_user"
      }
    ],
    "unknown": [
      {
        "token": "lleva",
        "start": 11,
        "end": 16
      }
    ],
    "complete": false,
    "compare": false,
    "reason": "coverage_terms_uncertain"
  },
  "proposed_fragment_ids": [],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": []
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

Valoracion humana: pendiente.

## rag04-natural-07

Pregunta: ¿Cómo hacemos una prenda de principio a fin?

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["proc-1", "proc-2", "proc-3", "proc-4"]; retenidos simulados: [].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "uncertain",
  "reason": "coverage_terms_uncertain",
  "signature": {
    "topics": [
      "garment"
    ],
    "aspects": [
      "procedure"
    ],
    "qualifiers": [],
    "spans": [
      {
        "concept": "procedure",
        "kind": "aspect",
        "start": 1,
        "end": 5,
        "origin": "current_user"
      },
      {
        "concept": "garment",
        "kind": "topic",
        "start": 18,
        "end": 24,
        "origin": "current_user"
      }
    ],
    "unknown": [
      {
        "token": "principio",
        "start": 28,
        "end": 37
      },
      {
        "token": "fin",
        "start": 40,
        "end": 43
      }
    ],
    "complete": false,
    "compare": false,
    "reason": "coverage_terms_uncertain"
  },
  "proposed_fragment_ids": [],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": []
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

Valoracion humana: pendiente.

## rag04-natural-08

Pregunta: Necesito entender cómo fabricamos un vestido

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["proc-1", "proc-2", "proc-3", "proc-4"]; retenidos simulados: [].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "uncertain",
  "reason": "coverage_terms_uncertain",
  "signature": {
    "topics": [
      "garment"
    ],
    "aspects": [
      "procedure"
    ],
    "qualifiers": [],
    "spans": [
      {
        "concept": "procedure",
        "kind": "aspect",
        "start": 18,
        "end": 22,
        "origin": "current_user"
      },
      {
        "concept": "garment",
        "kind": "topic",
        "start": 37,
        "end": 44,
        "origin": "current_user"
      }
    ],
    "unknown": [
      {
        "token": "necesito",
        "start": 0,
        "end": 8
      },
      {
        "token": "entender",
        "start": 9,
        "end": 17
      },
      {
        "token": "fabricamos",
        "start": 23,
        "end": 33
      }
    ],
    "complete": false,
    "compare": false,
    "reason": "coverage_terms_uncertain"
  },
  "proposed_fragment_ids": [],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": []
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

Valoracion humana: pendiente.

## rag04-natural-09

Pregunta: ¿Cómo se transforma la tela en un vestido?

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["proc-1", "proc-2", "proc-3", "proc-4"]; retenidos simulados: [].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "uncertain",
  "reason": "coverage_terms_uncertain",
  "signature": {
    "topics": [
      "garment"
    ],
    "aspects": [
      "procedure"
    ],
    "qualifiers": [],
    "spans": [
      {
        "concept": "procedure",
        "kind": "aspect",
        "start": 1,
        "end": 5,
        "origin": "current_user"
      },
      {
        "concept": "garment",
        "kind": "topic",
        "start": 34,
        "end": 41,
        "origin": "current_user"
      }
    ],
    "unknown": [
      {
        "token": "transforma",
        "start": 9,
        "end": 19
      }
    ],
    "complete": false,
    "compare": false,
    "reason": "coverage_terms_uncertain"
  },
  "proposed_fragment_ids": [],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": []
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

Valoracion humana: pendiente.

## rag04-natural-10

Pregunta: Descríbeme el proceso de confección

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["proc-1", "proc-2", "proc-3", "proc-4"]; retenidos simulados: [].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "uncertain",
  "reason": "coverage_terms_uncertain",
  "signature": {
    "topics": [
      "garment"
    ],
    "aspects": [
      "procedure"
    ],
    "qualifiers": [],
    "spans": [
      {
        "concept": "procedure",
        "kind": "aspect",
        "start": 14,
        "end": 21,
        "origin": "current_user"
      },
      {
        "concept": "garment",
        "kind": "topic",
        "start": 25,
        "end": 35,
        "origin": "current_user"
      }
    ],
    "unknown": [
      {
        "token": "describeme",
        "start": 0,
        "end": 10
      }
    ],
    "complete": true,
    "compare": false,
    "reason": "coverage_terms_uncertain"
  },
  "proposed_fragment_ids": [],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": []
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

Valoracion humana: pendiente.

## rag04-natural-11

Pregunta: ¿Qué se hace antes de cortar la tela?

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["proc-1", "work-1"]; retenidos simulados: [].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "not_covered",
  "reason": "coverage_subject_mismatch",
  "signature": {
    "topics": [
      "cutting"
    ],
    "aspects": [
      "timing"
    ],
    "qualifiers": [],
    "spans": [
      {
        "concept": "cutting",
        "kind": "topic",
        "start": 22,
        "end": 36,
        "origin": "current_user"
      },
      {
        "concept": "timing",
        "kind": "aspect",
        "start": 13,
        "end": 18,
        "origin": "current_user"
      }
    ],
    "unknown": [],
    "complete": false,
    "compare": false,
    "reason": "coverage_intent_resolved"
  },
  "proposed_fragment_ids": [],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": []
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

---

> Organización ficticia: separar piezas por pedido, identificar cada paquete y revisar la disponibilidad del material antes de programar el corte. [S2]
```

Valoracion humana: pendiente.

## rag04-natural-12

Pregunta: ¿Cómo se prepara un vestido para entregarlo?

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["proc-1", "proc-2", "proc-3", "proc-4"]; retenidos simulados: ["proc-1", "proc-2", "proc-3", "proc-4"].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "approved",
  "reason": "coverage_verified",
  "signature": {
    "topics": [
      "delivery",
      "garment"
    ],
    "aspects": [
      "procedure"
    ],
    "qualifiers": [],
    "spans": [
      {
        "concept": "procedure",
        "kind": "aspect",
        "start": 1,
        "end": 5,
        "origin": "current_user"
      },
      {
        "concept": "garment",
        "kind": "topic",
        "start": 20,
        "end": 27,
        "origin": "current_user"
      },
      {
        "concept": "delivery",
        "kind": "topic",
        "start": 33,
        "end": 43,
        "origin": "current_user"
      }
    ],
    "unknown": [],
    "complete": false,
    "compare": false,
    "reason": "coverage_intent_resolved"
  },
  "proposed_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4"
  ],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": [
    "430c6426a758b8cf9a39078a6264e98fcd73c52d8778e1afddcd8e1fb70d3a40",
    "bd49c93e0a711e075e29f5f4e8877f3605eaf4158b11601442dfecb25caff33e"
  ]
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

Valoracion humana: pendiente.

## rag04-natural-13

Pregunta: ¿En qué momento se corrigen los ajustes?

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["proc-3"]; retenidos simulados: [].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "uncertain",
  "reason": "coverage_terms_uncertain",
  "signature": {
    "topics": [
      "fitting"
    ],
    "aspects": [
      "timing"
    ],
    "qualifiers": [],
    "spans": [
      {
        "concept": "timing",
        "kind": "aspect",
        "start": 8,
        "end": 15,
        "origin": "current_user"
      },
      {
        "concept": "fitting",
        "kind": "topic",
        "start": 32,
        "end": 39,
        "origin": "current_user"
      }
    ],
    "unknown": [
      {
        "token": "corrigen",
        "start": 19,
        "end": 27
      }
    ],
    "complete": false,
    "compare": false,
    "reason": "coverage_terms_uncertain"
  },
  "proposed_fragment_ids": [],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": []
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S1]
```

Valoracion humana: pendiente.

## rag04-natural-14

Pregunta: ¿Qué revisamos al terminar el vestido?

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["proc-4"]; retenidos simulados: [].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "uncertain",
  "reason": "coverage_terms_uncertain",
  "signature": {
    "topics": [
      "garment"
    ],
    "aspects": [],
    "qualifiers": [],
    "spans": [
      {
        "concept": "garment",
        "kind": "topic",
        "start": 30,
        "end": 37,
        "origin": "current_user"
      }
    ],
    "unknown": [
      {
        "token": "revisamos",
        "start": 5,
        "end": 14
      },
      {
        "token": "terminar",
        "start": 18,
        "end": 26
      }
    ],
    "complete": false,
    "compare": false,
    "reason": "coverage_terms_uncertain"
  },
  "proposed_fragment_ids": [],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": []
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S1]
```

Valoracion humana: pendiente.

## rag04-literal-03

Pregunta: ¿Qué exige la guía antes de entregar?

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["proc-4"]; retenidos simulados: [].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "uncertain",
  "reason": "coverage_terms_uncertain",
  "signature": {
    "topics": [
      "delivery"
    ],
    "aspects": [
      "timing"
    ],
    "qualifiers": [],
    "spans": [
      {
        "concept": "timing",
        "kind": "aspect",
        "start": 19,
        "end": 24,
        "origin": "current_user"
      },
      {
        "concept": "delivery",
        "kind": "topic",
        "start": 28,
        "end": 36,
        "origin": "current_user"
      }
    ],
    "unknown": [
      {
        "token": "exige",
        "start": 5,
        "end": 10
      }
    ],
    "complete": false,
    "compare": false,
    "reason": "coverage_terms_uncertain"
  },
  "proposed_fragment_ids": [],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": []
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S1]
```

Valoracion humana: pendiente.

## rag04-literal-08

Pregunta: Lee las instrucciones para organizar el taller

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1"]; retenidos simulados: [].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "uncertain",
  "reason": "coverage_terms_uncertain",
  "signature": {
    "topics": [
      "workshop"
    ],
    "aspects": [],
    "qualifiers": [],
    "spans": [
      {
        "concept": "workshop",
        "kind": "topic",
        "start": 27,
        "end": 46,
        "origin": "current_user"
      }
    ],
    "unknown": [
      {
        "token": "lee",
        "start": 0,
        "end": 3
      },
      {
        "token": "instrucciones",
        "start": 8,
        "end": 21
      }
    ],
    "complete": false,
    "compare": false,
    "reason": "coverage_terms_uncertain"
  },
  "proposed_fragment_ids": [],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": []
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]

---

> Organización ficticia: separar piezas por pedido, identificar cada paquete y revisar la disponibilidad del material antes de programar el corte. [S5]
```

Valoracion humana: pendiente.

## rag04-synonyms-07

Pregunta: ¿Cuándo se hacen los retoques?

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["proc-3"]; retenidos simulados: ["proc-3"].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "approved",
  "reason": "coverage_verified",
  "signature": {
    "topics": [
      "fitting"
    ],
    "aspects": [
      "timing"
    ],
    "qualifiers": [],
    "spans": [
      {
        "concept": "timing",
        "kind": "aspect",
        "start": 1,
        "end": 7,
        "origin": "current_user"
      },
      {
        "concept": "fitting",
        "kind": "topic",
        "start": 21,
        "end": 29,
        "origin": "current_user"
      }
    ],
    "unknown": [],
    "complete": false,
    "compare": false,
    "reason": "coverage_intent_resolved"
  },
  "proposed_fragment_ids": [
    "proc-3"
  ],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": [
    "430c6426a758b8cf9a39078a6264e98fcd73c52d8778e1afddcd8e1fb70d3a40",
    "bd49c93e0a711e075e29f5f4e8877f3605eaf4158b11601442dfecb25caff33e"
  ]
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S1]
```

Valoracion humana: pendiente.

## rag04-synonyms-10

Pregunta: ¿Qué umbral de reposición usa la guía?

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["stock-1"]; retenidos simulados: ["stock-1"].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "approved",
  "reason": "coverage_verified",
  "signature": {
    "topics": [
      "inventory"
    ],
    "aspects": [],
    "qualifiers": [],
    "spans": [
      {
        "concept": "inventory",
        "kind": "topic",
        "start": 5,
        "end": 25,
        "origin": "current_user"
      }
    ],
    "unknown": [],
    "complete": false,
    "compare": false,
    "reason": "coverage_intent_resolved"
  },
  "proposed_fragment_ids": [
    "stock-1"
  ],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": [
    "67a8cf5b252e9fabd9c4f5649615cdc15667783acac6031d530093447e152a5d",
    "bd49c93e0a711e075e29f5f4e8877f3605eaf4158b11601442dfecb25caff33e"
  ]
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Regla ficticia: contar unidades físicamente; mínimo 8 unidades; registrar diferencias con su motivo. No modificar existencias por conversación. [S1]
```

Valoracion humana: pendiente.

## rag04-synonyms-11

Pregunta: ¿Cómo agrupamos las piezas de una orden?

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["work-1", "proc-1"]; retenidos simulados: [].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "uncertain",
  "reason": "coverage_terms_uncertain",
  "signature": {
    "topics": [],
    "aspects": [
      "procedure"
    ],
    "qualifiers": [],
    "spans": [
      {
        "concept": "procedure",
        "kind": "aspect",
        "start": 1,
        "end": 5,
        "origin": "current_user"
      }
    ],
    "unknown": [
      {
        "token": "agrupamos",
        "start": 6,
        "end": 15
      },
      {
        "token": "orden",
        "start": 34,
        "end": 39
      }
    ],
    "complete": false,
    "compare": false,
    "reason": "coverage_terms_uncertain"
  },
  "proposed_fragment_ids": [],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": []
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Organización ficticia: separar piezas por pedido, identificar cada paquete y revisar la disponibilidad del material antes de programar el corte. [S1]

---

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S2]
```

Valoracion humana: pendiente.

## rag04-followup-01

Pregunta: ¿Y después?

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["proc-1", "proc-2", "proc-3", "proc-4"]; retenidos simulados: [].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "uncertain",
  "reason": "coverage_anchor_uncertain",
  "signature": {
    "topics": [],
    "aspects": [],
    "qualifiers": [],
    "spans": [],
    "unknown": [],
    "complete": false,
    "compare": false,
    "reason": "coverage_anchor_uncertain"
  },
  "proposed_fragment_ids": [],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": []
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
El siguiente punto numerado de la guía es:

3. Trazar el patrón antes del corte. [S1]
```

Valoracion humana: pendiente.

## rag04-followup-02

Pregunta: Explícame la siguiente etapa

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["proc-1", "proc-2", "proc-3", "proc-4"]; retenidos simulados: [].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "uncertain",
  "reason": "coverage_anchor_uncertain",
  "signature": {
    "topics": [],
    "aspects": [],
    "qualifiers": [],
    "spans": [],
    "unknown": [],
    "complete": false,
    "compare": false,
    "reason": "coverage_anchor_uncertain"
  },
  "proposed_fragment_ids": [],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": []
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
El siguiente punto numerado de la guía es:

3. Trazar el patrón antes del corte. [S1]
```

Valoracion humana: pendiente.

## rag04-followup-03

Pregunta: Resúmelo en cinco pasos

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["proc-1", "proc-2", "proc-3", "proc-4"]; retenidos simulados: ["proc-1", "proc-2", "proc-3", "proc-4"].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "approved",
  "reason": "coverage_verified",
  "signature": {
    "topics": [
      "garment"
    ],
    "aspects": [
      "procedure"
    ],
    "qualifiers": [],
    "spans": [
      {
        "concept": "procedure",
        "kind": "aspect",
        "start": 1,
        "end": 5,
        "origin": "user_topic"
      },
      {
        "concept": "garment",
        "kind": "topic",
        "start": 19,
        "end": 27,
        "origin": "user_topic"
      }
    ],
    "unknown": [],
    "complete": true,
    "compare": false,
    "reason": "coverage_intent_resolved"
  },
  "proposed_fragment_ids": [
    "proc-1",
    "proc-2",
    "proc-3",
    "proc-4"
  ],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": [
    "430c6426a758b8cf9a39078a6264e98fcd73c52d8778e1afddcd8e1fb70d3a40",
    "bd49c93e0a711e075e29f5f4e8877f3605eaf4158b11601442dfecb25caff33e"
  ]
}
```

Respuesta baseline sintetica (historica, no regenerada):

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

Valoracion humana: pendiente.

## rag04-followup-04

Pregunta: ¿Qué ocurre antes de entregarlo?

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["proc-1", "proc-2", "proc-3", "proc-4"]; retenidos simulados: [].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "uncertain",
  "reason": "coverage_terms_uncertain",
  "signature": {
    "topics": [
      "delivery"
    ],
    "aspects": [
      "timing"
    ],
    "qualifiers": [],
    "spans": [
      {
        "concept": "timing",
        "kind": "aspect",
        "start": 12,
        "end": 17,
        "origin": "current_user"
      },
      {
        "concept": "delivery",
        "kind": "topic",
        "start": 21,
        "end": 31,
        "origin": "current_user"
      }
    ],
    "unknown": [
      {
        "token": "ocurre",
        "start": 5,
        "end": 11
      }
    ],
    "complete": false,
    "compare": false,
    "reason": "coverage_terms_uncertain"
  },
  "proposed_fragment_ids": [],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": []
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

Valoracion humana: pendiente.

## rag04-followup-05

Pregunta: ¿Y si hay diferencias en la prueba?

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["proc-1", "proc-2", "proc-3", "proc-4"]; retenidos simulados: [].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "uncertain",
  "reason": "coverage_logic_uncertain",
  "signature": {
    "topics": [
      "fitting"
    ],
    "aspects": [],
    "qualifiers": [],
    "spans": [
      {
        "concept": "fitting",
        "kind": "topic",
        "start": 28,
        "end": 34,
        "origin": "current_user"
      }
    ],
    "unknown": [
      {
        "token": "si",
        "start": 3,
        "end": 5
      }
    ],
    "complete": false,
    "compare": false,
    "reason": "coverage_logic_uncertain"
  },
  "proposed_fragment_ids": [],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": []
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

Valoracion humana: pendiente.

## rag04-followup-06

Pregunta: Continúa con ese procedimiento

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["proc-1", "proc-2", "proc-3", "proc-4"]; retenidos simulados: [].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "uncertain",
  "reason": "coverage_anchor_uncertain",
  "signature": {
    "topics": [],
    "aspects": [],
    "qualifiers": [],
    "spans": [],
    "unknown": [],
    "complete": false,
    "compare": false,
    "reason": "coverage_anchor_uncertain"
  },
  "proposed_fragment_ids": [],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": []
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
Continuación literal de los puntos numerados de la guía:

4. Cortar únicamente la tela del pedido identificado. [S2]

5. Hilvanar las piezas para la primera prueba. [S2]

6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. [S3]

7. Coser las piezas aprobadas. [S3]

8. Revisar costuras, limpieza y cierre. [S4]

9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

Valoracion humana: pendiente.

## rag04-followup-07

Pregunta: ¿Sigue siendo válido después del cambio de permisos?

Ruta baseline: no_evidence; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: []; retenidos simulados: [].

Sin llamada al gate: no habia respuesta documental objetivo para revisar.

Respuesta baseline sintetica (historica, no regenerada):

```text
No encontré información documental disponible para tu consulta. Puedes precisar la pregunta o solicitar al administrador que revise la documentación publicada.
```

Valoracion humana: pendiente.

## rag04-multi_conflict-01

Pregunta: Resume el procedimiento completo y sus condiciones

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["proc-1", "proc-2", "proc-3", "proc-4"]; retenidos simulados: [].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "uncertain",
  "reason": "coverage_terms_uncertain",
  "signature": {
    "topics": [],
    "aspects": [
      "condition",
      "procedure"
    ],
    "qualifiers": [],
    "spans": [
      {
        "concept": "procedure",
        "kind": "aspect",
        "start": 10,
        "end": 23,
        "origin": "current_user"
      },
      {
        "concept": "condition",
        "kind": "aspect",
        "start": 39,
        "end": 50,
        "origin": "current_user"
      }
    ],
    "unknown": [
      {
        "token": "resume",
        "start": 0,
        "end": 6
      }
    ],
    "complete": true,
    "compare": false,
    "reason": "coverage_terms_uncertain"
  },
  "proposed_fragment_ids": [],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": []
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

Valoracion humana: pendiente.

## rag04-multi_conflict-02

Pregunta: Compara las dos circulares de anticipo

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["conflict-2", "conflict-1"]; retenidos simulados: [].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "uncertain",
  "reason": "coverage_terms_uncertain",
  "signature": {
    "topics": [
      "alteration_price",
      "reservation"
    ],
    "aspects": [
      "comparison"
    ],
    "qualifiers": [],
    "spans": [
      {
        "concept": "comparison",
        "kind": "aspect",
        "start": 0,
        "end": 7,
        "origin": "current_user"
      },
      {
        "concept": "reservation",
        "kind": "topic",
        "start": 16,
        "end": 26,
        "origin": "current_user"
      },
      {
        "concept": "alteration_price",
        "kind": "topic",
        "start": 30,
        "end": 38,
        "origin": "current_user"
      }
    ],
    "unknown": [
      {
        "token": "dos",
        "start": 12,
        "end": 15
      }
    ],
    "complete": false,
    "compare": true,
    "reason": "coverage_terms_uncertain"
  },
  "proposed_fragment_ids": [],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": []
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
Se muestran las fuentes por separado; no se establece prioridad entre ellas.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Circular ficticia B, vigente: reserva con anticipo del 50%. Ninguna circular indica prioridad. Debe aclararse la contradicción. [S1]

---

> Circular ficticia A, vigente: reserva con anticipo del 30%. Ninguna circular indica prioridad. [S2]
```

Valoracion humana: pendiente.

## rag04-multi_conflict-03

Pregunta: ¿Qué anticipo puedo asegurar si ambas circulares están vigentes?

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["conflict-2", "conflict-1"]; retenidos simulados: [].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "uncertain",
  "reason": "coverage_logic_uncertain",
  "signature": {
    "topics": [
      "alteration_price",
      "reservation"
    ],
    "aspects": [
      "comparison"
    ],
    "qualifiers": [],
    "spans": [
      {
        "concept": "alteration_price",
        "kind": "topic",
        "start": 5,
        "end": 13,
        "origin": "current_user"
      },
      {
        "concept": "comparison",
        "kind": "aspect",
        "start": 32,
        "end": 37,
        "origin": "current_user"
      },
      {
        "concept": "reservation",
        "kind": "topic",
        "start": 38,
        "end": 48,
        "origin": "current_user"
      }
    ],
    "unknown": [
      {
        "token": "asegurar",
        "start": 20,
        "end": 28
      },
      {
        "token": "si",
        "start": 29,
        "end": 31
      },
      {
        "token": "estan",
        "start": 49,
        "end": 54
      }
    ],
    "complete": false,
    "compare": true,
    "reason": "coverage_logic_uncertain"
  },
  "proposed_fragment_ids": [],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": []
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
Se muestran las fuentes por separado; no se establece prioridad entre ellas.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Circular ficticia B, vigente: reserva con anticipo del 50%. Ninguna circular indica prioridad. Debe aclararse la contradicción. [S1]

---

> Circular ficticia A, vigente: reserva con anticipo del 30%. Ninguna circular indica prioridad. [S2]
```

Valoracion humana: pendiente.

## rag04-multi_conflict-04

Pregunta: Relaciona el control de calidad y la aprobación final

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["proc-4"]; retenidos simulados: [].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "uncertain",
  "reason": "coverage_terms_uncertain",
  "signature": {
    "topics": [
      "quality"
    ],
    "aspects": [
      "condition"
    ],
    "qualifiers": [],
    "spans": [
      {
        "concept": "quality",
        "kind": "topic",
        "start": 24,
        "end": 31,
        "origin": "current_user"
      },
      {
        "concept": "condition",
        "kind": "aspect",
        "start": 37,
        "end": 47,
        "origin": "current_user"
      }
    ],
    "unknown": [
      {
        "token": "relaciona",
        "start": 0,
        "end": 9
      },
      {
        "token": "control",
        "start": 13,
        "end": 20
      }
    ],
    "complete": false,
    "compare": false,
    "reason": "coverage_terms_uncertain"
  },
  "proposed_fragment_ids": [],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": []
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S1]
```

Valoracion humana: pendiente.

## rag04-multi_conflict-05

Pregunta: ¿Cómo se conectan el patrón, el corte y la prueba?

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["proc-1", "proc-2", "proc-3"]; retenidos simulados: [].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "uncertain",
  "reason": "coverage_terms_uncertain",
  "signature": {
    "topics": [
      "cutting",
      "fitting",
      "pattern"
    ],
    "aspects": [
      "procedure"
    ],
    "qualifiers": [],
    "spans": [
      {
        "concept": "procedure",
        "kind": "aspect",
        "start": 1,
        "end": 5,
        "origin": "current_user"
      },
      {
        "concept": "pattern",
        "kind": "topic",
        "start": 21,
        "end": 27,
        "origin": "current_user"
      },
      {
        "concept": "cutting",
        "kind": "topic",
        "start": 32,
        "end": 37,
        "origin": "current_user"
      },
      {
        "concept": "fitting",
        "kind": "topic",
        "start": 43,
        "end": 49,
        "origin": "current_user"
      }
    ],
    "unknown": [
      {
        "token": "conectan",
        "start": 9,
        "end": 17
      }
    ],
    "complete": false,
    "compare": false,
    "reason": "coverage_terms_uncertain"
  },
  "proposed_fragment_ids": [],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": []
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]
```

Valoracion humana: pendiente.

## rag04-multi_conflict-06

Pregunta: ¿Puedo omitir una condición al resumir el procedimiento?

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["proc-1", "proc-2", "proc-3", "proc-4"]; retenidos simulados: [].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "uncertain",
  "reason": "coverage_terms_uncertain",
  "signature": {
    "topics": [],
    "aspects": [
      "condition",
      "procedure"
    ],
    "qualifiers": [],
    "spans": [
      {
        "concept": "condition",
        "kind": "aspect",
        "start": 18,
        "end": 27,
        "origin": "current_user"
      },
      {
        "concept": "procedure",
        "kind": "aspect",
        "start": 42,
        "end": 55,
        "origin": "current_user"
      }
    ],
    "unknown": [
      {
        "token": "resumir",
        "start": 31,
        "end": 38
      }
    ],
    "complete": false,
    "compare": false,
    "reason": "coverage_terms_uncertain"
  },
  "proposed_fragment_ids": [],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": []
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

Valoracion humana: pendiente.

## rag04-multi_conflict-07

Pregunta: Describe el proceso utilizando varios fragmentos

Ruta baseline: ambiguous; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: []; retenidos simulados: [].

Sin llamada al gate: no habia respuesta documental objetivo para revisar.

Respuesta baseline sintetica (historica, no regenerada):

```text
¿Puedes precisar cómo se relaciona tu consulta con las actividades de BELLAARTE BOUTIQUE? Así podré orientarte con el contexto adecuado.
```

Valoracion humana: pendiente.

## rag04-formats-05

Pregunta: Explica la tarifa con cifras exactas y cita la fuente

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["price-1"]; retenidos simulados: ["price-1"].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "approved",
  "reason": "coverage_verified",
  "signature": {
    "topics": [
      "alteration_price"
    ],
    "aspects": [
      "price"
    ],
    "qualifiers": [],
    "spans": [
      {
        "concept": "price",
        "kind": "aspect",
        "start": 22,
        "end": 36,
        "origin": "current_user"
      },
      {
        "concept": "alteration_price",
        "kind": "topic",
        "start": 11,
        "end": 17,
        "origin": "current_user"
      }
    ],
    "unknown": [],
    "complete": false,
    "compare": false,
    "reason": "coverage_intent_resolved"
  },
  "proposed_fragment_ids": [
    "price-1"
  ],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": [
    "7973faa026dc2289959ab87dbbce5dee671af0b1c61aa4aef0eb120b7b7c0799",
    "bd49c93e0a711e075e29f5f4e8877f3605eaf4158b11601442dfecb25caff33e"
  ]
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.

Extractos de las fuentes publicadas, conservando sus condiciones:

> Tarifa ficticia para evaluación: arreglo simple Bs 250.00; anticipo 40%; saldo antes de entregar. No describe tarifas reales. [S1]
```

Valoracion humana: pendiente.

## rag04-formats-06

Pregunta: Resume las reglas de inventario en dos viñetas

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["stock-1"]; retenidos simulados: [].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "uncertain",
  "reason": "coverage_terms_uncertain",
  "signature": {
    "topics": [
      "inventory"
    ],
    "aspects": [],
    "qualifiers": [],
    "spans": [
      {
        "concept": "inventory",
        "kind": "topic",
        "start": 21,
        "end": 31,
        "origin": "current_user"
      }
    ],
    "unknown": [
      {
        "token": "resume",
        "start": 0,
        "end": 6
      },
      {
        "token": "reglas",
        "start": 11,
        "end": 17
      },
      {
        "token": "dos",
        "start": 35,
        "end": 38
      },
      {
        "token": "vinetas",
        "start": 39,
        "end": 46
      }
    ],
    "complete": false,
    "compare": false,
    "reason": "coverage_terms_uncertain"
  },
  "proposed_fragment_ids": [],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": []
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Regla ficticia: contar unidades físicamente; mínimo 8 unidades; registrar diferencias con su motivo. No modificar existencias por conversación. [S1]
```

Valoracion humana: pendiente.

## rag04-acl-01

Pregunta: Consulta la tarifa como CAJA

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["price-1"]; retenidos simulados: ["price-1"].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "approved",
  "reason": "coverage_verified",
  "signature": {
    "topics": [
      "alteration_price"
    ],
    "aspects": [],
    "qualifiers": [],
    "spans": [
      {
        "concept": "alteration_price",
        "kind": "topic",
        "start": 12,
        "end": 18,
        "origin": "current_user"
      }
    ],
    "unknown": [],
    "complete": false,
    "compare": false,
    "reason": "coverage_intent_resolved"
  },
  "proposed_fragment_ids": [
    "price-1"
  ],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": [
    "7973faa026dc2289959ab87dbbce5dee671af0b1c61aa4aef0eb120b7b7c0799",
    "bd49c93e0a711e075e29f5f4e8877f3605eaf4158b11601442dfecb25caff33e"
  ]
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Tarifa ficticia para evaluación: arreglo simple Bs 250.00; anticipo 40%; saldo antes de entregar. No describe tarifas reales. [S1]
```

Valoracion humana: pendiente.

## rag04-acl-02

Pregunta: Consulta la tarifa como MODISTA

Ruta baseline: no_evidence; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: []; retenidos simulados: [].

Sin llamada al gate: no habia respuesta documental objetivo para revisar.

Respuesta baseline sintetica (historica, no regenerada):

```text
No encontré información documental disponible para tu consulta. Puedes precisar la pregunta o solicitar al administrador que revise la documentación publicada.
```

Valoracion humana: pendiente.

## rag04-acl-03

Pregunta: Consulta inventario como INV_BOUTIQUE

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["stock-1"]; retenidos simulados: ["stock-1"].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "approved",
  "reason": "coverage_verified",
  "signature": {
    "topics": [
      "inventory"
    ],
    "aspects": [],
    "qualifiers": [],
    "spans": [
      {
        "concept": "inventory",
        "kind": "topic",
        "start": 9,
        "end": 19,
        "origin": "current_user"
      }
    ],
    "unknown": [],
    "complete": false,
    "compare": false,
    "reason": "coverage_intent_resolved"
  },
  "proposed_fragment_ids": [
    "stock-1"
  ],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": [
    "67a8cf5b252e9fabd9c4f5649615cdc15667783acac6031d530093447e152a5d",
    "bd49c93e0a711e075e29f5f4e8877f3605eaf4158b11601442dfecb25caff33e"
  ]
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Regla ficticia: contar unidades físicamente; mínimo 8 unidades; registrar diferencias con su motivo. No modificar existencias por conversación. [S1]
```

Valoracion humana: pendiente.

## rag04-acl-04

Pregunta: Consulta inventario como CAJA

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["price-1"]; retenidos simulados: [].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "not_covered",
  "reason": "coverage_subject_mismatch",
  "signature": {
    "topics": [
      "inventory"
    ],
    "aspects": [],
    "qualifiers": [],
    "spans": [
      {
        "concept": "inventory",
        "kind": "topic",
        "start": 9,
        "end": 19,
        "origin": "current_user"
      }
    ],
    "unknown": [],
    "complete": false,
    "compare": false,
    "reason": "coverage_intent_resolved"
  },
  "proposed_fragment_ids": [],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": []
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Tarifa ficticia para evaluación: arreglo simple Bs 250.00; anticipo 40%; saldo antes de entregar. No describe tarifas reales. [S1]
```

Valoracion humana: pendiente.

## rag04-acl-05

Pregunta: Consulta taller como MODISTA

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["proc-1", "proc-2", "proc-3", "proc-4", "work-1"]; retenidos simulados: [].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "not_covered",
  "reason": "coverage_tangential_unit",
  "signature": {
    "topics": [
      "workshop"
    ],
    "aspects": [],
    "qualifiers": [],
    "spans": [
      {
        "concept": "workshop",
        "kind": "topic",
        "start": 9,
        "end": 15,
        "origin": "current_user"
      }
    ],
    "unknown": [],
    "complete": false,
    "compare": false,
    "reason": "coverage_intent_resolved"
  },
  "proposed_fragment_ids": [],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": []
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]

---

> Organización ficticia: separar piezas por pedido, identificar cada paquete y revisar la disponibilidad del material antes de programar el corte. [S5]
```

Valoracion humana: pendiente.

## rag04-acl-06

Pregunta: Consulta tarifa con el rol DOC

Ruta baseline: unknown; objetivo ejecutado EN LA RONDA PREVIA: False.

Antes: []; retenidos simulados: [].

Sin llamada al gate: no habia respuesta documental objetivo para revisar.

Respuesta baseline sintetica (historica, no regenerada):

```text
[No ejecutada]
```

Valoracion humana: pendiente.

## rag04-acl-07

Pregunta: Continúa la tarifa después de revocar la ACL

Ruta baseline: no_evidence; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: []; retenidos simulados: [].

Sin llamada al gate: no habia respuesta documental objetivo para revisar.

Respuesta baseline sintetica (historica, no regenerada):

```text
No encontré información documental disponible para tu consulta. Puedes precisar la pregunta o solicitar al administrador que revise la documentación publicada.
```

Valoracion humana: pendiente.

## rag04-acl-08

Pregunta: Continúa el procedimiento después de retirar su publicación

Ruta baseline: no_evidence; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: []; retenidos simulados: [].

Sin llamada al gate: no habia respuesta documental objetivo para revisar.

Respuesta baseline sintetica (historica, no regenerada):

```text
No encontré información documental disponible para tu consulta. Puedes precisar la pregunta o solicitar al administrador que revise la documentación publicada.
```

Valoracion humana: pendiente.

## rag04-acl-09

Pregunta: Consulta tarifa como ADMIN

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["price-1"]; retenidos simulados: ["price-1"].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "approved",
  "reason": "coverage_verified",
  "signature": {
    "topics": [
      "alteration_price"
    ],
    "aspects": [],
    "qualifiers": [],
    "spans": [
      {
        "concept": "alteration_price",
        "kind": "topic",
        "start": 9,
        "end": 15,
        "origin": "current_user"
      }
    ],
    "unknown": [],
    "complete": false,
    "compare": false,
    "reason": "coverage_intent_resolved"
  },
  "proposed_fragment_ids": [
    "price-1"
  ],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": [
    "7973faa026dc2289959ab87dbbce5dee671af0b1c61aa4aef0eb120b7b7c0799",
    "bd49c93e0a711e075e29f5f4e8877f3605eaf4158b11601442dfecb25caff33e"
  ]
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Tarifa ficticia para evaluación: arreglo simple Bs 250.00; anticipo 40%; saldo antes de entregar. No describe tarifas reales. [S1]
```

Valoracion humana: pendiente.

## rag04-acl-10

Pregunta: Consulta inventario como INV_TALLER

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["stock-1"]; retenidos simulados: ["stock-1"].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "approved",
  "reason": "coverage_verified",
  "signature": {
    "topics": [
      "inventory"
    ],
    "aspects": [],
    "qualifiers": [],
    "spans": [
      {
        "concept": "inventory",
        "kind": "topic",
        "start": 9,
        "end": 19,
        "origin": "current_user"
      }
    ],
    "unknown": [],
    "complete": false,
    "compare": false,
    "reason": "coverage_intent_resolved"
  },
  "proposed_fragment_ids": [
    "stock-1"
  ],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": [
    "67a8cf5b252e9fabd9c4f5649615cdc15667783acac6031d530093447e152a5d",
    "bd49c93e0a711e075e29f5f4e8877f3605eaf4158b11601442dfecb25caff33e"
  ]
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Regla ficticia: contar unidades físicamente; mínimo 8 unidades; registrar diferencias con su motivo. No modificar existencias por conversación. [S1]
```

Valoracion humana: pendiente.

## rag04-no_evidence-01

Pregunta: ¿Qué procedimiento publicado regula bordados con hilo de oro?

Ruta baseline: rag; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: ["proc-1", "proc-2", "proc-3", "proc-4"]; retenidos simulados: [].

Decision exploratoria (sin autoridad de emision):

```json
{
  "verdict": "not_covered",
  "reason": "coverage_subject_mismatch",
  "signature": {
    "topics": [
      "embroidery"
    ],
    "aspects": [
      "procedure"
    ],
    "qualifiers": [
      "gold_thread"
    ],
    "spans": [
      {
        "concept": "gold_thread",
        "kind": "qualifier",
        "start": 49,
        "end": 60,
        "origin": "current_user"
      },
      {
        "concept": "procedure",
        "kind": "aspect",
        "start": 5,
        "end": 18,
        "origin": "current_user"
      },
      {
        "concept": "embroidery",
        "kind": "topic",
        "start": 36,
        "end": 44,
        "origin": "current_user"
      }
    ],
    "unknown": [],
    "complete": false,
    "compare": false,
    "reason": "coverage_intent_resolved"
  },
  "proposed_fragment_ids": [],
  "release_allowed": false,
  "authoritative": false,
  "manifest_fingerprints": []
}
```

Respuesta baseline sintetica (historica, no regenerada):

```text
Extractos de las fuentes publicadas, conservando sus condiciones:

> Documento ficticio de evaluación. 1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento. 3. Trazar el patrón antes del corte. [S1]

> Documento ficticio de evaluación. 4. Cortar únicamente la tela del pedido identificado. 5. Hilvanar las piezas para la primera prueba. [S2]

> Documento ficticio de evaluación. 6. Realizar la prueba de ajuste. Si hay diferencias, corregir antes de coser. 7. Coser las piezas aprobadas. [S3]

> Documento ficticio de evaluación. 8. Revisar costuras, limpieza y cierre. 9. Entregar solo después de la aprobación final; registrar la entrega. [S4]
```

Valoracion humana: pendiente.

## rag04-no_evidence-02

Pregunta: ¿Cuántas pruebas exige un vestido de ceremonia con plumas?

Ruta baseline: no_evidence; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: []; retenidos simulados: [].

Sin llamada al gate: no habia respuesta documental objetivo para revisar.

Respuesta baseline sintetica (historica, no regenerada):

```text
No encontré información documental disponible para tu consulta. Puedes precisar la pregunta o solicitar al administrador que revise la documentación publicada.
```

Valoracion humana: pendiente.

## rag04-no_evidence-03

Pregunta: ¿Qué plazo exacto publicado tienen los ajustes de encaje?

Ruta baseline: no_evidence; objetivo ejecutado EN LA RONDA PREVIA: True.

Antes: []; retenidos simulados: [].

Sin llamada al gate: no habia respuesta documental objetivo para revisar.

Respuesta baseline sintetica (historica, no regenerada):

```text
No encontré información documental disponible para tu consulta. Puedes precisar la pregunta o solicitar al administrador que revise la documentación publicada.
```

Valoracion humana: pendiente.

