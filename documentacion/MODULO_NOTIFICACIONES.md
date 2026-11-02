# Módulo de Notificaciones — BAB_VDOS

Revisión: 18/10/2026. FastAPI, SQLAlchemy síncrono, PostgreSQL 17 y React/Ant Design.

## Propósito y despliegue

Centralizar incidencias sin multiplicarlas, conservar su historial y distinguir reconocimiento, resolución y escritorio. Corrección implementada y probada en una instancia aislada. **La migración `20261018_0014` se aplicó con autorización explícita en `bellaarte_db:5432` el 18/10/2026**, después de verificar un respaldo y pausar la API. La API se reanudó y las consultas de preferencias, resumen y listado pasaron en modo de solo lectura. API y SPA deben conservar sus contratos coordinados.

Los servicios generan alertas dentro de sus operaciones; jobs explícitos reconcilian condiciones. No hay alta manual comercial desde la interfaz. No se añaden Redis, Celery, WebPush ni tareas Windows automáticamente. Los GET de consulta no generan alertas de stock ni reparan datos.

## Estructura

| Archivo bajo backend/app | Responsabilidad |
| --- | --- |
| core/notification_catalog.py | Tipos, destinatarios, cierre y zona horaria |
| models/notification.py | Notificacion, PreferenciaNotificacion y EnvioNotificacionCorreo |
| schemas/notification.py | Contratos, páginas, revisiones y preferencias |
| services/notification_service.py | Fachada para consumidores existentes |
| services/notification_sync_service.py | Episodios y sincronización con orígenes |
| services/notification_query_service.py | Consultas, lectura, cierre y reporte |
| services/notification_delivery_service.py | Consentimiento y claim atómico de escritorio |
| services/notification_email_service.py | Elegibilidad, intentos durables y reintentos |
| services/notification_job_service.py | Lotes, bloqueos y contadores |
| services/email_service.py | Transporte SMTP y categorías seguras |
| api/routers/notifications.py | HTTP y permisos explícitos |

Frontend: `NotificationsPage.jsx` administra lista/detalle y acciones; `useNotificationCenter.js` mantiene la campana personal; `notificationTransport.js` coordina polling, eventos y presentación nativa.

## Tipos y destinatarios

| Familia | Tipos | Roles operativos |
| --- | --- | --- |
| Stock | STOCK_BAJO_BOUTIQUE / STOCK_BAJO_TALLER | ADMIN y responsable INV_BOUTIQUE / INV_TALLER |
| Entregas | ENTREGA_PEDIDO_2_DIAS, ENTREGA_PEDIDO_1_DIA, ENTREGA_PEDIDO_HOY | ADMIN, MODISTA, INV_BOUTIQUE; CAJA si existe saldo |
| Pruebas | PRUEBA_PEDIDO_2_DIAS, PRUEBA_PEDIDO_1_DIA, PRUEBA_PEDIDO_HOY | ADMIN, MODISTA, INV_BOUTIQUE |
| Material | PRUEBA_1_ALISTAR_MATERIAL, PRUEBA_2_ALISTAR_MATERIAL | ADMIN, MODISTA, CAJA |
| Devolución | DEVOLUCION_FLETE_2_DIAS, DEVOLUCION_FLETE_1_DIA, DEVOLUCION_FLETE_HOY, DEVOLUCION_FLETE_VENCIDA | ADMIN, INV_BOUTIQUE; CAJA con garantía pendiente o arreglo |
| Usos | FLETE_MAX_SALIDAS | ADMIN, INV_BOUTIQUE |
| Correo | ERROR_ENVIO_CORREO | ADMIN |
| Genérico | SISTEMA | Destinatarios del generador autorizado |

Cuenta, usuario y rol deben estar habilitados. Cambiar elegibilidad cierra copias que ya no corresponden. Los responsables nuevos reciben incidencias vigentes en la siguiente sincronización del origen o reconciliación diaria.

## Episodios, reconocimiento y resolución

La identidad abierta es destinatario + tipo + tabla de origen + ID de origen. Tipo y tabla se normalizan; referencias ausentes se conservan como NULL. El índice parcial único `ux_notificacion_abierta`, con NULLS NOT DISTINCT, protege también referencias nulas y sesiones concurrentes. Conflictos esperados usan UPSERT; errores reales no se ocultan.

Sin cambios no se crean filas ni se pierde el reconocimiento. Cambiar mensaje o prioridad conserva episodio, lectura y fecha de apertura. Leer reconoce una `revision`: una petición antigua devuelve 409 y no reconoce una escalada posterior. La lectura masiva protege también la revisión observada y es exclusivamente personal, incluido ADMIN.

Stock, ventanas de entrega/prueba, devoluciones, usos y errores de correo se cierran al corregirse o quedar obsoletos. Cierre manual de estas condiciones devuelve 409. Preparación de material y SISTEMA admiten cierre manual autorizado. Resolver no inventa una lectura. Campana y escritorio excluyen resueltas; el histórico conserva ambas fechas.

### Stock

- Artículo/tipo activos con stock <= mínimo: episodio abierto.
- Recuperación por encima del mínimo o desactivación: cierre automático.
- Primera alerta ya en cero: revisión 1 urgente.
- Primera caída posterior a cero: revisión 2 y un reconocimiento adicional.
- Oscilar bajo el mínimo no vuelve a escalar tras ese primer agotamiento.
- Recuperarse y volver a bajar abre otro episodio con ID distinto.

Se sincronizan altas/ediciones, entradas/salidas, ventas/reversiones y fletes que afectan Boutique. La alerta comparte commit/rollback con el origen comercial; sus helpers no confirman parcialmente. Se bloquea el origen antes de evaluarlo y las cuentas destinatarias al generar. La reconciliación de elegibilidad se coordina con esas cuentas. Esto no corrige todas las carreras comerciales de stock/pagos.

### Fechas y preparación

Fechas de negocio: America/La_Paz; timestamps: UTC. Cambiar ventana o estado cierra avisos obsoletos. Editar el máximo de usos de flete sincroniza su alerta antes del commit.

Preparación se renueva al registrar o reprogramar fecha/hora de pruebas 1/2; cambiar observaciones no crea otra tarea. La reconciliación puede entregar una tarea vigente a un responsable nuevo, sin reabrir su tarea completada ni simular una reprogramación. Las tareas de pedidos inactivos se cierran.

## Consultas y permisos

Campana y lista ordinaria personales, incluido ADMIN. Supervisión separada exige `notifications:list_all`; no permite leer copias ajenas. Reporte exige `notifications:report`. El nombre del rol no concede permisos. El resumen filtra abiertas/no leídas antes de limitar las últimas filas.

Página de servidor `{items,total,page,page_size}`: tamaño 25 por defecto, máximo 100, orden estable por fecha/ID descendentes. La SPA no descarga el histórico completo. Búsqueda con debounce 300 ms y catálogos autorizados aparte. Descarta respuestas obsoletas, bloquea dobles envíos y muestra errores de actualización. Las acciones actualizan lista y campana.

## Escritorio opcional

Preferencia y permiso se activan mediante acción explícita; no se pide permiso al montar la SPA. No se guardan tokens ni mensajes en storage. El servidor reclama atómicamente revisiones propias abiertas/no leídas:

- posteriores a la activación actual y de los últimos 15 minutos;
- todavía no reclamadas;
- máximo tres por ciclo, priorizando urgentes.

Dos pestañas/dispositivos no reclaman la misma revisión. El tag del navegador es complementario. Garantía: **como máximo un intento autorizado de presentación**, no entrega exactamente una vez. Una respuesta perdida consume el intento; la incidencia sigue en la campana. Activar escritorio no anuncia el histórico. No se promete entrega con la aplicación cerrada.

Polling cada 60 segundos, sin ciclos simultáneos equivalentes. Foco, visibilidad y acciones comparten coordinación y limpieza. Cambiar de cuenta reinicia el centro.

## Contratos API

Prefijo `/api/v1/notificaciones`; rutas estáticas antes del ID dinámico.

| Método/ruta | Contrato |
| --- | --- |
| GET /resumen | Resumen personal |
| GET / | Página personal |
| GET /supervision | Página global autorizada |
| GET /supervision/{id} | Detalle global autorizado |
| GET /{id} | Detalle personal |
| PATCH /{id}/read | Reconocer `{revision}` propia |
| PATCH /read-all | Reconocer exclusivamente propias |
| PATCH /{id}/resolve | Cierre manual permitido con motivo |
| GET/PATCH /preferencias | Preferencia personal `{desktop_enabled}` |
| POST /escritorio/reclamar | `{items:[...]}` de revisiones autorizadas |
| POST /{id}/retry-email | Reintento administrativo; confirmación de resultado incierto |
| GET /reportes/resumen | Reporte autorizado con filtros |

La página y lectura con revisión cambian contratos anteriores: actualizar API y SPA conjuntamente, sin mantener consumidores antiguos.

## Correo y recuperación

SMTP ausente es fallo de configuración. Sin credenciales ni excepciones SMTP crudas en logs. Coordinación durable por cuenta/destino, sin contraseña ni cuerpo persistidos. Las copias ADMIN no son trabajos de envío independientes.

Elegibilidad: cuenta/usuario/rol activos, sin primer login, cambio de contraseña obligatorio y clave inicial derivada coincidente con el hash vigente. Reintentar no modifica hash ni must_change_password. Si cambió la credencial se exige restablecimiento explícito.

Intento confirmado en BD antes de SMTP. Máximo tres intentos automáticos: inicial, +5 min y +30 min. Timeout de socket 10 s. Corte/timeout de entrega o intento abandonado: INCIERTO, sin reenvío automático. Reintento manual exige confirmar ese riesgo. Éxito confirmado cierra todas las copias del error. No se promete entrega exactamente una vez.

El resultado durable libera bloqueos de usuario/cuenta antes de publicar el aviso ADMIN. Si el proceso termina entre ambos pasos, el job vuelve a publicar el diagnóstico de estados FALLIDO/BLOQUEADO/INCIERTO sin autorizar otro envío por ese hecho. Republicar actualiza la misma incidencia abierta.

## Jobs Windows

`backend/scripts/run_notification_checks.py`: modos `daily` y `retry-emails`. Bloqueo PostgreSQL por modo, keyset en lotes de 200, contadores efectivos y salida fallida ante errores. Daily confirma cada origen por separado para no conservar bloqueos de destinatarios mientras adquiere el siguiente origen. Un fallo revierte ese origen y sus contadores; una conexión invalidada detiene el proceso.

Programación recomendada: daily a las 08:00 America/La_Paz; reintentos según frecuencia aprobada. Verificar tareas duplicadas. **No se crearon tareas Windows ni se ejecutaron jobs contra datos empresariales.**

## Migración y despliegue

`backend/alembic/versions/20261018_0014_notification_reliability.py` añade campos, tablas e índices, normaliza claves y conserva filas. Mantiene la canónica abierta más antigua por fecha/ID y cierra duplicados como DUPLICADA, con referencia y auditoría. No mezcla destinatarios ni inventa lecturas. El histórico queda consumido para escritorio.

`inspect_notification_duplicates.py` imprime SQL sin conectarse por defecto; inspección ejecutable restringida a testing. No aplica reparaciones.

Procedimiento empresarial ejecutado con autorización específica el 18/10/2026:

1. Confirmar destino, revisión previa 0013 y ausencia de grupos abiertos duplicados/tipos vacíos.
2. Identificar y pausar la API del proyecto; no se encontraron jobs activos ni tareas de notificaciones del proyecto habilitadas. Tomar los bloqueos de ambos modos de job durante respaldo/migración.
3. Generar respaldo custom con pg_dump 17.9. Verificar índice, lectura integral del archivo mediante pg_restore sin conexión y SHA-256.
4. Aplicar únicamente 0014 mediante Alembic y comprobar revisión, tablas nuevas, unicidad y conservación de filas.
5. Reanudar Uvicorn con el comando original `main:app --reload`. Comprobar arranque, health y CORS; verificar consultas de notificaciones sin mutaciones.

Se conservaron **16 filas antes y después**, con **0 grupos abiertos duplicados**.
Respaldo y manifiesto privados, fuera de Git:

```text
%LOCALAPPDATA%\BAB_VDOS\notification-migrations\20261018-021203-cd29f2dc56b34239a94cdbdbe01905eb\
  bellaarte_db_before_20261018_0014.dump
  manifest.json
  api-stdout.log
  api-stderr.log
```

Archivo: 214.213 bytes. SHA-256:
`523beba56e6149498b88ed89b853093f1ddd83d1707fae7328763054099310bb`.
La lectura del archivo no equivale a un ensayo completo de restauración, que no
se realizó en esta operación. El primer intento de mantenimiento abortó antes de
importar la configuración/conectarse a PostgreSQL por el directorio de trabajo
de la herramienta elevada; reanudó la API y se repitió con ubicación explícita.

El incidente 500 se debía a API nueva contra esquema 0013. El preflight CORS ya
respondía 200 con `http://localhost:5173` permitido; no se ampliaron orígenes.
Después del despliegue, `/health` devuelve 200 y los tres GET protegidos sin sesión
devuelven 401 con cabecera CORS correcta. Las consultas reales de preferencias,
resumen y listado pasaron en una transacción de solo lectura. La comprobación
HTTP con la sesión del navegador del usuario queda a la recarga de la SPA; no se
generaron tokens de cuentas reales ni se alteraron credenciales para verificarlo.

Downgrade no reabre duplicados reparados ni sustituye restaurar un respaldo. No se modifican migraciones aplicadas anteriores.

## Pruebas y resultados

Desde raíz, suite sin conexiones:

```powershell
.\backend\venv\Scripts\python.exe -B .\backend\scripts\run_base_tests.py
```

El runner excluye integración y bloquea PostgreSQL/SMTP/procesos externos. La integración exige credenciales de testing, directorio temporal sin .env, manifiesto, identidad del servidor y marcador `testing_control.instance`. Ver [estrategia y operación](ESTRATEGIA_PRUEBAS.md).

Verificación final del 18/10/2026:

| Comprobación | Resultado |
| --- | --- |
| Backend base, contratos y API con dobles | 146 aprobadas |
| Integración PostgreSQL 17.9 | 24 aprobadas |
| Vitest: transporte, componentes y errores de formulario | 20 aprobadas |
| ESLint | Sin errores |
| pip check | Sin dependencias incompatibles |
| Compilación Vite 6.4.1 | Correcta en temporal; aviso de chunk mayor de 500 kB |

Integración real: unicidad con NULL, UPSERT concurrente, lectura/revisiones y carrera de lectura masiva, claims concurrentes, ciclos de stock Boutique/Taller, recuperación/desactivación, rollback observado desde otra sesión, desactivación concurrente de destinatario, estado durable de correo antes de publicación, JWT/Casbin reales y reparación de duplicados sintéticos por migración.

Clúster autorizado: raíz propia en LOCALAPPDATA, puerto 55432, base `bab_vdos_testing`, roles bab_test_admin/migrator/runner y secretos DPAPI externos a Git. Aprovisionado con autorización y detenido al finalizar pruebas. PowerShell sin switches muestra solo propuesta; `-RunTests` reutiliza exclusivamente ese clúster. No crearlo de nuevo ni eliminarlo como procedimiento rutinario.

Límites: sin E2E de navegador real, entrega nativa del sistema operativo, SMTP real, programación Windows ni benchmark de volumen productivo certificados. Componentes usan jsdom y dobles. Corrección validada en testing y esquema empresarial actualizado con autorización; queda la comprobación visual con sesión existente del usuario.
