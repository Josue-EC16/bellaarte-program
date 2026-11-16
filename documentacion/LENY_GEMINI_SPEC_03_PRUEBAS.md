# LENY SPEC-03 — pruebas y revisión pendiente

05/11/2026. Evidencia de implementación; **no aprobación de calidad humana**.

## Comprobaciones terminadas

| Comprobación | Resultado | Evidencia |
|---|---|---|
| Regresión LENY sanitizada, SQL/procesos bloqueados | 1118 aprobadas, 1 omitida, 1 separada; 29,08 s | `evidencias/leny_spec03_regression_final.xml` |
| Prueba histórica de importación con subintérprete y guardas propias | 1 aprobada; 1,93 s | `evidencias/leny_spec03_import_test.xml` |
| SQL real de ACL, consentimiento, título y secciones | 9 aprobadas; 12,16 s, sin DDL/inferencia | `evidencias/leny_spec03_sql_scope.xml` |
| Migración/perfil/cuota en transacción aislada | 9 comprobaciones con rollback; después despliegue autorizado 0025 | `schema0025.json` y `deployment.json` privados |
| React: chat, selector, transporte y fuentes | 45 aprobadas | `evidencias/leny_spec03_frontend.json` |
| Paquete de revisión después de su último ajuste | 4 aprobadas | `evidencias/leny_spec03_review_package_tests.xml` |
| ESLint de tres archivos frontend modificados | Correcto | Comando indicado abajo |
| Vite en carpeta temporal nueva | Correcto: 4089 módulos, 53,62 s | No se sobrescribió `dist` habitual |
| Dependencias: `pip check` | Sin incompatibilidades | Sin instalaciones/actualizaciones |
| Estado tras recarga controlada | `/health` 200; LENY sin autenticación 401; Qwen instalado | `evidencias/leny_spec03_operational.json` |

La prueba de importación se separa porque abre deliberadamente un intérprete Python: el launcher general lo bloqueó correctamente en los intentos anteriores. No se relajó la prohibición de procesos para las otras pruebas. Se conservó el XML del intento inicial. La advertencia pypdf por `add_js` corresponde a una prueba de archivo adversarial sintético. Vite advierte del tamaño del bundle; no se modificó su umbral para ocultarlo.

Los 1118 casos incluyen el paquete antes del último texto explicativo; sus cuatro casos se ejecutaron nuevamente después. No sumar esas cuatro como casos nuevos independientes de aceptación.

## Ejecuciones reales conservadas

| Lote | Turnos | Documental/parcial con fuentes | General | Aclaración | Error | Rechazo operativo |
|---|---:|---:|---:|---:|---:|---:|
| B0 Gemini | 20 | 12 | 4 | 2 | 1 | 1 |
| C1 candidata | 20 | 0 | 7 | 10 | 2 | 1 |
| C2 corregida, RAM insuficiente | 20 | 0 | 7 | 1 | 11 | 1 |
| Qwen habitual | 20 | 6 | 3 | 10 | 0 | 1 |

No son aprobaciones semánticas. C1 demuestra una regresión, no una mejora. C2 incluye diez `LENY_RAG_MEMORY`. Todos los intentos se mantienen; no se reintentaron selectivamente hasta obtener respuestas buenas. El caso de correo fue bloqueado antes de enviar a Gemini y se conserva como error HTTP del runner, aunque el bloqueo era esperado. Qwen puede tratarlo localmente.

Fuentes abiertas: 24/24 B0 y 10/10 Qwen. Texto emitido/persistido coincide en todos los turnos admitidos: 19/19 de cada lote Gemini y 20/20 Qwen. Esto prueba transporte y persistencia, no fidelidad. No se midieron Hit/Recall/fidelidad sin gold empresarial humano.

Consumo durable: 94 solicitudes de evaluación, incluyendo cuatro de preflight. B0 48, C1 28, C2 14. No se agotó el límite de 150. Tokens conocidos agregados y llamadas fallidas con uso desconocido: `evidencias/leny_spec03_effective_state.json`. Qwen sin tokens locales capturados por este runner. Sin p95 ni comparación de velocidad entre lotes heterogéneos o estados de memoria distintos.

## Correcciones comprobadas sin nuevas llamadas

Reproducción sobre nueve salidas fijas de C1: todas pasan ahora el contrato; cinco fallaban antes (vestido, encargada, errata, título y descripción de puesto). Evidencia `leny_spec03_validator_replay.json`. Esta prueba usa la misma salida generada, **no genera ni publica otra respuesta** ni demuestra fidelidad completa.

Pares sintéticos críticos cubren paráfrasis válida frente a cargo cambiado; cantidad intercambiada citando ambos pasajes; unidad de tiempo; negación; condición temporal omitida frente a paráfrasis conservada; cuerpo con encabezado de ID diferente frente a mero título de archivo. Soporte ambiguo se omite, sin devolver silenciosamente texto extractivo como síntesis.

## Comandos reproducibles

Desde `C:\laragon\www\bellaarte-program`:

```powershell
backend\venv\Scripts\python.exe -B backend/scripts/run_leny_spec03_regression.py
& backend/scripts/test_leny_spec03_schema.ps1 -ScopeTests
backend\venv\Scripts\python.exe -B backend/scripts/revalidate_leny_spec03.py
backend\venv\Scripts\python.exe -B backend/scripts/build_leny_spec03_review.py
backend\venv\Scripts\python.exe -B backend/scripts/collect_leny_spec03_status.py
backend\venv\Scripts\python.exe -B backend/scripts/measure_leny_spec03_resources.py
backend\venv\Scripts\python.exe -B -m pip check
```

Desde `frontend`:

```powershell
pnpm.cmd exec vitest run src/pages/leny/LenyPage.test.jsx src/pages/leny/lenyTransport.test.js src/pages/leny/documents/documentAxios.test.js --no-cache --reporter=json --outputFile=../documentacion/evidencias/leny_spec03_frontend.json
pnpm.cmd exec eslint src/pages/leny/LenyPage.jsx src/pages/leny/useLenyChat.js src/pages/leny/LenyPage.test.jsx
```

La compilación se ejecutó con `pnpm.cmd exec vite build --outDir <carpeta-temporal-nueva>`; sin vaciar una ruta existente ni tocar el `dist` habitual. Las pruebas SQL verifican manifiesto, directorio e instancia 55432; no reutilizan fixtures destructivas contra la base original. El runner autenticado usado fue `backend/scripts/run_leny_spec03_review.py --watch`; la sesión de evaluación se cerró al terminar los lotes, sin guardar credenciales.

## Pruebas personales del propietario

1. Cuando haya RAM suficiente, entrar normalmente a `http://localhost:5173/app/leny` y actualizar la página.
2. Crear conversación nueva con **Qwen — Local** para comprobar comportamiento habitual. Qwen sigue predeterminado.
3. Crear otra con **Gemini — Google AI**. Con permiso administrativo, seleccionar **Perfil de revisión → Evaluación SPEC-03 (provisional)** antes de enviar. «Habitual» prueba la referencia anterior. Modelo y perfil quedan fijos en esa conversación.
4. Probar confección y, en el mismo chat: «¿Y después?», «¿Qué sucede en la segunda prueba?», «Explícame mejor ese último paso», «¿Quién se encarga?», «¿Dónde está documentado?» y resumen. No suponer tareas ejecutadas.
5. En conversaciones nuevas: encargada, título explícito, can-can, inventario, MODISTA frente a asesoría, especialidad ausente, manual general y ejemplo. Abrir las fuentes y comprobar cargo, cifras y condiciones. Si no existe evidencia del cargo, no adjudicar funciones de otro.
6. Registrar resultados en el paquete privado y después ejecutar las ocho preguntas reservadas sin usarlas para ajustar reglas. No pegar documentación privada en el chat de desarrollo.

Paquete: `%LOCALAPPDATA%\BAB_VDOS\leny-spec03\20261105-134550\review\human-review\REVISION_HUMANA_SPEC03.html`. Tiene 20 casos/80 intentos históricos, campo para la nueva ejecución corregida y ocho casillas reservadas. Exportar la rúbrica JSON a esa carpeta privada. No tiene red ni guardado automático en el navegador.

Si aparece `LENY_RAG_MEMORY`, no significa que Gemini esté desactivado: los embeddings siguen siendo locales y requieren la guarda de RAM. No se redujo el umbral de 2 GiB. La aceptación integral SPEC-03 permanece pendiente de estas pruebas, del gold adjudicado y de revisión humana.
