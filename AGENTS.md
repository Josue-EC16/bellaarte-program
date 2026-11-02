# AGENTS.md — BELLAARTE BOUTIQUE / BAB_VDOS

Guía global de contexto y trabajo. **Referencia: 17 de octubre de 2026.** No autoriza por sí sola operaciones sensibles. Respetar instrucciones superiores y alcance aprobado por el usuario. Distinguir implementación, requisito y deuda: un defecto actual no se convierte en comportamiento obligatorio.

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

**Empresa:** BELLAARTE BOUTIQUE, La Paz, Bolivia. **Sistema:** BAB_VDOS — Sistema Web Administrativo / ERP. **Repositorio:** `bellaarte-program`; la identificación funcional no implica renombrar rutas, paquetes, base de datos o APIs.

Objetivo: centralizar y fortalecer gestión administrativa, comercial, financiera y operativa, conectar Boutique/Taller y mejorar trazabilidad, disponibilidad y decisiones. Referencia empresarial: bolivianos (`BOB`) y `America/La_Paz`. Comprender el efecto empresarial antes de cambiar datos, estados o permisos.

<a id="negocio"></a>

## 2. Contexto empresarial y modelos de negocio

Comercialización y confección de vestidos de novia, de 15 años, ceremonias y accesorios. Unidades: **Boutique**, productos terminados/atención comercial; **Taller de Producción**, materiales, insumos/confección.

| Modalidad | Proceso |
|---|---|
| Venta directa | Producto → cantidad/precio/descuento → cobro/moneda → stock y comprobante |
| Confección a medida | Cliente → pedido/contrato, diseño/medidas → pruebas → pagos/saldo → entrega |
| Flete/alquiler | Vestido habilitado → reserva → entrega → devolución/revisión; garantía y usos separados del cobro |

El negocio orienta fletes a vestidos de 15 años; el código valida tipo vestido sin restringir expresamente el subtipo. Registrar la brecha, sin cambiar elegibilidad unilateralmente. **Multisucursal es visión futura**, no inventario, aislamiento o permisos por sede implementados.

<a id="alcance"></a>

## 3. Objetivos y alcance del ERP

Administra accesos, clientes, comercio, inventarios, pedidos, pagos, fletes, economía y controles transversales. Priorizar integridad, seguridad y continuidad antes que complejidad nueva.

Completar remuneraciones, agenda integral, historial de cliente y permisos administrables es alcance aprobado pendiente, no implementación demostrada. BI actual es principalmente descriptivo; no atribuir contabilidad integral, costos automáticos por orden, predicción o KMS/RAG al código activo.

<a id="estado"></a>

## 4. Estado de desarrollo y prioridades actuales

Implementación funcional importante **en consolidación**. Referencia: 38 tablas ORM, 13 migraciones y 14 grupos API; recontar si la tarea depende de esas cifras.

- **ETAPA A, inmediata:** defectos, módulos administrativos pendientes, integridad, seguridad, integración, pruebas, mantenibilidad y rendimiento.
- **LENY, actualización 19/10/2026:** núcleo conversacional Etapa 01 integrado y probado con Ollama en entorno aislado; revisión0017 habilitada posteriormente con autorización en `bellaarte_db:5432` y consultas de historial/estado comprobadas en el ERP habitual. Herramientas analíticas pendientes. Ver [módulo LENY](documentacion/MODULO_LENY.md).
- **LENY Etapa 01.1, 19/10/2026:** política empresarial y controles de entrada/salida, cuota PostgreSQL e historial por versión implementados; revisión0018 probada en la instancia aislada y aplicada posteriormente con autorización a `bellaarte_db:5432`, con respaldo verificado y estructura `public` intacta. No confundir la evaluación adaptada del corpus con validación no vista. Se conservaron los códigos de roles del respaldo, incluido `DOC` preexistente sin permisos LENY; no atribuir su creación a esta etapa. Evidencias y resultados: [reporte LENY](documentacion/REPORTE_IMPLEMENTACION_LENY.md).

Deuda que debe revalidarse: concurrencia stock/pagos; devoluciones sucesivas/cero; cambio de clave incompletamente exigido en servidor; cookies/secretos y revocación; fallback SMTP; seeds que resetean cuentas; permisos personalizados; casos de stock/flete/comprobante; agenda/historial/remuneraciones; pruebas limitadas, bundle grande y recuperación/programación externa no certificadas.

[ESTADO_ACTUAL_SISTEMA.md](ESTADO_ACTUAL_SISTEMA.md) contiene diagnóstico y resultados fechados. No tratarlo como especificación infalible, mandato de modificar código ni evidencia de defectos corregidos.

<a id="arquitectura"></a>

## 5. Arquitectura del sistema

**Cliente-servidor desacoplada: SPA React + API FastAPI, backend de monolito modular en capas y PostgreSQL compartido.** Conservarla por defecto.

```text
React / Ant Design / React Router
  ↓ Axios: JSON, Bearer JWT y cookie refresh
FastAPI: routers y dependencias de autenticación/autorización
  ↓ contratos Pydantic
Servicios: reglas, coordinación y transacciones
  ↓ SQLAlchemy Session y modelos
PostgreSQL: datos, restricciones, índices y triggers
```

Persistencia síncrona: `create_engine`, `Session`, psycopg2; ASGI no implica `AsyncSession`. Los servicios usan SQLAlchemy directamente: sin Repository independiente ni arquitectura hexagonal estricta. Auditoría, notificaciones, reportes y backups son transversales; scripts reutilizan servicios y necesitan programación externa.

No introducir patrones nuevos incidentalmente. No se encontraron Docker, Kubernetes, Redis ni CI/CD implementados en el repositorio; propuestas de infraestructura no son despliegues existentes.

<a id="stack"></a>

## 6. Stack tecnológico vigente

Fuentes: [requirements.txt](backend/requirements.txt), [package.json](frontend/package.json), [pnpm-lock.yaml](frontend/pnpm-lock.yaml). No actualizar dependencias para inspeccionar.

### Backend y entorno

Instaladas comprobadas por runtime/metadatos del venv el 17/10/2026; los paquetes coinciden con sus pins:

| Tecnología | Versión / origen |
|---|---|
| Python | 3.10.6 instalada; README declara 3.14.2 |
| FastAPI / Uvicorn | 0.115.6 / 0.32.1 instaladas y fijadas |
| SQLAlchemy / Alembic | 2.0.46 / 1.16.5 instaladas y fijadas |
| Pydantic / pydantic-settings | 2.12.5 / 2.10.1 instaladas y fijadas |
| psycopg2-binary / Casbin | 2.9.11 / 1.43.0 instaladas y fijadas |
| Bcrypt / Passlib | 4.2.0 / 1.7.4 instaladas y fijadas |
| python-jose / Pytest | 3.5.0 / 8.4.2 instaladas y fijadas |
| Pandas / NumPy | 2.3.3 / 2.2.6 presentes, sin uso analítico avanzado activo comprobado |
| PostgreSQL / pg_dump | 17.9 / 17.9, evaluación anterior del mismo día; no reconsultados para esta guía |
| Node.js / pnpm | 22.12.0 / 10.33.0, ejecutables comprobados |

### Frontend

| Paquete | Manifiesto | Lockfile |
|---|---|---|
| React / React DOM | `^19.0.0` | 19.0.0 / 19.0.0 |
| Vite | `^6.0.0` | 6.4.1 |
| Ant Design | `^5.27.6` | 5.29.3 |
| React Router DOM | `^7.9.3` | 7.14.0 |
| Axios | `1.14.0` | 1.14.0 |
| Recharts | `^3.8.1` | 3.8.1 |
| Day.js | `^1.11.20` | 1.11.20 |
| Vitest | `^3.2.4` | 3.2.4 |
| ESLint | `^9.15.0` | 9.39.4 |

La evaluación anterior también ejecutó Vite/Vitest con esas versiones. Lockfile no demuestra lo instalado. `engines.node >=18.8.0` no certifica todas las dependencias. Frontend JavaScript/JSX; tipos/configuración React 18 no cambian runtime React 19.

Parser user-agent propio; no asumir instalada la librería mencionada en documentos antiguos. FastAPI Users, Laravel, Filament y PHP no son aplicación activa comprobada. Python local tampoco fija automáticamente el mínimo soportado futuro.

<a id="estructura"></a>

## 7. Estructura y responsabilidades del repositorio

Rutas relativas desde raíz; abreviaciones expresamente ubicadas bajo su directorio:

| Ubicación | Responsabilidad |
|---|---|
| `backend/main.py`, `backend/app/main.py` | Entrada Uvicorn, aplicación, middleware/ciclo de vida |
| `backend/app/api/router.py` y `api/routers/` dentro de app | Composición `/api/v1` y HTTP |
| `backend/app/schemas/`, `services/`, `models/` | Contratos, reglas/transacciones, persistencia |
| `backend/app/core/`, `deps/`, `security/` | Configuración, sesiones, seguridad, auditoría/políticas |
| `backend/alembic/`, `backend/scripts/` | Migraciones y operaciones explícitas |
| `backend/tests/`, `pytest.ini` | Pruebas y descubrimiento |
| `frontend/src/pages/`, `components/` | Pantallas y componentes compartidos |
| `frontend/src/api/`, `auth/` | HTTP, token en memoria y sesión |
| `frontend/src/routes/`, `layout/`, `config/env.js` | Navegación, menú/configuración |
| `documentacion/` | Guías, especificaciones y material histórico |

`backend/core/database.py` y `backend/models/models.py` son reexportaciones de compatibilidad, no otra arquitectura.

### Entorno de desarrollo obligatorio

- **Windows nativo**, PowerShell como terminal principal, CMD como alternativa, Visual Studio Code y Laragon.
- Raíz del proyecto: `C:\laragon\www\bellaarte-program`. Confirmar el directorio de trabajo antes de ejecutar comandos; usar rutas Windows y herramientas instaladas de forma nativa.
- Este es el proyecto de producción y se trabaja directamente en él. Las modificaciones necesarias y las pruebas, incluidas las que usan persistencia, pueden realizarse en el mismo proyecto y entorno, sin exigir una copia del repositorio, otro proyecto ni una base de pruebas separada. Respetar el alcance autorizado y los controles de protección de datos y operaciones sensibles de esta guía.
- No ejecutar `wsl.exe`, buscar el proyecto en rutas Linux ni trabajar desde `/mnt/c/`, `/home/` o `/workspace/`. No se utiliza WSL, Ubuntu ni otras distribuciones Linux.
- Las instrucciones heredadas que sitúan BAB_VDOS en WSL o prescriben Docker, PHP, Artisan o Composer no corresponden al entorno de este proyecto. No aplicarlas ni alterar la configuración global para adaptarla como parte de una tarea local.
- No usar `sudo`, comandos de permisos Unix ni verificaciones de propietario `root` como procedimiento de desarrollo Windows. Los ejemplos genéricos de documentación o Skills deben adaptarse al entorno autorizado; no habilitan instalaciones o cambios de stack.

<a id="modulos"></a>

## 8. Módulos generales e integraciones

**Base** significa función principal implementada, no módulo terminado.

| N.º | Módulo / estado | Responsabilidad e integración |
|---|---|---|
| 1 | Usuarios y roles — **parcial** | Cuentas, JWT, roles/Casbin; permisos personalizados incompletos |
| 2 | Clientes — **parcial** | CRUD/relaciones; falta ficha histórica integral |
| 3 | Ventas — **base** | Precio, descuento, moneda, stock, comprobante/reversión; un producto por venta |
| 4 | Pedidos — **base** | Contrato, diseño, medidas, pruebas, pagos/entrega |
| 5 | Pagos — **base** | Abonos, conversión, saldo/comprobante; devoluciones pendientes |
| 6 | Inventario Boutique — **base** | Productos, tipos, detalles, entradas, stock/venta/flete |
| 7 | Inventario Taller — **base** | Insumos, unidades/movimientos; sin costo automático por pedido |
| 8 | Fletes — **base** | Reserva, entrega, garantía, devolución, usos/venta de usado |
| 9 | Agenda — **parcial** | Calendario/reprogramación de pruebas, no agenda integral |
| 10 | Gestión financiera — **base** | Ingresos derivados, egresos, devoluciones/cortes |
| 11 | Personal/remuneraciones — **pendiente como módulo específico** | Colaboradores y egreso SUELDO no equivalen a nómina/comisiones |
| 12 | Comprobantes internos — **base** | Emisión por origen, snapshot/historial e impresión no fiscal |
| 13 | Reportes/BI — **base descriptiva** | Indicadores, gráficos/reportes; sin predicción activa |
| 14 | Auditoría/backups — **base** | Trazabilidad/respaldos; recuperación no certificada |
| 15 | Notificaciones — **base** | Eventos/scripts, destinatarios, lectura/resolución |

Proveedores, monedas/cambios, tipos de producto/material/comprobante, dashboard y servicios son soporte, no módulos independientes por defecto. Dashboard actual es portada/accesos, no BI ejecutivo integral.

Flujos a preservar según servicios:

- Venta: validar stock → registrar/descontar → comprobante → auditoría/alertas; Economía deriva ingreso.
- Pedido: cliente habilitado → contrato/detalle → pruebas → pagos/saldo → entrega.
- Pago: pedido → registro/conversión → recálculo saldo → comprobante/auditoría → ingreso derivado.
- Flete: separar unidad comercial → reserva/cobro/comprobante → entrega → devolución/revisión, garantía/contador → venta/retiro.
- Taller: material → entrada/salida → stock. Destino texto, sin FK a pedido ni imputación automática de costo.
- Usuarios/roles autorizan; operaciones alimentan reportes, alertas y auditoría.

Fuentes: [servicios](backend/app/services/), [rutas SPA](frontend/src/routes/AppRoutes.jsx), [modelos](backend/app/models/__init__.py).

<a id="reglas"></a>

## 9. Reglas de negocio críticas

### Ventas, pedidos y pagos

- Producto/tipo habilitados, referencias/stock válidos, cantidad positiva y precio desde inventario; descuento dentro del subtotal y motivo coherente.
- Moneda habilitada: conversión 1 si es base, tipo activo si no. Congelar conversión histórica, sin recotizar operaciones anteriores.
- Venta inmutable tras alta; reversión única y coordinada de stock, economía, comprobante/auditoría.
- Pedido exige cliente habilitado, responsable y detalle acorde al tipo; no cambiar tipo libremente tras alta.
- Respetar contrato específico de descuento/motivo, viaje/destino y fechas: `null`/cero no son intercambiables entre módulos.
- Pagos válidos recalculan total/saldo; no superar deuda ni editar importes históricos injustificadamente. Entrega con saldo cero y fechas coherentes.
- Pruebas con número positivo, secuencia/unicidad por pedido y fecha compatible. No imponer cuatro/cinco pruebas fijas por documentos históricos.

### Inventarios y fletes

- Stock/mínimos no negativos, movimientos positivos/unidad compatible; sin conversiones implícitas.
- **Regla esperada:** movimientos/ajustes trazables, sin editar stock con historial. **Brecha:** Boutique bloquea por ventas y Taller por movimientos activos; no legitimar esos huecos.
- Desactivar/reactivar revierte/reaplica una vez validando disponibilidad. Cambiar unidad con historial requiere analizar equivalencias/datos.
- Detalle Boutique según tipo: vestido, velo, bouquet/brassier. Preservar contrato `BRASIER` y tabla `detalle_brassier_boutique`.
- Flete retira una unidad comercial y tiene configuración única por producto; no controla varios ejemplares físicos independientes por código.
- Respetar reserva, entrega, devolución/observación/arreglo y revisión; garantía separada del servicio.
- Usos válidos son devoluciones contadas. **Brecha:** número histórico de salida anulada puede consumir cupo pese a revertir contador.
- Pase a venta crea otro producto usado, stock uno; retiro/restitución depende de usos previos.

### Relaciones y concurrencia

- Cuenta tiene un rol y usuario como máximo una cuenta; no suponer múltiples roles.
- Cliente opcional en venta no elimina snapshot; pedido/salida flete requieren cliente.
- Unicidad de detalle por tabla no garantiza exclusividad entre tablas: validar tipo en aplicación.
- Referencias polimórficas de egreso/notificación/auditoría no son FK; validar tabla/identificador.
- Proteger stock, saldo, duplicación/reembolso máximo con control concurrente; commit/lock de correlativo no protegen todas las decisiones previas.

Consultar servicios `boutique_sale`, `order`, `order_payment`, `workshop` y `flete` con sufijo `_service.py` bajo `backend/app/services/`; economía/seguridad en secciones 14 y 17.

<a id="convenciones"></a>

## 10. Convenciones de desarrollo y diseño

- Analizar primero; cambios pequeños/verificables, sin refactor ajeno, duplicación/dependencias innecesarias.
- Conservar nombres: snake_case Python, convenciones React/tablas nuevas minúsculas. Distinguir API, ORM y SQL.
- Mayúsculas para texto/códigos según contrato; correo minúsculo. No normalizar claves ni restringir texto libre indiscriminadamente.
- Español latino, importes base Bs y moneda origen; accesibilidad, teclado, carga/errores y adaptación de pantalla.
- Reutilizar componentes. Gmail en formulario Usuarios no es política universal de Clientes/Proveedores; evaluar antes de extender/eliminar.
- Documentar decisiones de estados, precisión, permisos, APIs/KPI; consultar reglas empresariales no aprobadas.

<a id="backend"></a>

## 11. Normas para backend

- Routers: transporte/dependencias; Pydantic: contratos; servicios: reglas/transacciones; modelos: persistencia.
- `/api/v1`, rutas estáticas antes de dinámicas conflictivas y permiso backend explícito.
- Usar sesiones existentes, sin compartir entre solicitudes/hilos ni evolucionar esquema con create_all.
- Operación atómica: helpers no confirman parcialmente; coordinador controla commit/rollback. Preservar excepciones justificadas como historial de backup.
- Validar referencias, habilitación/estado y propiedad usuario/corte en servidor; no confiar precio/total/rol/propietario de UI.
- Decimal/redondeo explícito y NUMERIC para dinero; float heredado no autoriza imprecisión ni cambio API silencioso.
- Controlar concurrencia/duplicación y reutilizar servicios de auditoría, comprobantes/alertas, sin atajos.
- Errores consistentes sin éxito ficticio/secretos; paginación/filtros server-side evaluando consumidores.
- [Configuración central](backend/app/core/config.py); nunca PostgreSQL desde navegador o secretos en `VITE_*`.

<a id="frontend"></a>

## 12. Normas para frontend

- Componentes funcionales React/JSX, Ant Design/Router actuales; [cliente HTTP](frontend/src/api/client.js) y sesión existentes.
- Token solo en memoria: sin clientes alternativos ni credenciales en localStorage/sessionStorage.
- Registrar rutas, guards/menú coherentes; UI no sustituye permiso servidor.
- Reutilizar [formConfig](frontend/src/components/forms/formConfig.js), [FormProcessAlert](frontend/src/components/forms/FormProcessAlert.jsx), [formErrorUtils](frontend/src/components/forms/formErrorUtils.js).
- Error inequívoco al campo; proceso/ambiguo a alerta; toast para éxito/acción puntual. Preservar ubicación 422.
- Inputs Row/Col, no Space como grilla; `maskClosable={false}` en edición/detalle crítico; limpiar errores sin perder captura accidentalmente.
- Ver con GET fresco, no fila resumida; carga/vacío/error recuperable y bloqueo de doble envío.
- Form.Item/payload coherentes; números vacíos según schema, no cadena vacía.
- Distinguir fecha local y timestamp UTC; filtros/KPI/impresión compatibles. Optimizar carga sin romper navegación/sesión. Persistir filtros no autoriza persistir tokens.

<a id="datos"></a>

## 13. Normas para PostgreSQL y migraciones

- Alembic versionado en [versions](backend/alembic/versions/), modelo/documentación. No alterar migración aplicada para introducir cambio nuevo sin decisión explícita.
- Registrar modelos; revisar FK, enums, defaults, nulabilidad, precisión/SQL y datos anteriores.
- CHECK/UNIQUE/índices parciales/FK para invariantes aprobadas; Pydantic no protege escrituras externas/concurrentes.
- Planificar backfill, compatibilidad/fallo/recuperación; conservar históricos. No quitar RESTRICT/agregar cascadas destructivas por comodidad.
- No editar columnas generadas ni stock/saldo por cálculo aislado; distinguir fila/agregado.
- Índices justificados por consultas/volumen, sin duplicados; rangos temporales indexables si equivalentes.
- Destructiva: análisis, respaldo/recuperación y autorización. Alembic no autoriza tocar base real.

Código usa roles/usuarios/cuentas y tablas comerciales minúsculas; contrastar documentos antiguos con modelos/migraciones.

<a id="seguridad"></a>

## 14. Seguridad, roles, permisos y auditoría

JWT acceso/refresh HttpOnly, hash Bcrypt/Passlib; Casbin por `rol.codigo` y `dominio:accion`. Cuenta, usuario/rol habilitados.

| Rol base | Alcance principal |
|---|---|
| ADMIN | Global; auditoría/backups exclusivos |
| INV_BOUTIQUE | Tipos, proveedores, stock/entradas y consultas autorizadas |
| INV_TALLER | Tipos, insumos/movimientos Taller |
| CAJA | Ventas, fletes, pagos, comprobantes/economía por usuario/corte |
| MODISTA | Clientes, pedidos, pruebas/salidas Taller y consultas permitidas |

Fuentes: [permissions.py](backend/app/core/permissions.py), [Casbin](backend/app/security/), [dependencias](backend/app/deps/auth.py). Rol adicional en base no adquiere políticas dinámicas por existir/nombre visible.

- Menor privilegio backend por recurso, no solo ruta.
- Clave obligatoria debe exigirse en servidor; redirección actual insuficiente.
- Nunca logs/respuestas/fixtures con claves, hashes, tokens/secretos o datos personales innecesarios.
- Se permite trabajar y probar en el mismo entorno conforme a la sección 7; fallback JWT y cookie secure=False actuales no son recomendación productiva.
- Evaluar expiración, renovación/revocación y reset; revocación persistente todavía ausente.
- No debilitar validadores/políticas para pruebas. Credenciales/.env requieren autorización; VITE_* es público.

[Auditoría](backend/app/core/audit.py): contexto funcional + triggers de refuerzo; reutilizar aud_id_evento, responsable/contexto y excluir sensibles. Consulta administrativa, sin CRUD manual UI/API; no certificar inviolabilidad frente a privilegios de base no evaluados.

<a id="pruebas"></a>

## 15. Pruebas, calidad y criterios de aceptación

Verificaciones proporcionales; actualizar pruebas significativas del comportamiento, no pruebas espejo ni suites completas por documentación.

| Nivel | Impacto a cubrir |
|---|---|
| Unitarias/contratos | Schemas, normalización/cálculos/helpers |
| Integración PostgreSQL | Restricciones/relaciones/transacción/rollback/migración |
| API/autorización | Credenciales, rol/recurso/propiedad/payload/errores |
| Concurrencia | Stock/pagos/duplicación/reembolso y reversión única, sesiones independientes |
| Frontend/regresión | Captura, carga/errores/navegación/permisos/impresión |
| E2E | Recorrido empresarial cuando existan herramientas/entorno aprobados |

Actual: contratos/helpers backend y errores de formulario frontend; no suite E2E completa ni cobertura porcentual acreditada.

### Comandos y seguridad

Configuración toma DATABASE_URL o DB_* y .env: **verificar la conexión efectiva y los efectos previstos antes de tests con aplicación/persistencia**; pueden ejecutarse en la base del mismo proyecto, sin exigir una base de prueba aislada y sin imprimir credenciales. Proteger los datos empresariales y respetar las autorizaciones aplicables a escrituras sobre registros existentes. Crear/migrar base requiere autorización aplicable.

Importar [router](backend/app/api/router.py) puede sincronizar/escribir policy.csv; arranque/middleware pueden revisar/limpiar locks. Importación, TestClient o GET no garantizan ausencia de efectos: revisar fixtures/diff.

Desde backend con venv Windows:
```powershell
.\venv\Scripts\python.exe -B -m pytest tests -q -p no:cacheprovider
.\venv\Scripts\python.exe -B -m pip check
```

Temporales propios fuera del repo cuando corresponda. -B/desactivar caché no impiden escrituras a base. Desde raíz pytest.ini descubre backend/tests con intérprete correcto.

Desde frontend:
```powershell
pnpm.cmd lint
pnpm.cmd exec vitest run --no-cache
pnpm.cmd build
```

pnpm.cmd evita wrapper ps1 bloqueado, sin cambiar política del sistema; otro shell compatible admite pnpm. Build escribe dist: usar salida temporal nueva con Vite para inspección. No instalar para sortear sandbox.

Arranque existente: uvicorn main:app --reload en backend/venv, pnpm.cmd dev en frontend; no arrancar por documentación pues puede tocar base/locks.

### Resultados anteriores

Evaluación 17/10/2026: **71 backend aprobadas y 1 fallida por fecha fija**, 3 frontend aprobadas, lint/build correctos y lectura/backups verificados. **No reejecutados para esta guía.** Caso test_order_base_payload_requires_discount_reason conserva fecha vencida: reloj/datos controlados en tarea propia, sin ocultar falla.

Resultados nuevos solo si se ejecutan; distinguir error nuevo/preexistente/entorno, sin reducir validación para obtener verde.

<a id="errores"></a>

## 16. Gestión de errores, logs y observabilidad

- Preservar 422 y distinguir autenticación, permiso, inexistencia/conflicto según contrato.
- Rollback ante fallo; sin éxito ficticio/parciales ni SQL, conexiones/rutas sensibles o stack traces públicos.
- Logs técnicos distintos de auditoría: contexto/evento sin secretos/datos personales innecesarios.
- Fallback SMTP que imprime credenciales y devuelve éxito es deuda, no patrón.
- Respetar 503 por backup; no mapear a campo ni reintentar escrituras sin prevenir duplicados.
- No inventar monitoreo/trazas/alertas externas; nuevas capacidades requieren propósito/acceso/retención/validación.

<a id="economia"></a>

## 17. Comprobantes, economía y consistencia transaccional

Hecho operativo y económico distintos: venta/pago/salida conservan ingreso bruto histórico; devolución efectiva es egreso, sin borrar ingreso al anular.

- Comprobante automático en transacción, exactamente un origen/único por operación; snapshot no actualiza cliente.
- Sin alta manual/edición de importes como atajo; estado deriva del origen. HTML/window.print, **no fiscal**, sin integración tributaria acreditada.
- Base/agregados BOB, moneda/importe original y conversión preservados; garantía separada del ingreso.
- [Coordinador de devolución](backend/app/services/refund_flow_service.py); no eludir endpoints bloqueados usando helpers privados.
- **Brecha:** parcial anula origen y bloquea posteriores; cero se rechaza. No afirmar soporte completo ni cambiar regla sin tarea específica.
- CAJA requiere corte para egreso; ADMIN puede operar sin él. Propiedad/enmascaramiento también en CSV.
- Corte abierto único por cajero; egreso tiene FK al corte, ingreso usuario/rango.
- Cierre esperado consistente; **brecha:** importes recalculados y ADMIN puede anular egresos de cierres. Ajuste/inmutabilidad requiere diseño aprobado.
- Operativo puede filtrar estados distinto de económico: definir KPI, sin confundir deuda, ingreso bruto, egreso/neto.

Fuentes: receipt_service.py, income_service.py, expense_service.py, cash_cut_service.py bajo backend/app/services/.

<a id="backups"></a>

## 18. Backups y operaciones sensibles

[Servicio](backend/app/services/backup_service.py), [runtime](backend/app/core/backup_runtime.py) y [generador](backend/scripts/backup_manager.py): pg_dump -Fc, historial, tamaño/SHA-256, descarga/lock ADMIN. Síncrono, bloquea operaciones normales con excepciones definidas.

No retirar lock a ciegas ni éxito sin archivo válido. Hash correcto no certifica recuperación empresarial. Scripts backend/scripts/run_backup_job.py y run_notification_checks.py tienen modos en sus argumentos; backup recomendado domingo 02:00 America/La_Paz, programación externa por verificar.

- Backup/chequeos/reintentos escriben y pueden afectar disponibilidad.
- Restaurar/sobrescribir/mover/eliminar exige autorización; los ensayos pueden realizarse en el mismo proyecto y destino con la autorización aplicable, respaldo y recuperación previstos, sin exigir un destino aislado.
- Sin dumps públicos/Git; cambio destructivo exige respaldo, reversión/validación.
- Recuperación certificada, restauración UI/retención avanzada no acreditadas.
- Proceso colgado/EN_PROCESO residual requieren procedimiento, no borrar evidencia para desbloquear.

<a id="leny"></a>

## 19. APORTE INGENIERIL — LENY

**Actualización 19/10/2026:** Etapa 01 conversacional implementada con Qwen/Ollama local, historial privado PostgreSQL, JWT/Casbin y chat React; comprobada mediante conversación real desde el ERP en una base aislada. La revisión0017 se aplicó posteriormente con autorización a `bellaarte_db:5432`, con respaldo y verificación de estructura/permisos; historial y estado comprobados desde el ERP habitual. Ver [módulo LENY](documentacion/MODULO_LENY.md). Las capacidades analíticas siguientes permanecen planificadas: lenguaje natural → operaciones analíticas verificables sobre datos autorizados. Historia, indicadores/predicciones/recomendaciones explicables, sin reemplazar transacciones o responsabilidad humana.

| Componente previsto | Función |
|---|---|
| LLM local | Comprender/redactar con resultados sustentados |
| SQL controlado | Recuperación autorizada con herramientas acotadas |
| BI | Descriptivo, diagnóstico/comparativo |
| Machine Learning | Predicción con historia adecuada/validada |
| AutoML controlado | Viabilidad/comparación de técnicas permitidas |
| RAG contextual | Reglas/glosarios/documentación con procedencia |
| Orquestador | Coordinar herramientas/pasos trazables |
| Seguridad | Usuario/rol/módulo/recurso/datos |

Primera versión: consultas, información, cálculo/interpretación de indicadores, análisis/recomendaciones. Pronóstico solo con datos/evaluación suficientes.

**RAG-SPEC-01, actualización 19/10/2026:** biblioteca documental ADMIN implementada y probada en PostgreSQL aislado con migración0019, originales privados, versiones, ACL, papelera y respaldo conjunto. Con autorización expresa posterior se aplicó0019 a bellaarte_db:5432 y se habilitó en backend/.env; listado/actualización verificados desde la sesión ADMIN habitual y respaldo conjunto privado comprobado. La selección/carga del navegador fue aceptada posteriormente por el propietario en el chat; distinguir esa evidencia de las pruebas ejecutadas por el agente. Ver módulo/reporte LENY y leny_rag01_business_deployment.json. Se conservó DOC preexistente excluido y no se cambiaron versiones actuales.

**RAG-SPEC-02, actualización 19/10/2026:** implementada y desplegada con autorización, migración0020 y pgvector0.8.7 en esquema leny. Extracción/OCR local, fragmentos trazables y embeddings1024 con qwen3-embedding:0.6b existente, CPU obligatoria. Worker de arranque manual separado de Uvicorn, trabajos durables, idempotencia, cancelación, checkpoints y coordinador PostgreSQL compartido con el chat. Recorrido real en ERP habitual: cuatro fragmentos/cuatro vectores validados. Código deshabilitado por defecto, activación local en backend/.env. Se preservaron versiones actuales y public/roles; pruebas y riesgos en documentacion/MODULO_LENY.md, REPORTE_IMPLEMENTACION_LENY.md y evidencias/leny_rag02_*. No inferir exactitud integral de OCR ni seguridad absoluta de esos resultados.

**RAG-SPEC-03, actualización20/10/2026:** implementada y desplegada después de autorización separada.0021 y rollback se ensayaron en55432; luego0021 se aplicó a bellaarte_db:5432 con respaldo completo verificado. Publicación ADMIN fija versión+índice; recuperación exacta con ACL en SQL; fuentes privadas, singleton durable, streaming e historial. LENY_RAG_CHAT_ENABLED=true y residencia0 adoptada tras pruebas reales de cuatro formatos, ataque focalizado, abstención y restauración; se mantienen márgenes2GiB/1GiB. Backend recargado, Vite5173 reiniciado con aprobación específica y worker manual RAG_READY. El propietario aprobó expresamente publicar versión1 del manual existente para ADMIN/CAJA; publicación y consulta real con S1/página1 comprobadas desde React, sin guardar su texto privado en evidencias. La base conserva los cinco roles oficiales y un DOC preexistente adicional: no fue creado ni modificado y no tiene política LENY. Ver reporte/evidencias leny_rag03_*; no confundir esos escenarios con certificación global. SPEC-04 conserva calidad, falsos positivos del clasificador y carga sostenida.

### Caso predictivo y evaluación

- **Objetivo:** cantidad de unidades vendidas por categoría para el siguiente mes calendario.
- **Unidad:** categoría comercial por mes; **variable:** unidades efectivamente vendidas, no dinero ni demanda total no satisfecha.
- **Horizonte:** siguiente mes calendario, no ventana indistinta de 30 días.
- **Fuentes:** historia validada, categorías/estados documentados.
- **Evaluación:** MAE contra baseline comparable, separación temporal y sin fuga.

Evaluar calidad, completitud, cancelaciones, cambios de categoría e historia suficiente antes de declarar apto el dataset. Dataset exacto/baseline/técnicas se aprobarán en etapa experimental.

**CRISP-DM:** 1) comprensión del negocio; 2) comprensión de datos; 3) preparación; 4) modelado; 5) evaluación; 6) despliegue. Para componente predictivo, sin sustituir ingeniería/pruebas del ERP/agente.

| Métrica | Finalidad | Criterio preliminar previsto |
|---|---|---|
| ERA | Exactitud de respuestas analíticas contra casos verificados | Al menos 90 % |
| MAE | Error de predicción mensual | Inferior al baseline comparable |
| CCA | Cumplimiento del control de acceso en batería definida | 100 % y ninguna exposición de datos protegidos |

**Criterios futuros, no resultados alcanzados.** Definir batería, denominadores/referencias/protocolo antes de medir.

<a id="limites-leny"></a>

## 20. Restricciones y límites actuales de LENY

- No implementarlo incidentalmente al consolidar/documentar ERP.
- Inicialmente **lectura controlada**: sin modificar autónomamente ventas, saldos, inventarios/remuneraciones u otros registros críticos.
- Consultas, recuperado y salida LLM son no confiables: no amplían permisos ni se ejecutan automáticamente como SQL.
- Sin cuentas alternativas/consultas sin filtros para eludir acceso; separar observado/calculado/estimado/recomendado.
- LLM, embeddings, orquestación/despliegue definitivos requieren evaluación/aprobación futura. Pandas/NumPy o ejemplos RAG no prueban LENY.

<a id="integracion-leny"></a>

## 21. Preparación de integración futura

En tareas ERP autorizadas favorecer contratos, validación, indicadores y auditoría reutilizables; no crear anticipadamente tablas/endpoints/dependencias LENY.

Diseño futuro: identidad/permisos ERP comprobados por herramienta/recurso; lectura acotada por filas/tiempo/recursos; sin credenciales privilegiadas al modelo; resultados con filtros/período/unidad/moneda/procedencia; auditoría minimizada y resistencia a instrucciones maliciosas en consultas/documentos.

Separar reales/estimados y registrar versiones de datasets/modelos/evaluaciones/predicciones; incorporar modelos adicionales sin alterar transacciones. Proceso interno, servicio Python u otra organización: justificar/aprobar posteriormente, sin fijar despliegue aquí.

<a id="protocolo"></a>

## 22. Protocolo de trabajo de los agentes

**Antes:** comprender alcance/resultado; leer instrucciones; revisar Git/trabajo ajeno; identificar módulos/contratos/reglas/pruebas; inspeccionar efectos; evaluar datos/seguridad/integraciones. Resolver hechos leyendo código, preguntar solo decisiones críticas/autorización necesaria.

**Durante:** alcance/arquitectura/compatibilidad; cambios mínimos; atomicidad/precisión/permisos/auditoría; pruebas pertinentes y documentación. Si falta decisión, pausar acción dependiente y continuar trabajo seguro independiente.

**Después:** diff/archivos nuevos; verificaciones proporcionales; reglas/contratos y efectos en economía/seguridad/auditoría; documentación y entrega verificable.

No repetir autorización concreta ya concedida. Si el entorno exige otra, explicar restricción/acción real; sin flujos inventados para lecturas/ediciones reversibles autorizadas.

<a id="autorizacion"></a>

## 23. Acciones prohibidas sin autorización

Autorización explícita concreta, salvo ya concedida para mismo alcance:

- Eliminar/sobrescribir datos, base real u operaciones comerciales de prueba sobre registros existentes.
- Migraciones destructivas, esquema real fuera de procedimiento, restauración/sobrescritura de backups.
- Seeds que alteran registros/cuentas, permisos de usuarios reales/importes económicos.
- Secretos/credenciales, dependencias nuevas o actualización de versiones principales.
- Stack/arquitectura, reestructurar módulos, producción, commits/publicaciones no solicitados.
- Borrar archivos ajenos/sobrescribir trabajo de colaboradores.

Mejora genérica no autoriza esas acciones: preparar análisis/cambios seguros revisables antes de la operación sensible final. No sudo, permisos 777, Docker root/eliminación de volúmenes como arreglo genérico; no introducir Docker donde no hay configuración ni eludir sandbox/autenticación/permisos.

<a id="documentacion"></a>

## 24. Mantenimiento documental y fuentes de verdad

Para **lo existente**, prioridad: 1) código/configuración efectiva; 2) esquemas/migraciones/contratos; 3) manifiestos/lockfiles; 4) pruebas/resultados reproducibles; 5) documentación vigente; 6) reporte de estado; 7) histórico; 8) planes futuros.

Para **lo que debe implementarse**, requisitos aprobados del propietario. Código no justifica defecto; plan no demuestra capacidad activa.

Referencias: [README](README.md), [backend](backend/README.md), [frontend](frontend/README.md), [desarrollo](documentacion/GUIA_DESARROLLO.md), [UX/UI](documentacion/GUIA_UX_UI.md), [formularios](documentacion/ESTANDARES_DE_DISENO_FORMULARIOS.md) y documento del dominio.

Conflictos conocidos: versiones/nombres SQL antiguos, enlaces de seguridad faltantes, comprobantes/ingresos anulados y reglas toast/moneda desactualizados. Contrastar; preguntar si cambia negocio importante, sin crear archivos/cambiar API por una referencia vieja.

Actualizar guía ante cambio aprobado de stack/arquitectura/módulos/convenciones con fecha/evidencia; retirar deuda solo comprobada. Sin cantidades de registros/resultados como verdades permanentes.

Instrucción por directorio precisa global respetando seguridad/instrucciones superiores. Resolver contradicción material antes de acción afectada; cambio rutinario autorizado no exige nueva decisión arquitectónica.

<a id="terminacion"></a>

## 25. Criterios para considerar terminada una tarea

- Resultado/alcance cumplidos, sin cambios incidentales/pérdida de trabajo ajeno.
- Contratos, reglas, permisos/datos/historia económica/auditoría revisados.
- Migración/compatibilidad/documentación cuando procede, sin acciones sensibles no autorizadas.
- Verificaciones suficientes ejecutadas; fallos/límites explícitos.
- Diff/nuevos revisados; entrega explica cambio, motivo, evidencia/pendientes.
- Sin presentar propuesta/simulación/validación parcial como capacidad productiva completa.

Solo documentación: Markdown/enlaces/exactitud/vigencia/secretos/diff; no operaciones, seeds/migraciones/arranque para aumentar artificialmente verificación.

<a id="orquestacion-codex"></a>

## 26. ORQUESTACIÓN DE CODEX, SUBAGENTES Y SKILLS

### 26.1. Coordinación y configuración local

Codex es el agente principal y mantiene responsabilidad sobre el resultado integrado. Debe comprender solicitudes e instrucciones, determinar complejidad, planificar cuando corresponda, seleccionar especialistas, delimitar tareas, gestionar dependencias y archivos, integrar resultados, verificar el objetivo y comunicar evidencia y limitaciones.

Configuración exclusivamente para Codex en [config.toml](.codex/config.toml); perfiles independientes en `.codex/agents/`. No crear configuraciones para otros sistemas ni modificar la configuración global del usuario. Los perfiles se descubren mediante su mecanismo nativo; cada TOML define `name`, `description` y `developer_instructions`, sin un registro duplicado de roles.

`agents.enabled = true` y `agents.max_concurrent_threads_per_session = 2`: máximo dos hilos de subagentes abiertos concurrentemente, además del principal. Cerrar hilos terminados que ya no sean necesarios antes de abrir otros. El límite no obliga a utilizar dos agentes. No fijar modelos ni esfuerzo de razonamiento en estos perfiles: heredan los del principal salvo selección explícita aplicable de la sesión. No introducir cambios de proveedor, permisos o herramientas.

### 26.2. Selección y responsabilidades

| Perfil | Delegar cuando | Ámbito habitual y coordinación |
|---|---|---|
| [backend](.codex/agents/backend.toml) | FastAPI, contratos Pydantic, reglas, JWT/Casbin, transacciones, errores o auditoría | `backend/app/api/`, `services/`, `schemas/`, `core/`, `deps/`, `security/`; acordar API con frontend y persistencia con data_sql mediante el principal |
| [frontend](.codex/agents/frontend.toml) | React/JSX, formularios, navegación, Ant Design, integración Axios, gráficos, accesibilidad o rendimiento de interfaz | `frontend/src/`; preservar contratos, componentes y sesión; informar endpoints requeridos; validación con qa_testing |
| [qa_testing](.codex/agents/qa_testing.toml) | Verificación independiente, diagnóstico, pruebas, permisos, casos límite o regresiones | Inspección de `backend/tests/`, `backend/app/` y `frontend/src/`; editar pruebas/fixtures solo por delegación expresa; sin corregir código funcional |
| [data_sql](.codex/agents/data_sql.toml) | PostgreSQL, modelos/relaciones, consultas SQL/ORM, agregaciones, índices, bloqueos o integridad | `backend/app/models/`, `backend/alembic/`, `backend/app/services/`, `backend/app/core/database.py`; backend conserva API y reglas; sin ejecución de migraciones o cambios sobre datos reales |

Las rutas delimitan especialidades habituales, no autorizan ediciones indiscriminadas. El principal asigna archivos concretos y coordina cualquier ampliación. Ante cambios integrales, definir contratos/dependencias primero y ejecutar etapas secuenciales cuando compartan archivos.

### 26.3. Política de delegación y coste

- **Sin delegación:** tarea sencilla, lectura de uno o dos archivos, cambio mínimo o coste de coordinación superior al beneficio.
- **Un especialista:** dominio claro o revisión independiente acotada.
- **Hasta dos especialistas:** trabajo complejo con entregables independientes y beneficio concreto de calidad o tiempo.
- No activar los cuatro perfiles automáticamente, repetir análisis ya resueltos ni transferir toda la documentación a cada agente. Entregar contexto mínimo y referencias pertinentes.
- Los subagentes no inician otros subagentes ni ciclos de consulta/delegación sin autorización del principal; coordinan dependencias a través de él.

### 26.4. Contrato de delegación

Cada encargo debe incluir:

1. Objetivo concreto y contexto mínimo necesario.
2. Módulos/archivos relevantes y responsable de edición.
3. Alcance permitido: lectura, pruebas o modificaciones concretas.
4. Restricciones, permisos efectivos y dependencias con otros trabajos.
5. Resultado esperado y criterios de aceptación verificables.
6. Formato de retorno y verificaciones pertinentes.

No delegar «revisar todo y mejorar lo encontrado». Delimitar el flujo y la evidencia buscada. Una delegación no amplía la autorización del usuario ni resuelve por sí misma decisiones empresariales pendientes.

### 26.5. Entrega, integración y conflictos

Cada especialista devuelve trabajo realizado, archivos inspeccionados/modificados, hallazgos, pruebas/comandos y resultados, riesgos/limitaciones y decisiones pendientes. Citar rutas y evidencia suficiente; no trasladar logs completos ni información sensible. Distinguir propuesta, modificación, verificación estática y ejecución real.

qa_testing debe indicar además módulo/flujo, resultado esperado/obtenido, reproducción, severidad, recomendación y verificaciones pendientes. Priorizar defectos funcionales y de seguridad.

Cuando se necesite el mismo archivo, el principal asigna **un único responsable de modificación**; los demás pueden inspeccionar/revisar sin editar. No realizar escrituras simultáneas contradictorias ni sobrescribir trabajo ajeno. Integrar cambios, revisar diff y contratos y ejecutar verificaciones proporcionales; resolver dependencias por etapas. El principal conserva responsabilidad sobre las afirmaciones de la entrega final.

### 26.6. Skills existentes y uso selectivo

**Subagente:** ejecuta una tarea delegada con especialidad y contexto propio. **Skill:** aporta instrucciones y recursos reutilizables para una actividad. Son complementarios; no convertir Skills en agentes ni instalar perfiles dentro de `.agents/skills/`.

Conservar el descubrimiento nativo de Codex en [.agents/skills/](.agents/skills/). Leer el `SKILL.md` pertinente cuando corresponda y abrir referencias adicionales solo si la tarea lo exige; no cargar todas las Skills ni duplicar sus instrucciones en perfiles o en esta guía.

| Skill | Aplicación | Agentes habituales |
|---|---|---|
| [frontend-design](.agents/skills/frontend-design/SKILL.md) | Diseño visual, componentes o experiencia de usuario solicitados, dentro de Ant Design y los patrones actuales | Principal y frontend |
| [accessibility](.agents/skills/accessibility/SKILL.md) | Accesibilidad, teclado, formularios, lectores de pantalla y evaluación de interfaces | Principal, frontend y qa_testing |
| [seo](.agents/skills/seo/SKILL.md) | Posicionamiento de páginas públicas pertinentes; no requisito general del ERP autenticado | Principal y frontend cuando corresponda |

Todos pueden aprovechar Skills pertinentes disponibles en la sesión; no presumir Skills de backend o datos que no existan. No activar automáticamente las tres. Los ejemplos genéricos de una Skill no autorizan instalaciones, nuevas dependencias, cambios de arquitectura ni rediseños ajenos a la tarea. Respetar el alcance aprobado, las convenciones del proyecto y el entorno Windows.

Preservar nombres, metadatos, recursos y licencias. No mover/duplicar carpetas, crear enlaces simbólicos, instalar/eliminar Skills ni alterar `skills-lock.json` sin autorización específica. Los enlaces a Skills opcionales ausentes deben identificarse como tales, sin instalaciones automáticas. Las correcciones locales de enlaces no actualizan el lock de origen ni certifican sus hashes contra el contenido corregido.

### 26.7. Seguridad y operaciones sensibles

Los subagentes heredan las restricciones y permisos efectivos de la sesión principal. Una instrucción TOML de «solo lectura» es una regla de comportamiento, **no aislamiento técnico**. Aplican los controles reales de Codex y las autorizaciones de la sección 23, tanto al principal como a especialistas.

No ampliar permisos, debilitar Casbin, revelar secretos ni realizar operaciones destructivas sin autorización aplicable. Las modificaciones y las pruebas con persistencia pueden realizarse en el mismo proyecto y entorno de producción, sin exigir un entorno separado. Verificar efectos de comandos, imports y fixtures; proteger los datos empresariales y respetar las autorizaciones de la sección 23 para escrituras sobre registros existentes. Preservar cambios preexistentes, incluso archivos no agregados a Git.

### 26.8. LENY y mantenimiento de la configuración

Esta organización sirve a la consolidación del ERP y a tareas LENY expresamente aprobadas. El núcleo conversacional Etapa 01 está integrado; las herramientas analíticas de las secciones 19 a 21 permanecen planificadas. No crear perfiles LLM, RAG, ML o AutoML incidentalmente; su etapa específica evaluará especialistas e integración.

Antes de modificar perfiles, comprobar versión instalada de Codex y documentación oficial vigente. Validar sintaxis TOML con un parser disponible, campos obligatorios, nombres únicos, límite concurrente y ausencia de cambios globales o modelos impuestos. Verificar frontmatter, rutas/anclajes de Skills y conservación de esta guía. No instalar dependencias únicamente para validar.

Fuentes de configuración: [subagentes](https://learn.chatgpt.com/docs/agent-configuration/subagents), [referencia de configuración](https://learn.chatgpt.com/docs/config-file/config-reference) y [Skills](https://learn.chatgpt.com/docs/build-skills). Volver a contrastarlas si cambia Codex; no copiar claves heredadas cuando exista una alternativa compatible.

Comprobar reconocimiento de perfiles mediante inspección ligera si el cliente lo permite, sin lanzar tareas complejas o cuatro agentes para demostrar disponibilidad. Si no aparecen, abrir una sesión nueva desde la raíz del proyecto para recargar y revisar diagnóstico. Las políticas de confianza/configuración administrada pueden condicionar la carga: no cambiarlas automáticamente. En cada entrega distinguir **archivos creados**, **sintaxis validada**, **perfiles reconocidos** y **delegación ejecutada**; no afirmar los dos últimos sin evidencia.
