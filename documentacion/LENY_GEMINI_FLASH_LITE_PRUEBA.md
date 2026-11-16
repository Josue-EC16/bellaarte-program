# LENY — cambio autorizado a Gemini 3.5 Flash-Lite

Fecha:05/11/2026. Cambio pequeño solicitado por el propietario tras SPEC-02.1.

Se configuró `gemini-3.5-flash-lite`, identificador de la [ficha oficial](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite). Google publica una modalidad gratuita para este modelo en sus [precios](https://ai.google.dev/gemini-api/docs/pricing); no se activó facturación ni otro proyecto.

Se cambió únicamente el modelo de la configuración privada. Se preservaron clave, RPM5, TPM250000, RPD20, pensamiento`medium`, entrada32678, salida8192, timeouts y Qwen predeterminado. Gemini sigue deshabilitado para usuarios.

Archivos: `backend/.env`, `backend/.env.example`, default de `backend/app/core/config.py`, lista permitida en `backend/app/services/leny_gemini.py` y pruebas `backend/tests/test_leny_gemini_provider.py`. El adaptador conserva también3.8Flash como identidad permitida para conversaciones históricas; no convierte conversaciones existentes ni hace fallback entre modelos. El diagnóstico congelado de SPEC-02.1 sigue referido a3.8Flash; esta prueba utilizó el runner de sondeo compatible con el modelo configurado.

Prueba real ejecutada:

```powershell
& backend\venv\Scripts\python.exe -B backend\scripts\probe_leny_gemini_spec02.py --name flash_lite_connectivity --plain
```

Se consultaron metadatos del modelo y se pidió únicamente «Responde únicamente OK.», sin RAG, historial ni documentación. Se usaron lease PostgreSQL y registro durable de cuota. **Metadatos accesibles; generación fallida con HTTP503.** El adaptador efectuó dos intentos de generación como máximo —el único reintento503 permitido—. Duración total41,454s. No hubo respuesta generada utilizable; no se probaron JSON, conversación o RAG ni se declara SPEC-02 aceptada.

Evidencia: `evidencias/leny_gemini_spec02_flash_lite_connectivity.json`. La prueba no guardó la clave, prompts privados ni cuerpos de error. No se borró consumo previo para conseguir llamadas favorables.

Pruebas locales:76aprobadas,3,18s, sin Google ni base comercial; `evidencias/leny_gemini_flash_lite_tests.xml`. Verifican ambos modelos explícitos y conservación de cuotas/parámetros. No se sustituyeron dependencias ni se modificaron ACL, documentos, índices o esquema.

Backend original recargado con el helper que comprueba identidad, lease y operaciones activas. Salud200. Estado efectivo en `evidencias/leny_gemini_flash_lite_state.json`; se verificó por huella que `.env` solo cambió en su variable de modelo.

Respaldo privado de fuentes y hashes antes/después: `%LOCALAPPDATA%\BAB_VDOS\leny-gemini-flash-lite\20261105-123754`, manifiestos `manifest.json` y `manifest-final.json`. No incluye copia del archivo privado de entorno. Reversión operacional: mantener Gemini desactivado; si se decide volver al modelo anterior, cambiar solo `LENY_GEMINI_MODEL=gemini-3.8-flash` y recargar controladamente. No modificar conversaciones persistidas. Para retirar los cambios de fuente, comprobar hashes posteriores y revisar solo las líneas del default/lista permitida/ejemplo/pruebas; no restaurar el repositorio desde HEAD ni sobrescribir ediciones posteriores.
