# Módulo Tipo Cambio Moneda

**Estado vigente TC-02, 04/11/2026:** automatización USD/BOB desplegada y tarea
Windows activa desde esta fecha. Primera consulta verificada: 12.0600 BOB/USD,
vigencia 04/11/2026, un intento exitoso. Consulta diaria 05:00 Bolivia, reintento
una hora después de fallar y máximo diez llamadas diarias compartidas con
recuperación. Nueva pantalla ADMIN de registros y estado funcional disponible
según permisos de lectura. Ver [funcionamiento, pruebas y despliegue TC-02](SPEC_TC_02_IMPLEMENTACION.md).
La exclusión de automatización descrita abajo corresponde al alcance histórico
de TC-01, ahora extendido por TC-02.

**Actualización SPEC-TC-01, 04/11/2026.** Las reglas siguientes sustituyen el
contrato histórico al pie. Ver [implementación y pruebas](SPEC_TC_01_IMPLEMENTACION.md).

## Contrato vigente desde revisión 0023

`tipo_cambio_moneda` mantiene `NUMERIC(12,4)` y sus siete columnas anteriores.
Agrega únicamente `tcm_origen VARCHAR(12)`, `tcm_fuente VARCHAR(64)` y
`tcm_fec_consulta TIMESTAMPTZ`. Las filas heredadas quedan MANUAL, con fuente y
consulta nulas, sin modificar valores, estados o fechas. `usu_id` conserva su FK
y admite NULL por decisión aprobada: MANUAL exige autor; AUTO usa NULL/SISTEMA.
`moneda` no cambia de estructura; BOB conserva código/base y referencia 1.

`tipo_cambio_registros` tiene exactamente las diez columnas aprobadas. Conserva
intentos y fecha oficial mediante `tcm_id`; no hay `tcm_fecha_vigencia` ni
`tcs_mensaje`. El registro en ERP no se presenta como vigencia oficial.

- Una nueva tasa operativa bloquea la moneda, desactiva su activo e inserta una
  nueva fila activa de forma atómica, protegida por el índice parcial existente.
- La recuperación y carga histórica insertan inactivas.
- Editar el valor de una MANUAL crea otro ID activo, conservando el valor anterior.
  Editar solo observaciones conserva ID, valor y estado.
- Ningún usuario puede editar o cambiar directamente el estado de AUTOMATICO.
- Una MANUAL inactiva no se reactiva: para recuperar su valor se registra otra.
  Se permite desactivar una MANUAL activa, salvo BOB.
- Las monedas deshabilitadas no admiten nuevas cotizaciones operativas.
- Ventas, pagos, fletes y comprobantes conservan snapshots congelados.

Se conservan las rutas descritas abajo. POST exige activo true; PATCH acepta valor
y observaciones opcionales, y devuelve nuevo ID si cambia el valor. `/status`
rechaza AUTO y reactivación histórica con 409. Valores inválidos producen 422.
Enviar `valor_bob` como cadena decimal, por ejemplo `"6.9600"`, con máximo cuatro
decimales y ocho enteros. La respuesta usa cadena decimal e incluye `origen`,
`fuente` y `fecha_consulta`; estos campos no admiten escritura humana.

ADMIN gestiona exclusivamente tasas manuales; CAJA e INV_BOUTIQUE conservan
lectura, con autorización backend. La UI existente admite Decimal, presenta
procedencia/SISTEMA y bloquea edición AUTO y reactivación histórica. Reportes
distinguen «último registro» de «tasa activa».

Por excepción aprobada, las operaciones futuras de esta tabla no generan
`EXCHANGE_RATE_*` ni usan su trigger general. Se conserva auditoría anterior y
la del catálogo moneda. El registro técnico no documenta toda edición manual
de observaciones. No hay nuevas pantallas, consulta externa, tareas o
notificaciones; automatización y vigencia externa corresponden a TC-02.

## Referencia histórica anterior a 0023

## Objetivo

Documentar `tipo_cambio_moneda`, usado para congelar el valor de conversión en ventas boutique.

## Tabla implementada

- `tipo_cambio_moneda`

## Columnas clave

- `tcm_id`
- `mon_id`
- `usu_id`
- `tcm_valor_bob`
- `tcm_fec_reg`
- `tcm_obs`
- `tcm_activo`

## Reglas de negocio

- `tcm_valor_bob > 0`
- solo puede existir un tipo de cambio activo por moneda
- si se crea uno nuevo activo, el anterior activo se desactiva
- para la moneda base, el valor activo debe ser `1`
- no se pueden activar tipos de cambio sobre monedas deshabilitadas

## API

- `GET /api/v1/monedas/tipos-cambio`
- `GET /api/v1/monedas/tipos-cambio/{id}`
- `POST /api/v1/monedas/tipos-cambio`
- `PATCH /api/v1/monedas/tipos-cambio/{id}`
- `PATCH /api/v1/monedas/tipos-cambio/{id}/status`

## Permisos

`ADMIN`:

- CRUD completo

`CAJA` e `INV_BOUTIQUE`:

- lectura

## Frontend

Ruta:

- `/app/monedas/tipos-cambio`

## Auditoría

- `EXCHANGE_RATE_CREATED`
- `EXCHANGE_RATE_UPDATED`
- `EXCHANGE_RATE_STATUS_CHANGED`
