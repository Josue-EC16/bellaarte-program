# Plan de mejora incremental LENY

## Actualización operacional autorizada — 03/11/2026

El propietario autorizó posteriormente integración selectiva y recarga del backend original, ajustes propios de configuración y pruebas por API con autenticación normal. Esta autorización reemplaza las restricciones de activación de la planificación histórica que sigue abajo. No autoriza modificar datos comerciales, publicaciones, ACL, originales o índices. No hubo migraciones ni dependencias nuevas.

Orden realmente ejecutado en el original: respaldo privado del árbol local → B0 autenticada → A3 (dependencia de soporte entre fragmentos) → A1 → A2 → dos experimentos A4 → combinación → correcciones de interacciones → repetición completa. Se preservan los intentos negativos y los intentos donde la recarga no cargó la variante. Estos últimos no demuestran beneficio de una mejora.

Configuración candidata: soporte vinculado, contexto estructural y cobertura por fuente activados; pista experimental de seguimiento desactivada porque repitió pasos en las pruebas reales. A5 conserva métricas acumuladas y alcance visible. La calidad semántica y SPEC-04 permanecen pendientes de revisión y evaluación completa; la configuración activa no implica aceptación.

La comparación original utiliza la identidad introducida localmente por el propietario. Las conversaciones/cuotas/fuentes de esos ensayos sí se registran por las API normales; los documentos, índices y permisos no se alteran. Las pruebas de revocación y otros estados modificables usan PostgreSQL sintético 55432 con manifiesto, marcador y revisión verificados. Ollama comparte el coordinador durable habitual y las inferencias se ejecutan en serie.

Reversión y resultados vigentes: `REPORTE_MEJORA_INCREMENTAL_LENY.md`, sección de integración original. Los apartados siguientes conservan el plan anterior como historia, no como descripción del estado operativo actual.

Fecha: 03/11/2026. Autorización: implementación y evaluación aisladas, sin activación del ERP.
## Aislamiento y snapshot
Rama codex/leny-incremental-20261103; worktree C:/Users/MARCELO/AppData/Local/Temp/BAB_LENY_INCREMENTAL_20261103.
HEAD base 5a1d15a04c2f97483769c86e82dbba056adce6b8 más overlay de28 archivos locales, identificados en documentacion/evidencias/leny_incremental_snapshot.json.
No se copiaron .env ni documentos empresariales. Intérprete existente reutilizable; imports desde copia y configuración aislada. Destino PostgreSQL55432 se verificará por manifiesto, marcador SQL y data_directory, no por puerto solamente.
El propietario autorizó expresamente usar bloqueo/estado técnico de inferencia habituales para compartir Ollama. Conversaciones, cuotas, corpus y fuentes de evaluación permanecerán aislados. Ningún runner podrá usar bases habituales para otra finalidad.
## Diagnóstico y línea base
El informe comparativo y código muestran síntesis activa; cinco referencias finales cuentan fragmentos, aunque procedan del mismo documento. RRF ya existe; vecinos globales apagados en la configuración de referencia. Revalidar configuración permitida antes de inferir.
Problemas: pérdida de encabezado, cobertura parcial por título, validación de cantidades sobre fragmentos hermanos, progreso conversacional recortado y métricas de última llamada.
B0 ejecutará pruebas actuales y corpus sintético existente sin abrir holdout. Registrar fallos originales, candidatos, selección, soporte, respuesta y causa. Encargada: no atribuir fallo a recuperación si evidencia completa llega al prompt.
## Hipótesis y decisiones predefinidas
|Variante|Hipótesis y archivos|Indicador principal y puerta de conservación|
|---|---|---|
|A1|Paquete autorizado de sección: retrieval/selection y pruebas; sin reindexar|Recuperar encabezado/condición gold ausente con IDs, límites20/5 intactos; cero cruce de sección/cargo/ACL|
|A2|Fuente explícita corta o cobertura parcial: retrieval/service y pruebas|Mejor cobertura del asunto final del documento, sin afirmar totalidad ni cambiar permisos|
|A3|Soportes explícitos y causas: synthesis/service/diagnostics y pruebas|Rechazar cifra prestada de pasaje no citado y aceptar paráfrasis fiel; no LLM juez ni segundo pase|
|A4|Progreso verificable: store/routing/service y pruebas|Continuación sin repetir pasos ni reutilizar fuente revocada; ambiguo si progreso no comprobable|
|A5|Alcance y métricas: diagnostics/inference_state/frontend y pruebas|Acumulación exacta de todas las llamadas y clasificación documental/general/parcial; sin atribuir mejora semántica a contadores|
## Orden y comparaciones
1. Verificar destinos/fixtures/lifespan, documentar B0 y congelar casos de desarrollo antes de editar comportamiento.
2. A1, A2, A3, A4, A5 con checkpoints independientes cuando sea posible; dependencia declarada si existe.
3. Tests pertinentes y comparaciones Qwen seriales con modelo/evidencia iguales. Corregir como máximo dos intentos justificados por variante; conservar resultados negativos.
4. Combinar solo variantes con beneficio demostrado; las semánticas sin revisión humana se marcan provisionales y no se activan.
5. Reporte con fila B0/A1/A2/A3/A4/A5/final, comandos, N y resultados reales. No declarar candidato final si faltan puertas críticas.
## Configuración y recursos
Conservar Qwen3.5:4b-q4_K_M, embedding0.6b/1024 CPU, ctx4096/salida768/temp0,20 candidatos/5 fragmentos, cuotas y RAM2/1GiB. Una inferencia a la vez, coordinación durable. Puertos de aplicación aislada distintos de8000/5173; autostart deshabilitado, sin worker habitual.
Coste aceptable inicial: sin inferencias adicionales de redacción; A1/A2 SQL/contexto acotados; plazo120s y márgenes actuales intactos. Comparación de latencias individuales: aumento >20% frente a B0 comparable requiere justificar y deja variante pendiente; no es SLA. Con pocas muestras no se infiere estabilidad ni p95.
## Casos y métricas
Encargada; vestidos; primera prueba con errata; seguimiento2–3turnos; manual/ejemplo/título; can-can; cargos separados; inventario/tarifas; especialidad ausente; documento extenso; plantilla/norma; números/unidades/negaciones/excepciones; restricciones/revocaciones/inyección/capacidad no disponible.
Registrar Hit/Recall/MRR@20 y @5 por fragmentos, selección/cobertura, fidelidad por afirmación y citas, falsas abstenciones/aceptaciones. Conservar SPEC04:95%activación,<=5%rechazo,90%Hit@5,85%Recall@5,90%fidelidad,95%citas/ausencia evidencia. Cero errores críticos observados. Conjunto pequeño solo informa casos, no certifica porcentajes.
No abrir holdout para optimizar. Revisión humana A/B privada, sin completar puntuaciones humanas automáticamente.
## Reversión y riesgos
No migraciones/dependencias/reindexación global. Índices sintéticos solo en aislamiento si se justifican. Cada experimento separado del baseline; revertir únicamente cambios propios en copia mediante parche inverso/checkpoint, nunca reset/clean del árbol habitual.
No alterar originales/publicaciones/ACL ni recargar ERP. Activación y merge quedan para decisión posterior.
Los secretos nunca se imprimen; textos empresariales solo en paquete privado autorizado. La coordinación técnica compartida no concede permiso para datos comerciales.

