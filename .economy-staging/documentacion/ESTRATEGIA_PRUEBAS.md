# Pruebas base e integración aislada — BAB_VDOS

Referencia histórica: 17/10/2026. Actualización de notificaciones: 18/10/2026,
al final del documento. Entorno: Windows nativo y PowerShell.

## Estado y alcance

La fase 1 estabiliza los tests existentes y documenta la futura integración con
PostgreSQL. No cambia reglas comerciales, contratos API ni dependencias. La
instancia de testing descrita aquí **no estaba creada al cierre del 17/10/2026**.
La actualización del 18/10/2026 documenta su provisión autorizada y resultados;
los inventarios y resultados de esta primera sección son históricos.

Inventario revisado por `qa_testing` y `backend`: 72 funciones de prueba backend
en ocho archivos y tres casos frontend. El resultado histórico de 71 backend
aprobadas y una fallida no se toma como resultado de esta ejecución.

| Nivel observado | Casos | Alcance real |
| --- | ---: | --- |
| Unitarias, contratos y helpers backend | 68 | Pydantic, catálogos de permisos, JWT/hash y helpers con dobles |
| Componentes backend con archivos temporales/mocks | 3 | Locks y generación simulada de backups |
| Funcional HTTP de middleware | 1 | Bloqueo por backup y acceso a health; persistencia sustituida |
| Unitarias frontend | 3 | Errores 422/409 y campos anidados; sin DOM ni HTTP |
| Integración PostgreSQL, E2E y concurrencia | 0 | No certificadas por los casos anteriores |

`pytest.ini` limita el descubrimiento a `backend/tests/test_*.py`.
`backend/tests/conftest.py` solo añade el backend a `sys.path`: ejecutar Pytest
directamente no proporciona aislamiento de base. Vitest usa la configuración
Vite existente, sin setup DOM; los tres casos actuales necesitan entorno Node.
Las dependencias se reutilizan sin instalar ni actualizar paquetes.

## Correcciones y ejecución de la suite base

El test `test_order_base_payload_requires_discount_reason` utilizaba una entrega
fija del 20/06/2026. El schema valida primero que la fecha no haya pasado, por lo
que no llegaba al motivo de descuento. Se cambia únicamente la fecha por mañana,
con `date.today() + timedelta(days=1)`, conservando el payload sin motivo y su
aserción original. No se cambia el validador comercial.

El test de middleware de backups sustituye `app.main.SessionLocal` y
`cleanup_stale_backup_lock` antes de crear la aplicación. Conserva los resultados
503/200 y comprueba que ambas solicitudes invoquen la limpieza y cierren la sesión simulada.
Un GET puede ejecutar consultas y limpieza; no basta con que no sea un POST.

Desde la raíz del repositorio, usar el lanzador de la suite base:

```powershell
.\backend\venv\Scripts\python.exe -B .\backend\scripts\run_base_tests.py
```

El lanzador prepara un proceso hijo antes de importar la aplicación: directorio
temporal sin `.env`, variables de configuración sintéticas, backups y temporales
propios, plugins externos deshabilitados y conexiones PostgreSQL bloqueadas.
También bloquea SMTP y la creación de procesos externos por los mecanismos
utilizados en esta suite. Son protecciones para los tests revisados, no un sandbox
general para ejecutar código arbitrario. No es un runner de integración y no
admite una conexión empresarial como alternativa.
La colección comprueba las políticas generadas contra `policy.csv` mediante
lectura, sin sincronizarlo en disco ni sustituir la autorización de Casbin.
Una discrepancia detiene la ejecución en vez de reescribir el archivo.

No ejecutar `backend/test_db.py` ni scripts de conexión para validar esta suite.
No usar filtros `-k` como protección frente a imports: la colección ocurre antes
del filtrado. El lanzador selecciona exclusivamente tests bajo `backend/tests`.

Desde `frontend/`:

```powershell
pnpm.cmd exec vitest run src/components/forms/formErrorUtils.test.js --no-cache --environment node
pnpm.cmd lint
```

No se requiere build para estos cambios de tests. Registrar errores de permisos
o herramientas como límites de ejecución, sin reinstalar dependencias para
ocultarlos. Los resultados efectivos de esta fase figuran al final del documento.

## Matriz de cobertura crítica

Toda prueba pendiente de operaciones persistidas necesita PostgreSQL aislado.
Los contratos existentes no demuestran la transacción comercial ni la
autorización efectiva del endpoint.

| Flujo | Existente | Pendiente sobre datos sintéticos |
| --- | --- | --- |
| Ventas y Boutique | Payload, descuento/motivo, snapshot y permisos declarados | Alta, precio desde inventario, stock exacto, insuficiencia, moneda/conversión y comprobante único |
| Pagos parciales | Payload multimoneda y snapshot | Dos abonos, saldos intermedio/final, sobrepago y estados/entrega |
| Anulaciones/devoluciones | Contrato y rechazo 409 de rutas antiguas | Coordinador económico, egreso, ingreso histórico, reversión de stock/saldo/comprobante y duplicación |
| Materiales | Payload de entrada/salida y unidad | Movimientos persistidos, disponibilidad, unidad incompatible, desactivación/reactivación única |
| Fletes | Descuento, fechas y condiciones de arreglo | Reserva, entrega, devolución, garantía separada, disponibilidad y usos |
| Autorización HTTP | Catálogos de permisos y JWT válido | 401/403, JWT inválido/expirado/tipo incorrecto, cuenta/usuario/rol inactivos y propiedad de recursos |
| Integridad/atomicidad | Auditoría con DummySession y rechazos con db=None | Fallos intermedios sin operación, stock, saldo, comprobante o egreso parcialmente persistidos |
| Concurrencia | Sin casos observados | Última unidad, pagos simultáneos, doble reversión/reembolso, salidas Taller y reservas/devoluciones flete |

Las devoluciones parciales sucesivas/cero y otras brechas descritas en AGENTS.md
requieren decisiones empresariales específicas. No convertir sus limitaciones
actuales en reglas aprobadas ni introducir cambios para obtener tests verdes.

## Propuesta de PostgreSQL exclusivo de testing

**Propuesta histórica del 17/10/2026.** Su ejecución autorizada y los límites
actuales se registran en la actualización del 18/10/2026 al final.

| Recurso | Valor propuesto |
| --- | --- |
| Binarios | PostgreSQL 17.9 ya instalado en Laragon; reutilizar ejecutables, no datos/configuración |
| Raíz propia | `%LOCALAPPDATA%\BAB_VDOS\postgresql-testing` |
| Datos y configuración | Subdirectorio `data`, con postgresql.conf y pg_hba.conf exclusivos |
| Logs y temporales | Subdirectorios `logs` y `runtime` de la raíz propia |
| Escucha | `127.0.0.1`, puerto `55432`; abortar si está ocupado, sin cambiar otro servicio |
| Base | `bab_vdos_testing` |
| Administración | `bab_test_admin`, exclusivo de este clúster |
| Migraciones | `bab_test_migrator`, propietario de la base, sin superusuario/CREATEDB/CREATEROLE |
| Tests | `bab_test_runner`, permisos DML y secuencias necesarios, sin DDL ni privilegios administrativos |
| Autenticación | SCRAM, contraseñas propias suministradas fuera de Git y logs; sin autenticación trust |

No registrar un servicio Windows ni modificar PATH, variables persistentes,
puertos, usuarios, bases, configuración o directorios de la instancia del ERP.
Compartir la instalación de binarios no debe compartir ningún recurso mutable.
Si faltan permisos o componentes, detener y documentar; no instalar ni elevar
privilegios de forma implícita.

### Procedimiento posterior sujeto a autorización

1. Identificar y autorizar la raíz absoluta, puerto, roles/base y operaciones
   permitidas. Verificar que el directorio de datos no exista o esté vacío y que
   el puerto esté libre. Nunca reutilizar un clúster existente.
2. Inicializar con `initdb.exe` el directorio propio, UTF-8 y SCRAM. Suministrar
   credenciales por un medio temporal protegido; no ponerlas en comandos/logs.
3. Configurar únicamente los archivos de ese clúster y arrancarlo con
   `pg_ctl.exe`, `-D` apuntando al directorio propio y log propio. No parar,
   reiniciar ni consultar la base comercial para preparar este entorno.
4. Crear únicamente los roles/base anteriores, restringir acceso público a la
   base de testing y conceder al runner los permisos mínimos necesarios.
5. Crear un manifiesto externo del arnés con la identidad del clúster y un
   identificador aleatorio de provisión. Antes de DDL/DML o limpieza, validar
   host/puerto/base/rol exactos, `current_database()`, `current_user`, puerto
   efectivo, directorio autorizado e identificador de provisión. Un nombre con
   sufijo `_test` no basta. Nunca recurrir a `DATABASE_URL`/`DB_*` empresariales.
6. Preparar el proceso de migración desde un directorio sin `.env`, con URL de
   testing explícita y configuración sintética antes de importar settings.
   Alembic sustituye su URL por la de settings: un INI alternativo no aísla por
   sí solo. Ejecutar la cadena de migraciones hasta head sobre la base vacía.
7. Comprobar `pgcrypto`, funciones y triggers de auditoría de la migración 0011,
   restricciones e índices reales. El administrador prepara la extensión si
   los privilegios del migrator no bastan. No usar `create_all()` como sustituto.
8. Cargar fixtures mínimas exclusivamente sintéticas: roles/cuentas/usuarios,
   clientes, monedas/cambios, comprobantes y entidades de cada flujo. No usar
   seeds que creen o reseteen administradores ni restaurar dumps empresariales.
9. Probar primero aislamiento/rollback; habilitar luego servicios, API y por
   último concurrencia. El arnés de integración será independiente del lanzador
   sin base de esta fase y exigirá activación explícita.
10. Cerrar clientes/sesiones/engines. Detener exclusivamente este clúster si la
    autorización lo permite. Conservar datos sintéticos fallidos para diagnóstico;
    eliminación, recreación y limpieza deben estar autorizadas y volver a validar
    todos los identificadores. Nunca ejecutar limpieza genérica sobre una URL.

La presencia local de binarios y `pgcrypto.control` se comprobó por lectura.
Al cerrar esta fase, la instalación de la extensión y toda la cadena Alembic
seguían sin ejecutarse en una base nueva. Ver la actualización posterior.

## Diseño de transacciones y concurrencia futuras

- Secuenciales: conexión por caso, transacción externa y
  `Session(bind=connection, join_transaction_mode="create_savepoint")`. Cerrar y
  hacer rollback externo incluso si los servicios ejecutan commit. Mantener una
  línea base sintética para comprobar ausencia de cambios tras errores.
- Atomicidad real: además del rollback de limpieza, inyectar fallos antes del
  commit y verificar desde una sesión nueva lo que quedó persistido. No afirmar
  rollback empresarial únicamente porque el arnés revierte el caso al terminar.
- API: mantener JWT/Casbin reales y cuentas sintéticas. Aislar `get_db` y las
  fábricas SessionLocal directas usadas por lifespan/middleware; no compartir
  sesiones entre hilos. La auditoría de un 403 también puede hacer commit.
- Efectos externos: sustituir SMTP, pg_dump y otros procesos por dobles; archivos
  y backups únicamente en temporales de testing. La sincronización de políticas
  no debe sobrescribir el archivo del repositorio.
- Concurrentes: datos iniciales confirmados, sesiones/conexiones independientes,
  commits reales, barreras antes de la decisión crítica y tiempos máximos de
  bloqueo. No reutilizar la transacción de una sola conexión. Preparar una base
  desechable por grupo mediante el rol de provisión y autorización específica.
- Prioridad: última unidad (como máximo una venta), dos pagos cuya suma excede la
  deuda (sin sobrepago) y devolución simultánea del mismo origen (sin doble
  egreso/reversión). Después Taller, fletes y correlativos de comprobantes.
- No asumir que el advisory lock de correlativos protege decisiones anteriores
  de stock/saldo. No exigir secuencias sin huecos: sus valores no hacen rollback.

Antes de corregir concurrencia comercial, reproducir cada caso en este entorno,
registrar la invariante aprobada, el fallo y las transacciones involucradas.
Diseñar entonces bloqueos/restricciones y sus regresiones en una tarea propia,
sin debilitar permisos ni ampliar el alcance de esta fase.

## Resultados de esta fase

Verificaciones ejecutadas el 17/10/2026:

| Verificación | Resultado |
| --- | --- |
| Selección conservadora backend, después del ajuste de fecha | 48 aprobadas, 1,29 s |
| Suite completa mediante `run_base_tests.py` | 72 aprobadas, 1,70 s |
| Vitest, archivo `formErrorUtils.test.js`, entorno Node | 3 aprobadas; Vitest 3.2.4 |
| ESLint sin `--fix` | Código de salida 0 |
| `python -B -m pip check` del venv existente | Sin requisitos incompatibles |
| Sondeo del lanzador sin red/base | Bloqueó psycopg2, SQLAlchemy, SMTP y subprocess; los intentos capturados también fuerzan resultado fallido |
| Selección fuera de `backend/tests` | Rechazada por el lanzador |
| Revisión independiente de QA | Sin defectos bloqueantes para los 72 casos actuales |

No se reejecutó el test original con la fecha vencida antes de editarlo; su causa
se confirmó por el orden de validaciones. El resultado de 48 casos ya corresponde
al test corregido y no se presenta como una medición previa al cambio.

La primera ejecución de Vitest y ESLint mediante pnpm encontró errores EPERM del
sandbox al leer los paquetes instalados. El reintento fuera del sandbox con pnpm
no resolvió los comandos. La verificación final usó Node y los archivos locales
existentes, fuera del sandbox con autorización, desde `frontend/`:

```powershell
node.exe .\node_modules\vitest\vitest.mjs run src/components/forms/formErrorUtils.test.js --no-cache --environment node
node.exe .\node_modules\eslint\bin\eslint.js .
```

Al cierre del 17/10/2026 no se instalaron dependencias ni se modificaron archivos
frontend; no se habían ejecutado integración PostgreSQL, migraciones ni concurrencia,
y no existía instancia de testing. La suite de esa fecha no acreditaba esos
escenarios. Las operaciones empresariales reales permanecen fuera de las pruebas.

## Actualización: notificaciones e instancia aislada, 18/10/2026

Esta sección sustituye el estado «solo propuesta» anterior para el entorno de
testing. Se implementó la corrección de notificaciones, sus pruebas y runners.
Se aprovisionó con autorización explícita un clúster PostgreSQL 17.9 independiente:

| Recurso | Configuración efectiva |
| --- | --- |
| Raíz | `%LOCALAPPDATA%\BAB_VDOS\postgresql-testing` |
| Datos/configuración | Subdirectorio propio `data` |
| Logs/temporales | `logs` y `runtime` propios |
| Escucha | `127.0.0.1:55432` |
| Base | `bab_vdos_testing` |
| Roles | `bab_test_admin`, `bab_test_migrator`, `bab_test_runner` |
| Protección | SCRAM, contraseñas aleatorias protegidas con DPAPI fuera de Git |
| Identidad | Manifiesto propio y `testing_control.instance` |
| Esquema | Cadena Alembic hasta `20261018_0014`; pgcrypto |
| Estado al finalizar | Servidor de testing detenido |

No se crearon servicios Windows ni variables persistentes; no se cambiaron
usuarios, puerto, datos o configuración de la instancia empresarial
`bellaarte_db:5432`. No se usaron dumps reales ni seeds empresariales.

### Ejecución reproducible

Desde raíz, base sin conexiones:

```powershell
.\backend\venv\Scripts\python.exe -B .\backend\scripts\run_base_tests.py
```

Integración, reutilizando exclusivamente el clúster ya aprovisionado:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\provision_notification_test_postgres.ps1 -RunTests
```

Sin switches, PowerShell solo muestra propuesta. `-Provision` se niega a
sobrescribir una raíz existente; no es necesario para repetir pruebas. El script
reutiliza binarios instalados de Laragon, desencripta credenciales en el proceso,
suprime variables PG heredadas y restaura su entorno al terminar. Si inicia el
servidor propio, lo detiene en finally. No elimina el clúster ni sus archivos.
ExecutionPolicy Bypass se limita al proceso invocado, sin cambio global.

`run_notification_integration.py` no crea ni inicia servidores. Exige manifiesto
y URLs explícitos, sin opciones de redirección ni fallback a `.env`/DB_*.
Comprueba host, puerto, base, roles, directorio efectivo y marcador antes de
migrar. Ejecuta en un temporal sin `.env`, permite conexiones solo a testing,
bloquea SMTP/procesos externos y verifica policy.csv sin escribirlo. El runner
recibe DML/secuencias; el migrator ejecuta DDL sin superusuario. Las fixtures
confirman y limpian exclusivamente registros sintéticos por sus identificadores.
El ensayo de reparación ejecuta downgrade/upgrade dentro de una transacción
revertida; no elimina el esquema compartido de testing al finalizar.

Frontend, desde `frontend/`, con herramientas locales existentes:

```powershell
node.exe .\node_modules\vitest\vitest.mjs run --no-cache --environment node
node.exe .\node_modules\eslint\bin\eslint.js .
```

Los tests de componentes declaran jsdom en su archivo; las utilidades usan Node.
La compilación Vite se ejecutó con `--outDir` hacia un temporal nuevo fuera del
repositorio, sin vaciar directorios existentes. No se instalaron dependencias.
Se usó ejecución autorizada fuera del sandbox para PostgreSQL y herramientas
frontend, tras las limitaciones de permisos del entorno.

### Resultados finales

| Comprobación | Resultado |
| --- | --- |
| Backend base completo, sin persistencia | 146 aprobadas, 2,47 s |
| Integración PostgreSQL | 24 aprobadas, 1,78 s |
| Vitest | 20 aprobadas: 10 transporte, 7 componentes, 3 errores de formulario |
| ESLint | Código de salida 0 |
| pip check | Sin requisitos incompatibles |
| Vite 6.4.1, salida temporal | Correcto, 20,87 s; aviso de chunk mayor de 500 kB |

El bundle principal permanece en unos 2,27 MB sin comprimir. No se ocultó el
aviso ni se amplió este trabajo a una reorganización general de bundles.

| Cobertura de notificaciones | Evidencia y alcance |
| --- | --- |
| Episodios y claves nulas | Índice real rechaza duplicados; UPSERT desde dos sesiones devuelve una incidencia |
| Stock Boutique/Taller | Bajo→cero→bajo→cero conserva episodio/revisión; recuperación y recaída crean otro |
| Desactivación y atomicidad | Origen/tipo cierra alerta; rollback de stock y alerta comprobado desde otra sesión |
| Elegibilidad concurrente | Desactivar cuenta antes/después de sincronizar no deja copias abiertas |
| Lectura y escalamiento | Lectura antigua rechazada; lectura masiva concurrente no consume revisión nueva |
| Escritorio | Claims de dos sesiones sin duplicar, recarga sin repetir, exclusión de backlog/leídas/resueltas |
| Autorización | JWT, cuenta y Casbin reales: 401, 403, propiedad y supervisión explícita en PostgreSQL |
| Migración | Duplicados sintéticos conservados, canónica estable, cierre/auditoría y rollback del ensayo |
| Correo | SMTP con dobles; elegibilidad, presupuesto, incertidumbre, secretos y credenciales sin mutación |
| Bloqueos de correo | PostgreSQL verifica resultado durable y cuenta desbloqueada antes de publicar a ADMIN |
| Interfaz | Paginación, acciones, errores, polling, limpieza y presentación con dobles/jsdom |

### Límites y siguiente etapa

La corrección requiere migración 0014 y despliegue coordinado API/SPA. Después de
la validación de testing, el usuario autorizó explícitamente el mantenimiento
empresarial descrito en la sección siguiente y en el
[módulo de notificaciones](MODULO_NOTIFICACIONES.md).

No se certificaron E2E en navegador real, entrega nativa del sistema operativo,
SMTP real, tareas Windows ni rendimiento con volumen productivo. Tampoco se
certifican por estas 24 pruebas las transacciones completas de venta, pagos,
devoluciones económicas o reservas: la matriz empresarial anterior sigue siendo
la guía para esa etapa. El aislamiento ya está disponible para reproducir esos
casos con fixtures mínimas, sesiones independientes y fallos antes del commit.
Priorizar última unidad, sobrepago simultáneo y doble devolución antes de cambiar
sus bloqueos o reglas comerciales.

## Mantenimiento empresarial autorizado del 18/10/2026

Esta operación es un despliegue autorizado, separado de las pruebas con datos
sintéticos. Se aplicó exclusivamente `20261018_0014` a `bellaarte_db:5432`, con
API pausada, bloqueo de jobs y respaldo custom privado fuera del repositorio.
Se verificaron índice del archivo, lectura integral sin restaurar y SHA-256.
No se certifica por ello una restauración completa del ERP.

Resultados: revisión 0014 confirmada; 16 notificaciones antes y después; cero
grupos abiertos duplicados. Preferencias, resumen y listado pasaron contra la
base migrada mediante servicios reales en transacción de solo lectura. No se
crearon operaciones comerciales de prueba ni se hicieron lecturas/mutaciones
de notificaciones para simular interacciones de usuarios.

La API se reanudó con `main:app --reload`. Health devolvió 200. Los GET protegidos
sin token devolvieron 401 con `Access-Control-Allow-Origin: http://localhost:5173`.
No se generaron tokens de cuentas reales para comprobar HTTP autenticado; esa
verificación visual requiere recargar la sesión existente en la SPA.
El detalle del respaldo y manifiesto está en el documento del módulo.


## Consolidación de Economía — 18/10/2026

La entrega económica se valida en `.economy-staging` sin promoverla a la API con
reload. Ver [reporte económico](REPORTE_IMPLEMENTACION_ECONOMIA.md) para resultados
y matriz, y [despliegue](DESPLIEGUE_ECONOMIA.md) para reproducción y activación.

Se añaden casos reales en PostgreSQL para venta, pago, reembolsos sucesivos,
cancelación independiente, garantías, egresos/correcciones, cortes, snapshots,
reportes y autorización JWT/Casbin. Sesiones independientes prueban última unidad,
sobrepago, reembolso máximo, cierre contra gasto e idempotencia simultánea. Un
observador verifica rollback de fuente, stock, ledger y resultado idempotente.

La mayoría de fixtures revierten una transacción externa. Los casos concurrentes
necesitan commits compartidos y dejan evidencia sintética QA_ECON únicamente en
la instancia de testing. No usan datos empresariales ni deshabilitan triggers.
La instancia tiene datos, puerto 55432, usuarios y base exclusivos; el lanzador
valida identidad antes de cargar configuración y migra solo ese destino.

Pruebas de notificaciones previas siguen vigentes y se ejecutan junto a las
regresiones económicas. Los resultados no certifican E2E visual completo,
rendimiento productivo, SMTP real ni restauración empresarial. No se extrapola un
porcentaje de cobertura a partir del número de casos.
