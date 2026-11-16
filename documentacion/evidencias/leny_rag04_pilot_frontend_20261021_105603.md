# Piloto LENY RAG-04: verificación frontend

Fecha: 21/10/2026, `America/La_Paz`. Verificación ejecutada sobre el árbol existente, sin editar fuentes, pruebas, configuraciones o dependencias.

| Comprobación | Resultado |
|---|---|
| `pnpm.cmd lint` | Correcto; salida 0. |
| `pnpm.cmd exec vitest run --no-cache` | 117/117 pruebas; 18 archivos; sin fallos ni omitidas; duración informada 30,89 s. |
| Build Vite a TEMP nuevo | Correcto; 4.081 módulos; duración informada 41,37 s. |
| Integridad antes/después | 134 archivos comparados con SHA-256; ninguno cambió o desapareció. |

Runtime verificado: Node 22.12.0, pnpm 10.33.0, React 19.0.0, Ant Design 5.29.3, Axios 1.14.0, React Router 7.14.0, Vite 6.4.1, Vitest 3.2.4, ESLint 9.39.4 y jsdom 27.4.0. El reporte JSON contiene hashes relevantes y el desglose completo de pruebas.

El build se escribió en `%TEMP%/bab-leny-rag04-pilot-20261021-4052cc16`; no se modificó `frontend/dist`. El JavaScript principal pesa 2.692.244 bytes (gzip informado 805,59 kB), por lo que continúa la advertencia de chunks mayores a 500 kB. La advertencia sobre salida fuera de la raíz es esperada: se utilizó un directorio nuevo y no se ejecutó `emptyOutDir`.

Las pruebas cubren los escenarios existentes de chat/streaming, fuentes privadas, publicación, contextualización, biblioteca, cargas cancelables, JWT/XHR, formularios, notificaciones y contratos económicos mediante mocks. Esto no demuestra disponibilidad del backend, exactitud de respuestas/OCR, carga sostenida o seguridad global. No se accedió a bases de datos, modelos, redes ni al ERP desde el navegador; no se realizó E2E ni inspección visual. Las duraciones comparten recursos de la máquina por ejecución concurrente y no son un benchmark de latencia.

Se requirió ejecutar herramientas instaladas fuera del sandbox tras un error de lectura `EPERM` en `node_modules`; no se instalaron paquetes ni se cambiaron permisos.

Evidencia detallada: [leny_rag04_pilot_frontend_20261021_105603.json](leny_rag04_pilot_frontend_20261021_105603.json).
