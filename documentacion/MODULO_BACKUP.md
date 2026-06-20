# MÓDULO DE BACKUPS DE BASE DE DATOS

## BELLAARTE BOUTIQUE

### Resumen funcional

El módulo `Backups` permite generar respaldos lógicos completos de la base de datos con `pg_dump`, registrar cada ejecución en `backup_bd`, descargar los archivos exitosos desde el panel `ADMIN` y mantener trazabilidad en auditoría.

La versión actual quedó definida con estas reglas:

- solo `ADMIN` puede listar, ver, generar y descargar backups;
- el backup automático oficial se ejecuta cada domingo a las `02:00` a. m. hora `America/La_Paz`;
- el backup manual también se ejecuta desde la UI, de forma síncrona y bloqueante;
- mientras un backup está en proceso, el sistema queda temporalmente bloqueado para operaciones normales;
- la restauración no se expone desde la aplicación.

## Estructura de base de datos

Se agregan:

- enum `tipo_backup_bd`
  - `LOGICO_COMPLETO`
  - `SEMANAL`
  - `MANUAL`
- enum `estado_backup_bd`
  - `EN_PROCESO`
  - `EXITOSO`
  - `FALLIDO`
- tabla `backup_bd`

Campos principales:

- `bkp_id`
- `usu_id`
- `bkp_tipo`
- `bkp_estado`
- `bkp_origen`
- `bkp_nombre_archivo`
- `bkp_ruta_archivo`
- `bkp_tamano_bytes`
- `bkp_hash_sha256`
- `bkp_fec_inicio`
- `bkp_fec_fin`
- `bkp_pg_dump_version`
- `bkp_db_nombre`
- `bkp_observacion`
- `bkp_error`

Checks principales:

- `bkp_origen` solo admite `AUTOMATICO` o `MANUAL`
- `bkp_tamano_bytes >= 0`
- `EN_PROCESO` exige `bkp_fec_fin = NULL`
- `EXITOSO` y `FALLIDO` exigen `bkp_fec_fin` con valor

Índices operativos:

- `bkp_fec_inicio`
- `bkp_estado + bkp_fec_inicio`
- `bkp_tipo + bkp_fec_inicio`
- `bkp_origen + bkp_fec_inicio`
- `usu_id + bkp_fec_inicio`
- `bkp_nombre_archivo`

## Flujo técnico

### Generación manual

1. `ADMIN` entra a `/app/backups`.
2. Presiona `GENERAR BACKUP AHORA`.
3. El backend toma un candado compartido de runtime.
4. Se crea el registro `backup_bd` con `EN_PROCESO`.
5. Se ejecuta `pg_dump -Fc`.
6. Se calcula tamaño, hash SHA-256 y versión de `pg_dump`.
7. El registro pasa a `EXITOSO` o `FALLIDO`.
8. Se libera el candado.
9. El sistema vuelve a operar normalmente.

### Generación automática

La automatización oficial se resuelve con:

```powershell
python scripts/run_backup_job.py --mode weekly
```

Debe programarse externamente:

- Windows: Programador de tareas
- Linux: `cron` o `systemd timer`
- macOS: `launchd` o cron según despliegue

Horario oficial:

- domingo
- `02:00` a. m.
- zona `America/La_Paz`

## Bloqueo temporal del sistema

Durante la generación del backup se crea un lock file compartido. El backend lo usa para:

- impedir un segundo backup simultáneo;
- devolver `503` a rutas no exentas;
- mostrar el mensaje:
  - `EL SISTEMA ESTÁ GENERANDO UN BACKUP. ESPERE A QUE FINALICE.`

Rutas exentas:

- `login`
- `logout`
- `refresh`
- `auth:me`
- lecturas `GET` del módulo `backups`
- `health`

## Variables de entorno

Agregar en `backend/.env`:

```env
BACKUP_DIR=./storage/backups
PG_DUMP_PATH=
BACKUP_TIMEZONE=America/La_Paz
BACKUP_FILENAME_PREFIX=bellaarte_backup
```

Notas:

- `PG_DUMP_PATH` es opcional si `pg_dump` ya está en el `PATH`.
- `BACKUP_DIR` se resuelve relativo a `backend/` cuando no es ruta absoluta.

## API disponible

- `GET /api/v1/backups`
- `GET /api/v1/backups/status/active`
- `GET /api/v1/backups/{backup_id}`
- `POST /api/v1/backups/run`
- `GET /api/v1/backups/{backup_id}/check-file`
- `GET /api/v1/backups/{backup_id}/download`

Filtros del listado:

- `tipo`
- `estado`
- `origen`
- `usuario_id`
- `date_from`
- `date_to`
- `search`

## Frontend

Ruta SPA:

- `/app/backups`

Capacidades:

- tabla histórica
- filtros
- resumen de último exitoso, último fallido y total
- detalle en drawer
- verificación física del archivo
- descarga directa del `.dump`
- modal bloqueante durante generación manual

## Seguridad

Permisos nuevos:

- `backups:list`
- `backups:view`
- `backups:create`
- `backups:download`

Asignación actual:

- `ADMIN`: todos
- demás roles: ninguno

Reglas obligatorias:

- no descargar backups fallidos
- no descargar backups cuyo archivo no exista
- no guardar backups en rutas públicas del frontend
- no versionar `storage/backups/`
- auditar inicio, éxito, fallo y descarga

## Auditoría

Eventos registrados:

- `BACKUP_MANUAL_STARTED`
- `BACKUP_MANUAL_COMPLETED`
- `BACKUP_AUTOMATIC_STARTED`
- `BACKUP_AUTOMATIC_COMPLETED`
- `BACKUP_FAILED`
- `BACKUP_DOWNLOADED`
- `BACKUP_DOWNLOAD_FAILED`

Todos quedan asociados al módulo `BACKUPS`.

## Operación y retención

Recomendación inicial:

- conservar backups semanales al menos 3 meses;
- mover respaldos históricos críticos a almacenamiento externo;
- probar restauración manual periódicamente en una base de prueba.

Esta versión no implementa:

- restauración desde UI;
- backups incrementales;
- backups diferenciales;
- eliminación automática avanzada.

## Pruebas realizadas/esperadas

Escenarios clave:

- creación correcta de enums, tabla, checks e índices;
- rechazo de segundo backup simultáneo;
- error controlado si `pg_dump` no existe;
- registro `FALLIDO` cuando el proceso no genera archivo;
- descarga válida solo si el backup fue `EXITOSO`;
- bloqueo temporal del sistema mientras existe el lock activo;
- ejecución del script semanal sin depender del frontend.
