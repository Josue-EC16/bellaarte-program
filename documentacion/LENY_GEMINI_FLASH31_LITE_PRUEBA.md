# LENY — prueba solicitada de Gemini 3.1 Flash-Lite

Fecha:05/11/2026. **Generación mínima real satisfactoria** mediante GeminiProvider y SDK oficial instalado2.33.0. Modelo: `gemini-3.1-flash-lite`, conforme a la [ficha oficial](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite).

Comando ejecutado desde el proyecto original:

```powershell
& backend\venv\Scripts\python.exe -B backend\scripts\probe_leny_gemini_spec02.py --name flash31_lite_connectivity --model gemini-3.1-flash-lite --plain
```

Se pidió únicamente «Responde únicamente OK.», sin historial ni documentación. La consulta de modelo y la generación terminaron satisfactoriamente en2,719s totales. El adaptador obtuvo texto no vacío y finalizaciónSTOP. Dos llamadas totales: metadatos y generación; sin reintento de generación. Métricas de generación informadas:7tokens de entrada,1de salida y77de pensamiento; no se guardó ni mostró pensamiento interno. La llamada de metadatos no reportó contadores de tokens; por ello el agregado indica una llamada sin esos contadores.

Se mantuvieron pensamiento`medium`, entrada32678, salida8192, RPM5, TPM250000 y RPD20. Se usaron la coordinación y reservas durables actuales, sin borrar consumo ni modificar facturación/proyecto. La clave no se imprimió, copió ni sustituyó.

Se añadió3.1Flash-Lite a la lista explícita permitida del adaptador y un argumento de diagnóstico `--model` limitado a los tres modelos ya autorizados por el propietario. La selección afecta únicamente al proceso de prueba. **El `.env` permanece intacto, configurado con3.5Flash-Lite y Gemini desactivado; Qwen sigue predeterminado.** No se reinició el backend ni se alteraron conversaciones, ACL, corpus, índices, ranking o validadores.

Archivos de código: `backend/app/services/leny_gemini.py`, `backend/scripts/probe_leny_gemini_spec02.py`, `backend/tests/test_leny_gemini_provider.py`. Respaldo privado con hashes antes/después: `%LOCALAPPDATA%\BAB_VDOS\leny-gemini-flash31-probe`, subdirectorio de esta ejecución; no contiene copia de `.env`. Revertir únicamente esas líneas después de comprobar hashes; no restaurar desde HEAD ni sobrescribir ediciones posteriores.

Pruebas locales específicas: **77aprobadas**,2,94s, sin peticiones externas ni base empresarial. Backend `/health`200. Evidencia:

- `evidencias/leny_gemini_spec02_flash31_lite_connectivity.json`.
- `evidencias/leny_gemini_flash31_lite_tests.xml`.
- `evidencias/leny_gemini_flash31_lite_state.json`.

Esto acredita conectividad y generación de texto con este modelo. **No acredita JSON estructurado, historial, RAG, citas, calidad empresarial ni aceptación de SPEC-02.** No se ejecutaron esas pruebas adicionales en este encargo limitado.
