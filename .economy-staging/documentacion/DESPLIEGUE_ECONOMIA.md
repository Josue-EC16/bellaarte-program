# Despliegue controlado de Economía

Estado 18/10/2026: código y migraciones preparados en `.economy-staging`. Las migraciones económicas se probaron en PostgreSQL exclusivo de testing; **no se aplicaron a bellaarte_db:5432**. El código activo original conserva su versión para que Uvicorn `--reload` no cargue modelos nuevos contra un esquema anterior.

## Material revisable

- [Reglas del módulo](MODULO_INGRESOS_EGRESOS_CORTE_CAJA.md).
- [Contratos API](CONTRATOS_API_ECONOMIA.md).
- [Resultados y matriz de cobertura](REPORTE_IMPLEMENTACION_ECONOMIA.md).
- `../ECONOMIA_CAMBIOS.patch`: diff de los archivos preparados respecto a la copia local de inicio; conserva cambios previos, incluso no confirmados en Git.
- `../cambios.json`: archivos y SHA-256 de origen/destino. Antes de promover, comparar origen actual con hash de inicio; cualquier cambio concurrente requiere integración explícita.
- `../baseline.json`: inventario de partida de la copia aislada. No contiene credenciales.

No copiar `.env`, dependencias, scripts temporales de validación ni el directorio completo a ciegas. El paquete incluye únicamente diferencias autorizadas. Los archivos de Skills, AGENTS.md y configuraciones globales no forman parte de la entrega económica.

## Autorización pendiente

La siguiente operación exige autorización concreta del propietario: ventana de mantenimiento, respaldo empresarial, aplicación de revisiones 0015/0016 a bellaarte_db y promoción coordinada del código. Este documento no ejecuta esas acciones ni implica autorización automática.

## Secuencia para la ventana autorizada

1. Confirmar puerto 5432 y base bellaarte_db efectivos sin imprimir secretos; registrar revisión Alembic actual. La cadena preparada parte de 0014. Si difiere, detener y revisar, sin aplicar a otro destino.
2. Revisar diff/hashes y cambios concurrentes. Verificar las versiones backend/frontend emparejadas y reservar una ventana sin escritores HTTP, tareas programadas ni scripts.
3. Detener de forma controlada API y jobs; desactivar el watcher durante la promoción. No iniciar la nueva API antes del esquema compatible.
4. Generar respaldo empresarial en ubicación privada y verificar archivo, hash, lectura y procedimiento de restauración previamente ensayado en destino aislado. Un hash por sí solo no acredita recuperación. No restaurar sobre la instancia real como prueba.
5. Inventariar cortes abiertos/estados históricos y anomalías. Acordar cómo cerrar manualmente cada corte legado, sin inferir medios de pago ni crear egresos por anulaciones previas. La migración no cierra cortes ni los certifica.
6. Promover las diferencias revisadas de backend con la API aún detenida y configuración empresarial conservada. Aplicar Alembic hasta `20261018_0016` con su intérprete existente y conexión verificada. No seeds, create_all ni instalaciones.
7. Validar revisión, columnas/FK/índices, funciones y triggers. Las revisiones usan DDL transaccional; un error aborta y exige diagnóstico, no deshabilitar protecciones ni marcar revisión manualmente.
8. Compilar/promover frontend emparejado con las dependencias existentes. El config temporal `vite.validation.config.mjs` solo enlaza dependencias para la copia aislada: no se promueve. Conservar el vite.config.js original.
9. Arrancar API; efectuar smoke de autenticación y lecturas autorizadas (resumen, contexto, cortes, reportes/CSV). Confirmar manejo de cortes legados y navegación. No efectuar ventas o reembolsos ficticios sobre datos empresariales.
10. El cierre legado y apertura del corte nuevo son acciones empresariales explícitas de ADMIN. Contar/conciliar lo disponible con responsables, observaciones e información histórica; no certificar retrospectivamente.
11. Rehabilitar jobs después de verificar compatibilidad. Registrar fecha, versiones, revisiones, responsable y verificaciones. Conservar evidencia y monitorear errores/tiempos de espera.

## Recuperación

Antes de movimientos controlados, evaluar reversión del despliegue y esquema bajo la misma ventana; no asumir downgrade inocuo. La revisión 0015 rechaza downgrade si ya existen movimientos, constancias, solicitudes o cortes controlados. La revisión 0016 solo reemplaza una función de custodia y puede conservarse con una corrección hacia adelante.

Después de iniciar movimientos controlados, preferir corrección hacia adelante. No borrar ledger, constancias o solicitudes para forzar downgrade, ni sobrescribir un snapshot. Una recuperación desde respaldo debe tratar operaciones posteriores explícitamente y requiere autorización específica; no es un rollback automático del código.

## Pruebas reproducibles sin tocar la instancia empresarial

Desde la raíz Windows, para la copia preparada:

```powershell
.\backend\venv\Scripts\python.exe -B .\.economy-staging\backend\scripts\run_base_tests.py
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\.economy-staging\backend\scripts\provision_notification_test_postgres.ps1 -RunTests -PythonExecutable .\backend\venv\Scripts\python.exe
```

El segundo comando usa únicamente la instancia existente en `%LOCALAPPDATA%\BAB_VDOS\postgresql-testing`, puerto 55432, base bab_vdos_testing, roles exclusivos y marcador de identidad. No usar `-Provision` para sobrescribirla. Arranca esa instancia si está detenida y la detiene al terminar si la inició. Valida identidad y bloquea conexiones alternativas, SMTP y procesos durante pytest.

Tras promoción se usan los mismos scripts en backend, sin prefijo `.economy-staging` ni override de intérprete. No sustituirlos por pytest directo con `.env` empresarial.

La mayoría de casos PostgreSQL revierten su transacción externa. Los casos concurrentes necesitan commits observables desde sesiones independientes y conservan únicamente evidencia sintética `QA_ECON_*` en testing. No se borran registros financieros inmutables ni se desactivan triggers para limpiar. Planificar rotación de una instancia de prueba nueva mediante un procedimiento explícito si crece el volumen.
