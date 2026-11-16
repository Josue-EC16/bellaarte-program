# AGENTS.md — BELLAARTE BOUTIQUE / BAB_VDOS

Guía de trabajo. **Referencia: 17 de octubre de 2026.** Respetar instrucciones superiores/alcance aprobado. No autoriza operaciones sensibles. Distinguir implementación, requisito y deuda; un defecto no se convierte en regla.

## Índice

1. [Identidad y propósito](#identidad)
2. [Contexto empresarial](#negocio)
3. [Objetivos y alcance](#alcance)
4. [Estado y prioridades](#estado)
5. [Arquitectura](#arquitectura)
6. [Stack](#stack)
7. [Estructura](#estructura)
8. [Módulos e integraciones](#modulos)
9. [Reglas críticas](#reglas)
10. [Convenciones](#convenciones)
11. [Backend](#backend)
12. [Frontend](#frontend)
13. [PostgreSQL y migraciones](#datos)
14. [Seguridad y auditoría](#seguridad)
15. [Pruebas y calidad](#pruebas)
16. [Errores y observabilidad](#errores)
17. [Comprobantes y economía](#economia)
18. [Backups](#backups)
19. [APORTE INGENIERIL — LENY](#leny)
20. [Límites de LENY](#limites-leny)
21. [Integración futura](#integracion-leny)
22. [Protocolo de agentes](#protocolo)
23. [Autorizaciones](#autorizacion)
24. [Documentación y fuentes](#documentacion)
25. [Terminación](#terminacion)
26. [ORQUESTACIÓN DE CODEX, SUBAGENTES Y SKILLS](#orquestacion-codex)

<a id="identidad"></a>

## 1. Identidad y propósito del proyecto

BELLAARTE BOUTIQUE, La Paz, Bolivia. BAB_VDOS: ERP administrativo/comercial que conecta Boutique y Taller. Repositorio `bellaarte-program`; no renombrar rutas, paquetes, BD o APIs por su identificación funcional. BOB y `America/La_Paz`. Evaluar efectos en datos, estados y permisos antes de cambiar.

<a id="negocio"></a>

## 2. Contexto empresarial y modelos de negocio

Vestidos de novia, 15 años, ceremonias y accesorios. Boutique gestiona productos/atención; Taller, materiales/confección.

| Modalidad | Proceso |
|---|---|
| Venta directa | Producto → cantidad/precio/descuento → cobro/moneda → stock/comprobante |
| Confección a medida | Cliente → pedido/contrato/diseño/medidas → pruebas → pagos/saldo → entrega |
| Flete/alquiler | Habilitación → reserva → entrega → devolución/revisión; garantía/usos separados del cobro |

Fletes orientados a vestidos de 15 años; el código valida vestido sin restringir subtipo. No cambiar elegibilidad unilateralmente. Multisucursal es futuro, no aislamiento/permisos por sede implementados.

<a id="alcance"></a>

## 3. Objetivos y alcance del ERP

Gestiona accesos, clientes, comercio, inventarios, pedidos, pagos, fletes, economía y controles transversales. Priorizar integridad, seguridad y continuidad. Remuneraciones, agenda integral, historial de cliente y permisos administrables: pendientes de completar. BI descriptivo; no atribuir contabilidad integral, costos automáticos por orden ni predicción al código sin evidencia.

<a id="estado"></a>

## 4. Estado de desarrollo y prioridades actuales

ERP en consolidación: priorizar defectos, administración pendiente, integridad, seguridad, integración, pruebas, mantenibilidad y rendimiento. Recontar tablas/migraciones/APIs cuando importe; cifras/resultados históricos no son estado actual.

LENY conversacional y controles de entrada/salida, cuota PostgreSQL e historial versionado implementados; 0017/0018 desplegadas con autorización en `bellaarte_db:5432`. Analítica pendiente. Corpus adaptado no es validación no vista. DOC preexistente no fue creado por esta etapa y carece de permisos LENY. Ver [módulo](documentacion/MODULO_LENY.md) y [reporte](documentacion/REPORTE_IMPLEMENTACION_LENY.md).

Revalidar deuda de concurrencia, devoluciones, seguridad/sesiones, SMTP/seeds, permisos, stock/fletes/comprobantes, módulos pendientes, pruebas, bundle y recuperación/programación externa. [ESTADO_ACTUAL_SISTEMA.md](ESTADO_ACTUAL_SISTEMA.md) es diagnóstico fechado, no especificación ni autorización de cambios.

<a id="arquitectura"></a>

## 5. Arquitectura del sistema

**SPA React + API FastAPI; monolito modular en capas y PostgreSQL compartido.** Conservar arquitectura.

```text
React / Ant Design / Router
  ↓ Axios: JSON, Bearer JWT, cookie refresh
FastAPI: routers y autenticación/autorización
  ↓ Pydantic: contratos
Servicios: reglas y transacciones
  ↓ SQLAlchemy Session / modelos
PostgreSQL: restricciones, índices y triggers
```

Persistencia síncrona (`create_engine`, `Session`, psycopg2); ASGI no implica AsyncSession. Servicios usan SQLAlchemy directamente: sin Repository independiente ni hexagonal estricta. Auditoría, notificaciones, reportes y backups transversales; scripts reutilizan servicios y requieren programación externa. No introducir patrones incidentalmente; propuestas Docker/Kubernetes/Redis/CI/CD no prueban infraestructura implementada.

<a id="stack"></a>

## 6. Stack tecnológico vigente

Fuentes: [requirements.txt](backend/requirements.txt), [package.json](frontend/package.json), [pnpm-lock.yaml](frontend/pnpm-lock.yaml). Comprobar runtime si importa: lockfile no demuestra instalación ni engines certifica dependencias. No actualizar para inspeccionar.

### Backend y entorno

| Tecnología | Versión / origen |
|---|---|
| Backend | Python, FastAPI/Uvicorn, SQLAlchemy/Alembic, Pydantic/settings, psycopg2 |
| Seguridad/pruebas | Casbin, Bcrypt/Passlib, python-jose, Pytest |
| Entorno | PostgreSQL/pg_dump, Windows, Node/pnpm; versiones según runtime/manifiestos |

Discrepancias Python instalado/README no fijan soporte futuro. Pandas/NumPy no acreditan analítica avanzada. No asumir librerías user-agent antiguas, FastAPI Users, Laravel, Filament o PHP como stack activo.

### Frontend

| Paquete | Manifiesto | Lockfile |
|---|---|---|
| React/React DOM | React 19 | Verificar runtime |
| UI/rutas/HTTP | Ant Design 5, Router, Axios | Consultar manifiesto/lock |
| Gráficos/fechas/calidad | Recharts, Day.js, Vite, Vitest, ESLint | Consultar manifiesto/lock |

JavaScript/JSX. Tipos/configuración React 18 no cambian runtime React 19.

<a id="estructura"></a>

## 7. Estructura y responsabilidades del repositorio

Rutas relativas a raíz; servicios/esquemas/modelos bajo `backend/app/`.

| Ubicación | Responsabilidad |
|---|---|
| `backend/main.py`, `backend/app/main.py` | Entrada, aplicación, middleware/ciclo de vida |
| `backend/app/api/router.py`, `api/routers/` | Composición `/api/v1` y HTTP |
| `backend/app/schemas/`, `services/`, `models/` | Contratos, reglas/transacciones, persistencia |
| `backend/app/core/`, `deps/`, `security/` | Configuración, sesiones, seguridad/auditoría |
| `backend/alembic/`, `backend/scripts/` | Migraciones/operaciones explícitas |
| `backend/tests/`, `pytest.ini` | Pruebas/descubrimiento |
| `frontend/src/pages/`, `components/` | Pantallas/componentes |
| `frontend/src/api/`, `auth/` | HTTP/sesión |
| `frontend/src/routes/`, `layout/`, `config/env.js` | Navegación/menú/configuración |
| `documentacion/` | Guías/especificaciones/histórico |

`backend/core/database.py` y `backend/models/models.py`: reexportaciones compatibles, no otra arquitectura.

### Entorno de desarrollo obligatorio

- Windows nativo, PowerShell (CMD alternativo), VS Code/Laragon. Raíz `C:\laragon\www\bellaarte-program`; confirmar cwd antes de comandos.
- Trabajar directamente en este proyecto de producción. Cambios/pruebas persistentes pueden hacerse en el mismo entorno sin exigir copia ni BD separada; proteger datos y respetar §23.
- No WSL/Ubuntu, `wsl.exe`, rutas `/mnt/c/`, `/home/`, `/workspace/`, sudo, permisos Unix, 777 ni verificar propietario root. Instrucciones heredadas WSL/Docker/PHP/Artisan/Composer no corresponden al proyecto.
- No adaptar configuración global ni instalar/cambiar stack por ejemplos de documentación/Skills.

<a id="modulos"></a>

## 8. Módulos generales e integraciones

“Base” no significa terminado.

| N.º | Módulo / estado | Responsabilidad e integración |
|---|---|---|
| 1 | Usuarios/roles — parcial | Cuentas, JWT/Casbin; permisos personalizados pendientes |
| 2 | Clientes — parcial | CRUD/relaciones; historial integral pendiente |
| 3 | Ventas — base | Un producto por venta; cobro, stock, comprobante/reversión |
| 4 | Pedidos — base | Contrato, detalle, pruebas, pagos/entrega |
| 5 | Pagos — base | Abonos, conversión, saldo/comprobante; revisar devoluciones |
| 6 | Boutique — base | Productos/tipos/detalles/entradas, venta/flete |
| 7 | Taller — base | Insumos/unidades/movimientos; sin costo automático por pedido |
| 8 | Fletes — base | Reserva, entrega, garantía, revisión/usos/venta de usado |
| 9 | Agenda — parcial | Pruebas/reprogramación, no agenda integral |
| 10 | Economía — base | Ingresos derivados, egresos/devoluciones/cortes |
| 11 | Remuneraciones — pendiente | Colaboradores/egreso SUELDO no equivalen a nómina/comisiones |
| 12 | Comprobantes — base | Por origen, snapshots/impresión no fiscal |
| 13 | Reportes/BI — descriptiva | Indicadores/reportes; sin predicción acreditada |
| 14 | Auditoría/backups — base | Trazabilidad/respaldos; recuperación no certificada |
| 15 | Notificaciones — base | Eventos/scripts, destinatarios, lectura/resolución |

Proveedores, monedas/cambios, tipos y dashboard son soporte; dashboard no implica BI integral.

Preservar: venta valida/descuenta stock y emite comprobante/auditoría/alertas; Economía deriva ingreso. Pedido coordina cliente/contrato/pruebas/pagos/saldo/entrega. Pago congela conversión/recalcula saldo. Flete separa unidad comercial y servicio/garantía; coordina reserva/entrega/devolución, contador/revisión/venta/retiro. Taller mueve stock con destino texto, sin FK/imputación automática a pedido. Roles autorizan; operaciones alimentan reportes/alertas/auditoría.

Fuentes: [servicios](backend/app/services/), [rutas SPA](frontend/src/routes/AppRoutes.jsx), [modelos](backend/app/models/__init__.py).

<a id="reglas"></a>

## 9. Reglas de negocio críticas

### Ventas, pedidos y pagos

- Referencias/producto/tipo habilitados; cantidad positiva, stock válido, precio desde inventario; descuento dentro del subtotal y motivo coherente.
- Moneda habilitada: base convierte a 1; otra requiere tipo activo. Congelar conversión histórica, sin recotizar.
- Venta inmutable; reversión única coordinada con stock/economía/comprobante/auditoría.
- Pedido: cliente habilitado, responsable/detalle según tipo; no cambiar tipo libremente tras alta.
- Respetar descuento/motivo, viaje/destino/fechas; null y cero no son intercambiables.
- Pago válido recalcula saldo; no sobrepagar ni editar importes históricos injustificadamente. Entrega con saldo cero/fechas coherentes.
- Pruebas: número positivo, secuencia/unicidad por pedido y fecha compatible; no imponer cuatro/cinco por historia documental.

### Inventarios y fletes

- Stock/mínimos no negativos; movimientos positivos/unidad compatible, sin conversiones implícitas.
- Ajustes trazables; no legitimar huecos de edición de stock con historial. Revalidar bloqueos Boutique por ventas/Taller por movimientos activos.
- Desactivar/reactivar revierte/reaplica una vez, comprobando disponibilidad. Cambiar unidad con historial exige analizar equivalencias/datos.
- Detalle acorde al tipo; conservar `BRASIER` y `detalle_brassier_boutique`.
- Flete retira una unidad comercial, configuración única por producto; no modela ejemplares físicos independientes por código.
- Preservar reserva/entrega/devolución/observación/arreglo/revisión; garantía separada del servicio.
- Usos válidos = devoluciones contadas; revalidar cupo por número histórico anulado.
- Pase a venta crea otro producto usado con stock uno; retiro/restitución depende de usos previos.

### Relaciones y concurrencia

- Cuenta tiene un rol; usuario como máximo una cuenta. Cliente opcional en venta exige snapshot; pedido/salida flete requieren cliente.
- Unicidad de detalle por tabla no asegura exclusividad entre tablas: validar tipo.
- Referencias polimórficas de egreso/notificación/auditoría no son FK: validar tabla/ID.
- Proteger stock, saldo, duplicación, reembolso máximo y reversión única con concurrencia; lock/commit de correlativo no protege decisiones previas.

Consultar `boutique_sale`, `order`, `order_payment`, `workshop`, `flete` (`*_service.py`) y §§14/17.

<a id="convenciones"></a>

## 10. Convenciones de desarrollo y diseño

- Analizar primero; cambios pequeños/verificables, sin refactor ajeno, duplicación o dependencias innecesarias.
- Conservar nombres: snake_case Python, convenciones React/tablas nuevas minúsculas; distinguir API/ORM/SQL.
- Mayúsculas en texto/códigos según contrato, correo minúsculo; no normalizar claves ni restringir texto libre indiscriminadamente.
- Español latino, BOB y moneda original; accesibilidad/teclado, carga/error/adaptación de pantalla.
- Reutilizar componentes; Gmail en Usuarios no impone política a Clientes/Proveedores.
- Documentar estados, precisión, permisos, APIs/KPI; consultar reglas empresariales no aprobadas.

<a id="backend"></a>

## 11. Normas para backend

- Routers: transporte/dependencias; Pydantic: contratos; servicios: reglas/transacciones; modelos: persistencia.
- `/api/v1`, rutas estáticas antes de dinámicas conflictivas y permiso backend explícito.
- Sesiones existentes, nunca compartidas entre solicitudes/hilos; sin `create_all` para evolucionar esquema.
- Atomicidad: coordinador controla commit/rollback; helpers sin commits parciales, salvo excepciones justificadas como historial de backup.
- Validar referencias/estados/habilitación y propiedad usuario/corte en servidor; no confiar precio/total/rol/propietario de UI.
- Decimal/redondeo explícito y NUMERIC para dinero; sin imprecisión ni cambios API silenciosos por float heredado.
- Concurrencia/idempotencia; reutilizar auditoría, comprobantes/alertas. Errores consistentes, sin éxito ficticio ni secretos; filtros/paginación server-side compatibles.
- [Configuración central](backend/app/core/config.py); nunca PostgreSQL desde navegador ni secretos en `VITE_*`.

<a id="frontend"></a>

## 12. Normas para frontend

- React/JSX funcional, Ant Design/Router y [cliente HTTP](frontend/src/api/client.js)/sesión existentes; token solo en memoria, sin clientes alternativos ni credenciales en localStorage/sessionStorage.
- Rutas/guards/menú coherentes; UI no reemplaza autorización servidor.
- Reutilizar [formConfig](frontend/src/components/forms/formConfig.js), [FormProcessAlert](frontend/src/components/forms/FormProcessAlert.jsx), [formErrorUtils](frontend/src/components/forms/formErrorUtils.js).
- Error inequívoco al campo, proceso/ambiguo a alerta, éxito/acción puntual a toast; preservar ubicación 422.
- Inputs Row/Col, no Space como grilla; `maskClosable={false}` en edición/detalle crítico. Limpiar errores sin perder captura.
- GET fresco para ver, no fila resumida; carga/vacío/error recuperable y bloqueo de doble envío.
- Form.Item/payload según schema; números vacíos no son cadena vacía.
- Diferenciar fecha local/timestamp UTC; filtros/KPI/impresión compatibles. Optimizar sin romper navegación/sesión; persistir filtros no autoriza tokens.

<a id="datos"></a>

## 13. Normas para PostgreSQL y migraciones

- Alembic en [versions](backend/alembic/versions/), modelos registrados/documentados. No alterar migración aplicada para cambios nuevos sin decisión explícita.
- Revisar FK/enums/defaults/nulabilidad/precisión/datos previos; CHECK/UNIQUE/índices parciales/FK para invariantes. Pydantic no protege escrituras externas/concurrentes.
- Planificar backfill, compatibilidad, fallo/recuperación; conservar históricos. No quitar RESTRICT ni añadir cascadas destructivas por comodidad.
- No editar columnas generadas ni stock/saldo por cálculo aislado; distinguir fila/agregado. Índices por consultas/volumen, sin duplicados; rangos temporales indexables equivalentes.
- Cambios destructivos: análisis, respaldo/recuperación y autorización; Alembic no autoriza tocar base real. Tablas comerciales/roles/usuarios/cuentas minúsculas; contrastar SQL antiguo.

**TC-01 (0023):** desplegada con autorización en `bellaarte_db:5432`. Mantener NUMERIC(12,4), procedencia/registro técnico propio; `usu_id` nullable AUTO/SISTEMA. Conservar auditoría previa/de moneda; operaciones futuras de tipos de cambio excluidas de auditoría general. Cambio MANUAL de valor crea otro ID; AUTO sin edición humana/activación directa. Serializar inserción por moneda; histórico inactivo. [Contrato/evidencia](documentacion/SPEC_TC_01_IMPLEMENTACION.md).

**TC-02:** tarea `BAB_VDOS_USD_BOB_SYNC` activa, InteractiveToken/Limited e independiente de API/React. Inicio fijo 2026-11-04; USD histórico por fecha/vigencia, 05:00 Bolivia, reintento +1h, máximo diez HTTP/día para hoy/recuperación. Registros/avisos solo ADMIN, exADMIN excluidos. No borrar INICIADO ni mover fecha inicial para forzar consultas; preservar tasas/registros al deshabilitar. Mes histórico opcional no cargado. [Operación/evidencia](documentacion/SPEC_TC_02_IMPLEMENTACION.md).

<a id="seguridad"></a>

## 14. Seguridad, roles, permisos y auditoría

**Usuarios/Sesiones 0022 desplegada:** [reglas actuales](documentacion/MODULO_USUARIOS_SESIONES.md). ADMIN exclusivo Usuarios/Roles; no autodesactivación/cambio de rol propio; mantener al menos un ADMIN habilitado. Reset propio/ajeno con iniciales+CI; CI numérico de mínimo siete dígitos. Cambio de rol actualiza permisos sin salir; reset/desactivación/cambio de clave revocan sesiones. No añadir `is_login` ni restaurar sesiones al reactivar.

JWT, refresh HttpOnly, Bcrypt/Passlib y Casbin por `rol.codigo`/`dominio:accion`; cuenta/usuario/rol habilitados.

| Rol base | Alcance principal |
|---|---|
| ADMIN | Global; auditoría/backups exclusivos |
| INV_BOUTIQUE | Tipos/proveedores/stock/entradas y consultas autorizadas |
| INV_TALLER | Insumos/movimientos Taller |
| CAJA | Ventas/fletes/pagos/comprobantes/economía por usuario/corte |
| MODISTA | Clientes/pedidos/pruebas/salidas Taller y consultas permitidas |

Fuentes: [permisos](backend/app/core/permissions.py), [Casbin](backend/app/security/), [auth](backend/app/deps/auth.py). Roles adicionales no adquieren políticas por existir.

- Menor privilegio por recurso, no solo ruta; cambio obligatorio de clave también en servidor.
- Sesiones durables, expiración, refresh rotatorio/revocación; no emitir tokens sin sesión ni reactivar sesiones revocadas.
- Rechazar secretos JWT de desarrollo en producción; cookie Secure bajo HTTPS. Distinguir código preparado de servicio desplegado.
- Sin claves/hashes/tokens/secretos/PII innecesaria en logs/respuestas/fixtures. Credenciales/.env requieren autorización; VITE_* público. No debilitar políticas/validadores para pruebas; aplica entorno §7.
- [Auditoría](backend/app/core/audit.py): reutilizar aud_id_evento, responsable/contexto y triggers; excluir sensibles. Solo consulta administrativa, sin CRUD manual UI/API; no certificar inviolabilidad ante privilegios BD no evaluados.

<a id="pruebas"></a>

## 15. Pruebas, calidad y criterios de aceptación

Verificaciones proporcionales del comportamiento; no pruebas espejo ni suites completas por documentación.

| Nivel | Impacto a cubrir |
|---|---|
| Unitarias/contratos | Schemas, normalización/cálculos/helpers |
| Integración PostgreSQL | Restricciones, relaciones, transacción/rollback/migración |
| API/autorización | Credenciales, rol/recurso/propiedad, payload/errores |
| Concurrencia | Stock/pagos/duplicación/reembolso/reversión única; sesiones independientes |
| Frontend/regresión | Captura, carga/errores, navegación/permisos/impresión |
| E2E | Recorrido empresarial con herramientas/entorno aprobados |

No atribuir suite E2E completa ni porcentaje de cobertura sin evidencia.

### Comandos y seguridad

Verificar conexión efectiva (`DATABASE_URL`/`DB_*`/`.env`) y efectos antes de tests/imports persistentes, sin imprimir credenciales. Se permite misma BD/proyecto (§7); proteger datos y respetar §23. Crear/migrar requiere autorización aplicable.

Importar [router](backend/app/api/router.py) puede escribir policy.csv; arranque/middleware pueden limpiar locks. Importación, TestClient o GET no garantizan ausencia de efectos. Revisar fixtures/diff; -B/no-cache no impiden escrituras BD.

Desde backend, venv Windows:

```powershell
.\venv\Scripts\python.exe -B -m pytest tests -q -p no:cacheprovider
.\venv\Scripts\python.exe -B -m pip check
```

Desde raíz, pytest.ini descubre backend/tests con el intérprete correcto. Desde frontend:

```powershell
pnpm.cmd lint
pnpm.cmd exec vitest run --no-cache
pnpm.cmd build
```

`pnpm.cmd` evita wrapper ps1 bloqueado sin cambiar política global. Build escribe dist: salida temporal nueva para inspección. No instalar para eludir sandbox. Arranque: `uvicorn main:app --reload` en backend/venv, `pnpm.cmd dev` en frontend; no arrancar solo por documentación. Temporales propios fuera del repo cuando corresponda.

### Resultados anteriores

Resultados históricos no certifican estado actual. Revalidar pruebas dependientes de fecha con reloj/datos controlados, conservando propósito/validaciones; no ocultar fallos ni cambiar negocio para obtener verde. Reportar solo resultados ejecutados y distinguir defecto nuevo, previo o de entorno.

<a id="errores"></a>

## 16. Gestión de errores, logs y observabilidad

- Preservar 422 y distinguir autenticación, permiso, inexistencia/conflicto según contrato.
- Rollback al fallar; sin éxitos/parciales ficticios, SQL/conexiones/rutas sensibles o stack traces públicos.
- Logs técnicos separados de auditoría, con contexto sin secretos/PII innecesaria. Fallback SMTP que imprime credenciales/devuelve éxito es deuda, no patrón.
- Respetar 503 por backup; no mapear a campo ni reintentar escrituras sin prevenir duplicados.
- Nuevos monitoreo/trazas/alertas requieren propósito/acceso/retención/validación; no atribuir capacidades externas inexistentes.

<a id="economia"></a>

## 17. Comprobantes, economía y consistencia transaccional

- Separar hecho operativo/económico: venta/pago/salida conservan ingreso bruto; devolución efectiva es egreso, sin borrar ingreso al anular.
- Comprobante automático/atómico, exactamente un origen y único por operación. Snapshot no actualiza cliente; sin alta manual/edición de importes como atajo; estado deriva del origen.
- HTML/window.print, no fiscal ni integración tributaria acreditada. Agregados BOB; preservar moneda/importe/tasa original; garantía fuera de ingreso.
- Usar [coordinador de devolución](backend/app/services/refund_flow_service.py), sin eludir endpoints con helpers privados.
- Revalidar brechas históricas: parcial que anula/bloquea posteriores, rechazo de cero, cierres recalculados/anulación de egresos cerrados. No asumir soporte ni cambiar reglas sin tarea aprobada.
- CAJA requiere corte para egreso; ADMIN puede operar sin él. Propiedad/enmascaramiento también en CSV; corte abierto único por cajero. Verificar atribución de egreso por FK e ingresos por usuario/rango según implementación vigente.
- Definir KPI/estados y consistencia de cierre/ajustes/inmutabilidad; no confundir deuda, ingreso bruto, egreso, neto o utilidad.

Fuentes en services: receipt_service.py, income_service.py, expense_service.py, cash_cut_service.py.

<a id="backups"></a>

## 18. Backups y operaciones sensibles

[Servicio](backend/app/services/backup_service.py), [runtime](backend/app/core/backup_runtime.py), [generador](backend/scripts/backup_manager.py): pg_dump -Fc, historial/tamaño/SHA-256, descarga/lock ADMIN; síncrono, bloquea operaciones con excepciones definidas.

- No quitar locks a ciegas ni afirmar éxito sin archivo válido. Hash no certifica recuperación; recuperación integral, restauración UI/retención avanzada no acreditadas.
- Backup, chequeos/reintentos escriben/afectan disponibilidad. `backend/scripts/run_backup_job.py` y `run_notification_checks.py` tienen modos; programación externa por verificar (backup recomendado domingo 02:00 Bolivia).
- Restaurar/sobrescribir/mover/eliminar exige autorización y respaldo/recuperación previstos; ensayo puede usar mismo proyecto/destino autorizado, sin exigir aislamiento.
- Sin dumps públicos/Git; cambio destructivo exige reversión/validación. Proceso colgado/EN_PROCESO exige procedimiento, no borrar evidencia para desbloquear.

<a id="leny"></a>

## 19. APORTE INGENIERIL — LENY

LENY conversacional implementado: Qwen/Ollama local, historial PostgreSQL privado, JWT/Casbin y chat React; 0017/0018 desplegadas con autorización. Analítica/indicadores/predicciones/recomendaciones siguen sujetos a implementación/evaluación; no reemplazan transacciones ni responsabilidad humana. [Módulo](documentacion/MODULO_LENY.md) y [reporte](documentacion/REPORTE_IMPLEMENTACION_LENY.md) contienen despliegues/evidencias; aceptación del propietario no equivale a pruebas del agente.

| Componente previsto | Función |
|---|---|
| LLM local | Comprender/redactar con resultados sustentados |
| SQL controlado | Recuperación autorizada/acotada |
| BI | Análisis descriptivo/diagnóstico/comparativo |
| Machine Learning | Predicción validada con historia suficiente |
| AutoML controlado | Evaluar técnicas/alternativas permitidas |
| RAG contextual | Documentos/reglas con procedencia |
| Orquestador | Tareas/herramientas trazables |
| Seguridad | Usuario/rol/módulo/recurso/datos |

RAG 0019–0021 desplegado con autorización: biblioteca ADMIN, originales privados/versiones/ACL/papelera/respaldo conjunto; publicación fija versión+índice y recuperación exacta con ACL SQL. No cambiar versiones actuales por una evaluación. DOC preexistente sigue excluido/sin política LENY: no atribuir su creación a estas etapas.

Extracción/OCR local, fragmentos trazables, pgvector0.8.7 en esquema leny y embeddings1024 con qwen3-embedding:0.6b existente; CPU obligatoria. Worker manual separado de Uvicorn; trabajos durables/idempotentes, cancelación/checkpoints y coordinador PostgreSQL compartido con chat. Fuentes privadas, singleton durable, streaming/historial; flags deshabilitados por defecto y activación local autorizada en backend/.env. Mantener `LENY_RAG_CHAT_ENABLED=true`, residencia0 y márgenes 2GiB/1GiB adoptados tras pruebas. No inferir exactitud OCR ni seguridad global; SPEC-04 conserva calidad, falsos positivos/carga sostenida. Evidencias `leny_rag01_business_deployment.json`, `leny_rag02_*`, `leny_rag03_*`; publicación del manual v1 para ADMIN/CAJA tuvo autorización específica.

### Caso predictivo y evaluación

Objetivo futuro: unidades efectivamente vendidas por categoría comercial para el siguiente mes calendario, no dinero, demanda no satisfecha ni ventana móvil de 30 días. Historia/estados/categorías validados; evaluar cancelaciones, cambios de categoría, completitud/suficiencia antes de aprobar dataset/baseline/técnicas. Separación temporal sin fuga; MAE contra baseline comparable.

CRISP-DM: negocio → datos → preparación → modelado → evaluación → despliegue; no sustituye ingeniería/pruebas.

| Métrica | Finalidad | Criterio preliminar previsto |
|---|---|---|
| ERA | Exactitud contra casos verificados | ≥90 % |
| MAE | Error mensual | Inferior al baseline comparable |
| CCA | Control de acceso | 100 %, sin exposición protegida |

Objetivos futuros, no resultados: definir batería, denominadores, referencias y protocolo antes de medir.

<a id="limites-leny"></a>

## 20. Restricciones y límites actuales de LENY

- No ampliar LENY incidentalmente al consolidar/documentar ERP; nuevas capacidades requieren tarea específica.
- Lectura controlada: sin modificar autónomamente ventas, saldos, inventarios, remuneraciones u otros registros críticos.
- Entrada, recuperación y salida LLM no confiables: no amplían permisos ni se ejecutan automáticamente como SQL.
- Sin cuentas alternativas ni consultas sin filtros para eludir acceso. Separar observado/calculado/estimado/recomendado.
- Cambios de modelos, embeddings, orquestación/despliegue requieren evaluación/aprobación; Pandas/NumPy o ejemplos RAG no prueban capacidades.

<a id="integracion-leny"></a>

## 21. Preparación de integración futura

En tareas aprobadas, favorecer contratos/validación/KPI/auditoría reutilizables sin crear anticipadamente tablas, endpoints o dependencias LENY.

Identidad/permisos ERP por herramienta/recurso; consultas acotadas por filas/tiempo/recursos, sin credenciales privilegiadas al modelo. Resultados con filtros/período/unidad/moneda/procedencia; auditoría mínima y resistencia a instrucciones maliciosas.

Separar reales/estimados; versionar datasets, modelos, evaluaciones, predicciones y resultados. Evaluar/aprobar organización/despliegue antes de fijarlos; no alterar transacciones al incorporar modelos.

<a id="protocolo"></a>

## 22. Protocolo de trabajo de los agentes

**Antes:** alcance/instrucciones/Git/cambios ajenos; módulos, contratos, reglas, pruebas, efectos/seguridad. Resolver hechos leyendo código; preguntar solo decisiones críticas/autorización necesaria.

**Durante:** cambios mínimos compatibles, atomicidad/precisión/permisos/auditoría, pruebas/documentación. Si falta decisión, detener acción dependiente y continuar lo seguro.

**Después:** revisar diff/nuevos, contratos, economía/seguridad/auditoría/documentación; entregar evidencia/límites. No repetir autorización ya concedida ni inventar aprobaciones para lecturas/ediciones reversibles autorizadas; explicar restricciones reales.

<a id="autorizacion"></a>

## 23. Acciones prohibidas sin autorización

Requieren autorización explícita para el mismo alcance, salvo ya concedida:

- Eliminar/sobrescribir datos, base real u operaciones comerciales de prueba sobre registros existentes.
- Migraciones destructivas, esquema real fuera de procedimiento, restaurar/sobrescribir backups.
- Seeds que alteren registros/cuentas, permisos reales o importes económicos.
- Secretos/credenciales, nuevas dependencias o actualización de versiones principales.
- Cambiar stack/arquitectura, reestructurar módulos, producción, commits/publicaciones no solicitados.
- Borrar archivos ajenos o sobrescribir trabajo de colaboradores.

Mejora genérica no autoriza estas acciones: preparar resultado seguro/revisable antes de la operación sensible. No sudo, 777, Docker root/eliminar volúmenes ni introducir Docker o eludir sandbox/autenticación/permisos como solución.

<a id="documentacion"></a>

## 24. Mantenimiento documental y fuentes de verdad

Fuentes para lo existente: código/configuración → esquemas/migraciones/contratos → manifiestos/locks → pruebas/resultados → documentación vigente → reporte de estado → histórico → planes. Para requisitos nuevos, manda lo aprobado por el propietario; código defectuoso no justifica reglas ni plan demuestra capacidad activa.

Referencias: [README](README.md), [backend](backend/README.md), [frontend](frontend/README.md), [desarrollo](documentacion/GUIA_DESARROLLO.md), [UX/UI](documentacion/GUIA_UX_UI.md), [formularios](documentacion/ESTANDARES_DE_DISENO_FORMULARIOS.md) y documento del dominio.

Contrastar versiones/SQL/enlaces y reglas antiguas de comprobantes, estados, toast/monedas. No cambiar API/negocio por documentación obsoleta. Actualizar guía ante cambios aprobados con evidencia/fecha; retirar deuda solo verificada y no perpetuar cifras/resultados. Instrucciones por directorio precisan la global sin superar seguridad; resolver contradicción material antes de actuar.

<a id="terminacion"></a>

## 25. Criterios para considerar terminada una tarea

- Alcance cumplido, sin cambios incidentales ni pérdida de trabajo ajeno.
- Contratos/reglas/permisos/datos/historia económica/auditoría revisados.
- Migraciones, compatibilidad/documentación cuando proceda, sin operaciones sensibles no autorizadas.
- Diff/nuevos y verificaciones proporcionales revisados; informar cambio, motivo, evidencia, fallos/límites y pendientes.
- No presentar propuesta/simulación/validación parcial como capacidad productiva completa.

Solo documentación: verificar Markdown, enlaces, exactitud, vigencia, secretos y diff; no arrancar servicios, seeds o migraciones para aumentar verificación.

<a id="orquestacion-codex"></a>

## 26. ORQUESTACIÓN DE CODEX, SUBAGENTES Y SKILLS

### 26.1. Coordinación y configuración local

Principal delimita alcance, contratos/dependencias y responsables; integra/verifica y responde del resultado. [config.toml](.codex/config.toml) local, perfiles `.codex/agents/`; sin cambios globales, proveedores, permisos/herramientas u otros sistemas. Descubrimiento nativo; TOML define name/description/developer_instructions, sin registro duplicado.

`agents.enabled=true`, `agents.max_concurrent_threads_per_session=2`: máximo dos hilos de subagentes abiertos además del principal; cerrar terminados innecesarios. No fijar modelo/esfuerzo: heredar salvo selección explícita aplicable.

### 26.2. Selección y responsabilidades

| Perfil | Delegar cuando | Ámbito habitual y coordinación |
|---|---|---|
| [backend](.codex/agents/backend.toml) | FastAPI/Pydantic/reglas/JWT/Casbin/transacciones/auditoría | API/services/schemas/core/deps/security; acuerda API con frontend y datos con data_sql vía principal |
| [frontend](.codex/agents/frontend.toml) | React/JSX/AntD/formularios/rutas/Axios/gráficos/a11y | frontend/src; conserva contratos/sesión, informa endpoints, valida con QA |
| [qa_testing](.codex/agents/qa_testing.toml) | Diagnóstico, pruebas/permisos/regresiones/concurrencia | Inspección backend/frontend; editar tests/fixtures solo por delegación expresa, no código funcional |
| [data_sql](.codex/agents/data_sql.toml) | PostgreSQL/ORM/migraciones/SQL/índices/bloqueos | models/alembic/services/database; backend conserva negocio/API; no migrar ni cambiar datos reales |

Asignar archivos concretos: las rutas no autorizan edición indiscriminada. Definir contratos antes de cambios integrales; secuenciar si comparten archivos.

### 26.3. Política de delegación y coste

Tarea simple: sin delegar. Dominio/revisión acotada: un especialista. Compleja con entregables independientes: hasta dos. No activar cuatro automáticamente, repetir análisis ni enviar documentación innecesaria. Subagentes no crean otros ni ciclos de consulta sin autorización del principal; coordinan dependencias mediante él.

### 26.4. Contrato de delegación

Cada encargo define objetivo/contexto mínimo, archivos/responsable, alcance lectura/pruebas/edición, restricciones/permisos/dependencias, resultado/criterios verificables y retorno. No delegar “revisar todo”; delegación no amplía autorización ni decide negocio pendiente.

### 26.5. Entrega, integración y conflictos

Especialista devuelve archivos/cambios, hallazgos, comandos/resultados, riesgos/límites y decisiones pendientes; rutas/evidencia sin logs completos ni sensibles. Distinguir propuesta, edición, verificación estática y ejecución. QA añade flujo, esperado/obtenido, reproducción, severidad/recomendación y verificaciones pendientes.

Un responsable de edición por archivo; otros revisan sin escribir. No sobrescribir trabajo ajeno. Principal integra, revisa contratos/diff, resuelve dependencias y verifica antes de afirmar éxito.

### 26.6. Skills existentes y uso selectivo

Subagente ejecuta; Skill aporta instrucciones/recursos. No convertirlos entre sí ni instalar perfiles en Skills. Conservar descubrimiento en [.agents/skills/](.agents/skills/); leer SKILL.md pertinente y solo referencias necesarias, sin duplicarlas en perfiles/guía.

| Skill | Aplicación | Agentes habituales |
|---|---|---|
| [frontend-design](.agents/skills/frontend-design/SKILL.md) | Diseño/UX solicitado dentro de AntD/patrones existentes | Principal/frontend |
| [accessibility](.agents/skills/accessibility/SKILL.md) | Teclado, formularios, lectores/a11y | Principal/frontend/QA |
| [seo](.agents/skills/seo/SKILL.md) | Páginas públicas pertinentes; no requisito de ERP autenticado | Principal/frontend |

Usar selectivamente, sin presumir Skills backend/SQL ni activar las tres. Ejemplos no autorizan instalaciones/arquitectura/rediseños. Conservar nombres/metadatos/recursos/licencias; sin mover/duplicar, symlinks, instalar/eliminar Skills o alterar skills-lock.json sin autorización específica. Enlaces opcionales ausentes no autorizan instalación; corregir enlaces no actualiza lock ni certifica hashes.

### 26.7. Seguridad y operaciones sensibles

Subagentes heredan límites/permisos efectivos y §23; “solo lectura” en TOML es regla, no aislamiento técnico. No ampliar acceso, debilitar Casbin, exponer secretos ni actuar destructivamente sin autorización. Se permite mismo proyecto/producción para pruebas persistentes (§7): verificar comandos/imports/fixtures, proteger registros reales y preservar cambios previos, incluidos no versionados.

### 26.8. LENY y mantenimiento de la configuración

Organización para ERP y LENY expresamente aprobado; núcleo conversacional integrado, analítica pendiente. No crear perfiles LLM/RAG/ML/AutoML incidentalmente.

Antes de modificar perfiles, verificar versión Codex/documentación oficial. Validar TOML con parser disponible, campos/nombres únicos/concurrencia/herencia, frontmatter/rutas/anclajes de Skills y ausencia de cambios globales; sin instalar solo para validar.

Fuentes: [subagentes](https://learn.chatgpt.com/docs/agent-configuration/subagents), [configuración](https://learn.chatgpt.com/docs/config-file/config-reference), [Skills](https://learn.chatgpt.com/docs/build-skills). Revalidar al cambiar Codex; no copiar claves heredadas incompatibles.

Comprobar reconocimiento ligero, sin lanzar cuatro agentes. Si faltan, sesión nueva desde raíz y diagnóstico; no modificar confianza/configuración administrada automáticamente. Distinguir archivos creados, sintaxis válida, perfiles reconocidos y delegación ejecutada; estos dos últimos requieren evidencia.
