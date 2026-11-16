# Usuarios, colaboradores, roles y sesiones

Actualización: 03/11/2026. Implementación y migración `20261103_0022` aplicadas
con autorización expresa a `bellaarte_db:5432`, con respaldo privado verificado,
reinicio del backend original y comprobaciones HTTP. Ver despliegue al final.

## Identidad y administración

`usuarios` contiene la ficha personal; `cuentas` contiene acceso y un único rol.
`cuentas.usuario_id` es obligatorio y único: cada colaborador tiene **como máximo
una cuenta**. Una cuenta puede tener varias sesiones de navegador independientes.
Los nombres de acceso existentes permanecen estables al editar la identidad.

Solo el código técnico `ADMIN`, además de sus permisos Casbin, permite consultar
o administrar Usuarios y Roles. Los permisos de la interfaz no sustituyen los
controles del servidor. Un ADMIN puede editar, cambiar el rol, desactivar y
resetear otras cuentas, incluidas las de otros ADMIN.

Un ADMIN no puede desactivar su propia cuenta, deshabilitar su propia ficha ni
cambiar su propio rol. Debe intervenir otro ADMIN. Siempre queda al menos una
cuenta ADMIN con cuenta, colaborador y rol habilitados. Las reglas se verifican
en edición y cambio de estado. Un advisory lock transaccional serializa cambios
de seguridad, revalida al responsable después de esperar y protege la decisión
frente a cambios concurrentes. No se puede deshabilitar el rol ADMIN.

## Captura y contraseñas temporales

- Nombres y apellido paterno: mínimo dos letras; letras Unicode, acentos y
  espacios entre palabras. Normalización NFC, mayúsculas, extremos recortados y
  espacios interiores unificados. Los espacios no satisfacen el mínimo.
- CI: texto de 7 a 30 dígitos ASCII; conserva ceros iniciales. Se rechazan letras,
  separadores y espacios, sin eliminar silenciosamente contenido inválido.
- Celular: de 8 a 30 dígitos. Zona: contenido real, mínimo dos letras o números.
- Correo válido, extremos recortados y minúsculas. Apellido materno y dirección
  vacíos se representan como `null`. Se rechazan caracteres invisibles y de
  control; la normalización de identidad nunca se aplica a contraseñas.

Alta y reset calculan **inicial de nombres + inicial de apellido paterno + CI**,
en mayúsculas: MARÍA JOSÉ / PÉREZ / 0012345 produce `MP0012345`. Se almacena solo
el hash Bcrypt. Esta fórmula empresarial es predecible: la credencial es temporal
y debe reemplazarse al ingresar. No se muestra en listados, auditoría ni logs.

`POST /api/v1/users/{account_id}/reset-password` acepta `{}`. El cliente no elige
la contraseña temporal. ADMIN puede resetear su propia cuenta o una cuenta
conectada. El reset marca `must_change_password=true` y revoca todas sus sesiones.
La próxima autenticación exige la nueva credencial temporal. La cuenta solo
puede consultar su sesión, escuchar sus eventos, cambiar clave y cerrar sesión
hasta completar el cambio. El servidor también exige esta restricción.

La clave personal conserva complejidad y mínimo de ocho caracteres; se limita a
72 bytes UTF-8 por el Bcrypt instalado, sin truncamiento silencioso. Un cambio de
clave personal también cierra todas las sesiones y devuelve al login.

Los datos históricos no se normalizan ni se reemplazan masivamente. Para resetear
una cuenta con identidad incompatible, ADMIN debe corregir primero sus datos.
El envío de bienvenida calcula la fórmula nueva y verifica su hash. Los
reintentos pendientes antiguos admiten CI solo si coincide con el hash anterior;
ningún reintento genera o cambia contraseñas. Si editar nombres o CI impide
reconstruir la credencial pendiente, se requiere un reset explícito.

## Sesiones y permisos vigentes

`sesion_cuenta` registra cada sesión con UUID, cuenta, versión de autenticación,
hash de refresh, vencimiento absoluto y revocación/motivo. `cuentas.auth_version`
permite invalidar credenciales anteriores y `security_version` identificar
cambios de estado o permisos. No existe `is_login`: un booleano confundiría
sesiones simultáneas, pestañas cerradas y credenciales todavía vigentes.

Los JWT incluyen emisor, audiencia, expiración, tipo, identificador aleatorio,
sesión y versión. Cada solicitud comprueba cuenta, colaborador, rol y sesión
actuales en PostgreSQL. Access token solo en memoria; refresh en cookie HttpOnly,
SameSite=Lax y Secure en producción HTTPS. El vencimiento del refresh no prolonga
indefinidamente una sesión. Se conserva la duración configurada (por defecto
30 minutos de access y 7 días de sesión).

La renovación rota el refresh. Reutilizar uno consumido revoca su familia;
logout revoca la sesión correspondiente. Reset, desactivación y cambio de clave
revocan todas las sesiones afectadas. Reactivar una cuenta no rehabilita tokens
revocados. El cliente serializa renovaciones dentro de una pestaña y entre
pestañas mediante Web Locks; no persiste tokens en storage.

Logout es idempotente y puede revocar su sesión usando la cookie de renovación
cuando el access token ya venció. Si falla la comunicación, el navegador informa
que solo confirmó el cierre local. Conserva un marcador booleano de intención de
cierre, sin credenciales, que impide renovar automáticamente al recargar; solo
un login explícito exitoso lo elimina. La señal de storage cierra otras pestañas.
Si el navegador bloquea ese almacenamiento, el marcador solo dura en memoria.

Cambiar el rol conserva la sesión. Las solicitudes posteriores al commit usan
los permisos del rol actual, aunque el JWT contenga el rol anterior. La SPA
recibe el nuevo resumen y actualiza menú, guards y acciones. Una operación ya
confirmada no se deshace retroactivamente por cambiar permisos después.

`GET /api/v1/auth/events` emite NDJSON autenticado mediante el cliente Axios:

| Evento | Efecto |
| --- | --- |
| `session`, con `user` y revisión | Actualizar identidad/permisos sin salir |
| `revoked`, con código | Vaciar sesión, cancelar peticiones/canales y volver al login |
| `expired`, ACCESS_TOKEN_EXPIRED | Renovar y reconectar |
| `heartbeat` | Mantener el canal |
| `unavailable`, AUTH_STATE_UNAVAILABLE | Cerrar la vista autenticada si no se puede verificar autorización |

PostgreSQL publica solo identificadores/revisiones mediante NOTIFY después del
commit. Un listener compartido por proceso despierta los canales. Cada canal
consulta snapshots en transacciones cortas y revalida periódicamente como
recuperación; no retiene una sesión ORM/conexión del pool durante la espera.
Al reconectar se consulta el estado durable, sin confiar en haber recibido todos
los avisos. Una pestaña desconectada no puede recibir eventos inmediatamente;
el servidor ya rechaza sus tokens y la revalidará al reconectar.

Una sesión inválida devuelve 401 con código; un permiso insuficiente devuelve
403. PASSWORD_CHANGE_REQUIRED es un 403 especial que redirige al cambio de clave.
Un 403 ordinario no cierra una sesión válida. El canal de sesión está exento del
bloqueo operativo de backups, igual que consulta y cierre de sesión.

Login limita fallos por cuenta/IP y por IP mediante ventanas PostgreSQL. Las
claves de presupuesto son HMAC, no credenciales. Hay límites configurables y
Retry-After; no se bloquean cuentas permanentemente. Se validan orígenes de las
operaciones con cookie y secretos de producción. Las respuestas 422 de auth
no deben reflejar valores de contraseñas.

## Migración, pruebas y despliegue

La revisión 0022 sigue a 0021; agrega estructura técnica sin resetear cuentas,
modificar roles o corregir identidades históricas. Los JWT anteriores quedan
incompatibles: tras el despliegue todos deben iniciar sesión de nuevo. Antes de
aplicarla a la base empresarial se requieren respaldo, autorización y despliegue
coordinado de API/SPA. No ejecutar seeds administrativos para actualizar sesiones.

Pruebas base sin conexiones ni efectos externos:

```powershell
.\backend\venv\Scripts\python.exe -B .\backend\scripts\run_base_tests.py
```

Integración focalizada exclusivamente en el clúster identificado de testing:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\provision_notification_test_postgres.ps1 -RunTests -Tests test_user_security.py
```

El lanzador conserva controles de identidad/destino, no recurre al `.env`
empresarial y actualiza solo el esquema aislado revisado. Los casos secuenciales
revierten sus transacciones; concurrencia conserva exclusivamente identidades
sintéticas QA_USER en testing. Cubrir unicidad, permisos reales JWT/Casbin,
autodesactivación por ambas vías, democión concurrente, reset propio/ajeno,
revocación, rotación, datos inválidos, rollback y actualización de interfaz.

### Resultados ejecutados el 03/11/2026

| Verificación | Resultado y alcance |
| --- | --- |
| Suite backend base, runner sin conexiones/efectos externos | 1175 aprobadas, 1 omitida; aviso de deprecación pypdf preexistente |
| Integración PostgreSQL completa en 55432 | 234 aprobadas; incluye 20 casos Usuarios/Sesiones y regresiones Economía, Notificaciones y LENY |
| Migración 0022 | Upgrade ejecutado solo en testing; ensayo downgrade/upgrade dentro de transacción revertida, conservando metadatos previos |
| Eventos | Cambio de rol y revocación recibidos por el generador NDJSON con sesiones independientes y PostgreSQL real; sin inferencias Ollama |
| Concurrencia | Democión cruzada admite una operación y rechaza al administrador que perdió permisos; refresh simultáneo detecta reutilización |
| Dependencias Python | pip check sin incompatibilidades; ninguna instalación |
| Frontend | Suite final completa: 160 aprobadas en 22 archivos; incluye respuestas tardías de cambio de clave/autoreset y logout sin red |
| ESLint | Correcto sobre todo el frontend, sin correcciones automáticas |
| Build Vite | Correcto en carpeta temporal nueva; dist conservado; aviso de bundle mayor de 500 kB (aprox. 2704 kB sin comprimir) |

La fase de pruebas anterior no ejecutó operaciones sobre cuentas empresariales,
migración en 5432 ni E2E en navegador real. Las pruebas de interfaz usan DOM y transporte simulado;
los eventos de integración prueban el generador con PostgreSQL, sin certificar
latencia absoluta de redes o navegadores. La base aislada quedó detenida al
terminar. Los cambios preexistentes de LENY se conservaron; únicamente se
adaptaron fixtures de autenticación para las sesiones nuevas.

## Despliegue empresarial autorizado — 03/11/2026

Con la instrucción explícita del propietario de migrar el proyecto original,
se verificó `bellaarte_db:5432` en 0021, dos ADMIN habilitados, cero identidades
incompatibles y ausencia de inferencias/trabajos documentales activos.

El procedimiento reproducible es `backend/scripts/deploy_user_sessions.py`:
sin argumentos inspecciona en solo lectura; `--apply --backend-pid <PID>` exige
identificar el proceso original, pausa exclusivamente su árbol y crea un respaldo
privado de PostgreSQL y originales documentales. Verifica índice del dump,
lectura completa offline, paquete documental y SHA-256 antes de aplicar solo
0022. No ejecuta seeds, restores, downgrade, reset ni regularización de datos.

Resultado: revisión `20261103_0022`, versiones iniciales de cuenta en cero,
permisos de las nuevas tablas comprobados y huellas/conteos de las 60 tablas
anteriores sin modificaciones de filas existentes. Backend original reiniciado;
`/health` respondió 200. Usuarios, Roles y eventos sin credenciales respondieron
401. Vite en 5173 respondió 200 y sirvió la implementación nueva de sesiones.
No se modificó `.env` ni se fabricaron tokens o probaron operaciones de usuarios
reales. La comprobación autenticada queda al propietario mediante login normal.

Respaldo y manifiesto privados: `%LOCALAPPDATA%/BAB_VDOS/users-deployments/20261103-202044-285cd5c4/deployment.json`;
el manifiesto contiene la ubicación del paquete privado y su hash. Evidencia sin
credenciales: [despliegue 0022](evidencias/users_sessions_0022_deployment.json).
La verificación del archivo no equivale a una restauración empresarial ensayada.
Los tokens anteriores no son compatibles: recargar la SPA e iniciar sesión de
nuevo con la contraseña personal existente; la migración no cambia claves.
