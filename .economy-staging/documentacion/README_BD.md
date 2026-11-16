# README – BASE DE DATOS V4

## BELLAARTE BOUTIQUE

**Motor de base de datos:** PostgreSQL 17  
**Versión documentada:** Base de Datos V4  
**Enfoque:** gestión empresarial, inventario, pedidos, fletes, pagos, comprobantes internos, multimoneda, auditoría y notificaciones.

\---

## 1\. Descripción general

La base de datos V4 de **BELLAARTE BOUTIQUE** fue diseñada para centralizar y controlar los procesos operativos, comerciales, administrativos y financieros de la empresa. Su estructura responde al modelo real de trabajo de la boutique, donde conviven tres flujos principales de ingreso:

- venta directa de productos de boutique;
- flete de vestidos, principalmente vestidos de 15 años;
- pedidos de confección personalizada y sus pagos parciales o finales.

La versión V4 mejora la estructura anterior incorporando proveedores, entradas de inventario, multimoneda, tipos de cambio, comprobantes internos, trazabilidad de cambios de estado, auditoría y notificaciones operativas. La base mantiene una separación clara entre tablas maestras, tablas operativas, tablas detalle, tablas documentales y tablas de control.

La regla económica principal del sistema es que los precios base se manejan en **bolivianos (Bs)**. Las monedas externas se utilizan para mostrar equivalencias y registrar pagos en moneda elegida por el cliente, congelando el tipo de cambio usado en la operación. Esto permite mantener reportes consistentes en Bs sin perder la trazabilidad del cobro real.

Los comprobantes internos se mantienen como documentos de control comercial y administrativo. No reemplazan una factura, nota fiscal ni documento equivalente tributario. Su función es dejar constancia interna y entregar un respaldo comercial al cliente por ventas, pagos de pedido y fletes.

\---

## 2\. Objetivo de la base de datos

El objetivo principal de la base de datos es centralizar la información de BELLAARTE BOUTIQUE para mejorar el control de ventas, pedidos, inventarios, pagos, fletes, egresos, comprobantes, notificaciones y auditoría.

Objetivos específicos:

- reducir la dependencia de registros manuales, hojas Excel y cuadernos físicos;
- mejorar la trazabilidad de clientes, pedidos, pruebas, ventas, pagos y fletes;
- controlar inventario de boutique e inventario de taller mediante entradas y salidas formales;
- documentar operaciones económicas mediante comprobantes internos no fiscales;
- permitir reportes de ingresos, egresos, saldos, stock, fletes, pruebas y entregas;
- conservar trazabilidad de cambios de estado, anulaciones y cancelaciones;
- permitir crecimiento progresivo del sistema sin rediseñar la estructura completa.

\---

## 3\. Estructura general por módulos

La base de datos se organiza en los siguientes módulos:

- **Seguridad y acceso:** `ROL`, `USUARIO`, `CUENTA`.
- **Clientes y proveedores:** `CLIENTE`, `PROVEEDOR`.
- **Multimoneda:** `MONEDA`, `TIPO\_CAMBIO\_MONEDA`.
- **Inventario boutique:** `TIPO\_ITEM\_BOUTIQUE`, `ITEM\_BOUTIQUE`, `DETALLE\_BRASSIER\_BOUTIQUE`, `DETALLE\_VESTIDO\_BOUTIQUE`, `DETALLE\_VELO\_BOUTIQUE`, `DETALLE\_BOUQUET\_BOUTIQUE`, `ENTRADA\_ITEM\_BOUTIQUE`, `VENTA\_BOUTIQUE`.
- **Fletes:** `FLETE\_VESTIDO`, `SALIDA\_FLETE`.
- **Inventario taller:** `TIPO\_INVENTARIO\_TALLER`, `INVENTARIO\_TALLER`, `ENTRADA\_INVENTARIO\_TALLER`, `SALIDA\_MATERIAL\_TALLER`.
- **Pedidos:** `PEDIDO`, `PEDIDO\_VESTIDO`, `PEDIDO\_VELO`, `PEDIDO\_COLA`, `PEDIDO\_MANGA`, `PEDIDO\_BOUQUET`, `PRUEBA\_PEDIDO`, `PAGO\_PEDIDO`.
- **Documentos internos:** `TIPO\_COMPROBANTE`, `COMPROBANTE\_INTERNO`, `DETALLE\_COMPROBANTE`.
- **Finanzas:** `EGRESO`.
- **Control interno:** `AUDITORIA\_SISTEMA`, `NOTIFICACION`.

\---

## 4\. Reglas globales del modelo

### 4.1 Moneda base

La moneda base del sistema es el boliviano. Todos los precios maestros de productos, pedidos, fletes, inventario y egresos se registran en Bs. Las otras monedas se usan para conversión, visualización y cobro.

Reglas principales:

- solo debe existir una moneda base activa en `MONEDA`;
- el índice `UQ\_MONEDA\_BASE` evita que existan varias monedas con `MON\_ES\_BASE = TRUE`;
- cada operación monetaria debe conservar el tipo de cambio usado en ese momento;
- los reportes económicos generales deben consolidarse en Bs.

### 4.2 Tipo de cambio

`TIPO\_CAMBIO\_MONEDA` registra el valor de una moneda respecto al boliviano. El campo `TCM\_VALOR\_BOB` indica cuántos bolivianos equivale una unidad de esa moneda.

Ejemplo:

- 1 USD = 9.80 Bs → `TCM\_VALOR\_BOB = 9.80`;
- 1 PEN = 2.50 Bs → `TCM\_VALOR\_BOB = 2.50`;
- 1 BOB = 1 Bs → `TCM\_VALOR\_BOB = 1`.

El índice `UQ\_TIPO\_CAMBIO\_ACTIVO\_MONEDA` evita más de un tipo de cambio activo por moneda.

### 4.3 Trazabilidad de estados

Las tablas operativas que pueden cambiar de estado deben conservar:

- estado actual;
- fecha del cambio de estado;
- motivo del cambio de estado.

El usuario que realiza el cambio debe quedar registrado principalmente en `AUDITORIA\_SISTEMA`. En las tablas operativas se guarda el hecho del cambio, pero no necesariamente el usuario del cambio.

Tablas con trazabilidad de estado:

- `VENTA\_BOUTIQUE`;
- `SALIDA\_FLETE`;
- `PEDIDO`;
- `PAGO\_PEDIDO`;
- `COMPROBANTE\_INTERNO`;
- `EGRESO`.

### 4.4 Columnas generadas

La BD usa columnas generadas para valores que se calculan dentro de la misma fila y no deben ser editados manualmente.

Ejemplos:

- `VENTA\_BOUTIQUE.VEB\_TOT` = cantidad × precio unitario − descuento;
- `SALIDA\_FLETE.SFL\_TOTAL\_FLETE` = precio de flete − descuento;
- `PEDIDO.PED\_PRE\_TOT` = precio base − descuento;
- `PAGO\_PEDIDO.PPD\_MONTO\_BOB` = monto pagado × tipo de cambio usado;
- `EGRESO.EGR\_MONTO` = cantidad × precio unitario.

Los valores acumulados, como `PED\_TOTAL\_PAGADO`, `PED\_SALDO`, `ITB\_STOCK`, `INT\_STOCK` y `FLE\_SALIDAS\_ACTUALES`, no deben ser columnas generadas porque dependen de operaciones en otras tablas. Estos valores deben actualizarse mediante backend, procedimientos o transacciones controladas.

\---

## 5\. Descripción funcional de tablas

### `ROL`

Define los roles del sistema y permite clasificar permisos de acceso. Se relaciona con `CUENTA`, ya que cada cuenta debe tener un rol asignado.

**Campos principales:** `ROL\_ID`, `ROL\_NOM`, `ROL\_DES`, `ROL\_HAB`, `ROL\_FEC\_REG`.

**Restricciones relevantes:**

- `ROL\_NOM` es único;
- `ROL\_HAB` indica si el rol puede seguir usándose.

\---

### `USUARIO`

Registra al personal interno que utiliza el sistema. Sirve como referencia para operaciones como ventas, pagos, entradas de inventario, salidas de material, comprobantes, tipos de cambio, egresos, auditoría y notificaciones.

**Campos principales:** `USU\_ID`, `USU\_NOM`, `USU\_APE\_PAT`, `USU\_APE\_MAT`, `USU\_CEL`, `USU\_CI`, `USU\_COR`, `USU\_FEC\_TRA`, `USU\_HAB`, `USU\_FEC\_REG`.

**Restricciones relevantes:**

- `USU\_CEL`, `USU\_CI` y `USU\_COR` son únicos cuando tienen valor;
- `USU\_HAB` permite habilitar o deshabilitar usuarios sin eliminarlos.

\---

### `CUENTA`

Almacena las credenciales de acceso del sistema. Relaciona a un usuario con un rol.

**Campos principales:** `CUE\_ID`, `USU\_ID`, `ROL\_ID`, `CUE\_NOM\_USU`, `CUE\_CON`, `CUE\_HAB`, `CUE\_FEC\_CRE`, `CUE\_ULT\_ACC`.

**Relaciones:**

- `CUENTA.USU\_ID` → `USUARIO.USU\_ID`;
- `CUENTA.ROL\_ID` → `ROL.ROL\_ID`.

**Restricciones relevantes:**

- `CUE\_NOM\_USU` es único;
- las contraseñas deben almacenarse en hash desde backend.

\---

### `CLIENTE`

Registra la información personal y de contacto de los clientes. Se utiliza en ventas, pedidos, fletes y comprobantes.

**Campos principales:** `CLI\_ID`, `CLI\_COD`, `CLI\_NOM`, `CLI\_APE\_PAT`, `CLI\_APE\_MAT`, `CLI\_CEL`, `CLI\_CEL\_REF`, `CLI\_COR`, `CLI\_CI`, `CLI\_PAIS`, `CLI\_CIUDAD`, `CLI\_ZONA`, `CLI\_CALLE`, `CLI\_OBS`, `CLI\_HAB`, `CLI\_FEC\_REG`.

**Restricciones relevantes:**

- `CLI\_COD` es único;
- `CLI\_COR` y `CLI\_CI` son únicos cuando se registran;
- `CLI\_CEL` es obligatorio, pero no necesariamente único, permitiendo casos familiares o números compartidos.

\---

### `PROVEEDOR`

Centraliza los datos de proveedores de boutique y taller. Reemplaza la captura de proveedores como texto libre dentro de inventarios.

**Campos principales:** `PRO\_ID`, `PRO\_NOM`, `PRO\_APE\_PAT`, `PRO\_APE\_MAT`, `PRO\_NOM\_COMERCIAL`, `PRO\_CEL`, `PRO\_CEL\_SEC`, `PRO\_COR`, `PRO\_PAIS`, `PRO\_CIUDAD`, `PRO\_DIR`, `PRO\_OBS`, `PRO\_HAB`, `PRO\_FEC\_REG`.

**Relaciones:**

- `ITEM\_BOUTIQUE.PRO\_ID` puede apuntar a `PROVEEDOR.PRO\_ID`;
- `INVENTARIO\_TALLER.PRO\_ID` puede apuntar a `PROVEEDOR.PRO\_ID`;
- las entradas de inventario también pueden conservar proveedor.

**Restricciones relevantes:**

- `PRO\_CEL` y `PRO\_COR` son únicos cuando se registran;
- `PRO\_HAB` permite retirar un proveedor sin eliminar su historial.

\---

### `MONEDA`

Catálogo de monedas disponibles en el sistema. Permite registrar monedas como BOB, USD, PEN o EUR.

**Campos principales:** `MON\_ID`, `MON\_COD`, `MON\_NOM`, `MON\_SIMBOLO`, `MON\_ES\_BASE`, `MON\_HAB`, `MON\_FEC\_REG`.

**Restricciones relevantes:**

- `MON\_COD` es único;
- `UQ\_MONEDA\_BASE` garantiza una única moneda base.

**Lógica:**

Los precios maestros no se duplican por moneda. Se guardan en Bs y se convierten usando el tipo de cambio activo.

\---

### `TIPO\_CAMBIO\_MONEDA`

Registra el tipo de cambio vigente e histórico de cada moneda respecto al boliviano.

**Campos principales:** `TCM\_ID`, `MON\_ID`, `USU\_ID`, `TCM\_VALOR\_BOB`, `TCM\_FEC\_REG`, `TCM\_OBS`, `TCM\_ACTIVO`.

**Relaciones:**

- `TCM.MON\_ID` → `MONEDA.MON\_ID`;
- `TCM.USU\_ID` → `USUARIO.USU\_ID`.

**Restricciones relevantes:**

- `TCM\_VALOR\_BOB > 0`;
- `UQ\_TIPO\_CAMBIO\_ACTIVO\_MONEDA` evita más de un tipo de cambio activo por moneda.

**Lógica:**

Cuando se actualiza una moneda, el tipo de cambio anterior debe desactivarse y el nuevo registro debe quedar activo. Las operaciones ya registradas no deben recalcularse con el nuevo tipo de cambio.

\---

### `TIPO\_ITEM\_BOUTIQUE`

Catálogo de tipos de artículos de boutique: vestido, velo, bouquet, brassier, accesorio u otros.

**Campos principales:** `TIB\_ID`, `TIB\_NOM`, `TIB\_DES`, `TIB\_HAB`, `TIB\_FEC\_REG`.

**Restricciones relevantes:**

- `TIB\_NOM` es único;
- se usa como FK desde `ITEM\_BOUTIQUE`.

\---

### `ITEM\_BOUTIQUE`

Tabla base del inventario de boutique. Guarda los atributos comunes de cualquier artículo disponible para venta o flete.

**Campos principales:** `ITB\_ID`, `TIB\_ID`, `PRO\_ID`, `ITB\_COD`, `ITB\_NOM`, `ITB\_COLOR\_PRIM`, `ITB\_COLOR\_SECUN`, `ITB\_MATERIAL`, `ITB\_LARGO`, `ITB\_ANCHO`, `ITB\_PRECIO\_COMPRA`, `ITB\_PRECIO\_VENTA`, `ITB\_STOCK`, `ITB\_STOCK\_MIN`, `ITB\_DETALLE`, `ITB\_ESTADO`, `ITB\_FEC\_REG`.

**Relaciones:**

- `ITB.TIB\_ID` → `TIPO\_ITEM\_BOUTIQUE.TIB\_ID`;
- `ITB.PRO\_ID` → `PROVEEDOR.PRO\_ID`;
- se especializa mediante tablas detalle;
- se relaciona con `ENTRADA\_ITEM\_BOUTIQUE`, `VENTA\_BOUTIQUE` y `FLETE\_VESTIDO`.

**Restricciones relevantes:**

- `ITB\_COD` es único;
- precios y stock no pueden ser negativos;
- largo y ancho aceptan nulo o valores mayores/iguales a cero.

**Lógica:**

`ITB\_STOCK` representa el stock actual. No debe editarse manualmente desde la interfaz común. Debe modificarse por entradas, ventas, anulaciones controladas o ajustes operativos.

\---

### `DETALLE\_BRASSIER\_BOUTIQUE`

Registra información específica cuando el ítem de boutique es un brassier.

**Campos principales:** `DBB\_ID`, `ITB\_ID`, `DBB\_COPA\_TALL`, `DBB\_TIENE\_ENCAJE`, `DBB\_MARCA`, `DBB\_OBS`.

**Restricciones relevantes:**

- `ITB\_ID` es `UNIQUE`, porque un ítem brassier solo debe tener un detalle brassier;
- `DBB\_COPA\_TALL` es obligatorio.

\---

### `DETALLE\_VESTIDO\_BOUTIQUE`

Registra información específica de vestidos de boutique.

**Campos principales:** `DVB\_ID`, `ITB\_ID`, `DVB\_TIPO\_VESTIDO`, `DVB\_CORTE\_FALDA`, `DVB\_TIPO\_ESCOTE`, `DVB\_TIENE\_COLA`, `DVB\_TIENE\_MANGA`, `DVB\_TIENE\_PEDRERIA`, `DVB\_COPA\_TALLA`, `DVB\_TALLA`, `DVB\_LARGO\_FALDA`, `DVB\_OBS`.

**Restricciones relevantes:**

- `ITB\_ID` es `UNIQUE`;
- `DVB\_TIPO\_VESTIDO` y `DVB\_TALLA` son obligatorios;
- largo de falda no puede ser negativo.

\---

### `DETALLE\_VELO\_BOUTIQUE`

Registra información específica de velos de boutique.

**Campos principales:** `DVE\_ID`, `ITB\_ID`, `DVE\_TIPO\_VELO`, `DVE\_CAPAS`, `DVE\_BORDE`, `DVE\_DECORACION`, `DVE\_OBS`.

**Restricciones relevantes:**

- `ITB\_ID` es `UNIQUE`;
- `DVE\_CAPAS` debe ser nulo o mayor a cero.

\---

### `DETALLE\_BOUQUET\_BOUTIQUE`

Registra información específica de bouquets de boutique.

**Campos principales:** `DBO\_ID`, `ITB\_ID`, `DBO\_TIPO\_BOUQUET`, `DBO\_FORMA`, `DBO\_TIPO\_FLOR`, `DBO\_DECORACION`, `DBO\_OBS`.

**Restricciones relevantes:**

- `ITB\_ID` es `UNIQUE`;
- permite describir forma, flor y decoración del bouquet.

\---

### `ENTRADA\_ITEM\_BOUTIQUE`

Registra entradas de stock al inventario de boutique. Evita modificar el stock directamente sin historial.

**Campos principales:** `EIB\_ID`, `ITB\_ID`, `USU\_ID`, `PRO\_ID`, `EIB\_FEC`, `EIB\_CANT`, `EIB\_COSTO\_UNITARIO`, `EIB\_MOTIVO`, `EIB\_DOC\_REF`, `EIB\_OBS`, `EIB\_ESTADO`.

**Relaciones:**

- `EIB.ITB\_ID` → `ITEM\_BOUTIQUE.ITB\_ID`;
- `EIB.USU\_ID` → `USUARIO.USU\_ID`;
- `EIB.PRO\_ID` → `PROVEEDOR.PRO\_ID`.

**Restricciones relevantes:**

- `EIB\_CANT > 0`;
- `EIB\_COSTO\_UNITARIO >= 0`;
- el motivo se controla por `MOTIVO\_ENTRADA\_ITEM`.

**Lógica:**

Una entrada puede originarse por `ENTRADA\_STOCK`, `PRODUCCION\_INTERNA`, `DEVOLUCION`, `AJUSTE\_POSITIVO`, `REGISTRO\_INICIAL` u `OTRO`. Al registrar una entrada válida, el backend debe incrementar `ITEM\_BOUTIQUE.ITB\_STOCK` dentro de una transacción.

\---

### `VENTA\_BOUTIQUE`

Registra ventas directas de artículos de boutique.

**Campos principales:** `VEB\_ID`, `ITB\_ID`, `USU\_ID`, `CLI\_ID`, `MON\_ID`, `VEB\_FEC`, `VEB\_CANT`, `VEB\_PRE\_UNI`, `VEB\_DESCUENTO`, `VEB\_MOTIVO\_DESC`, `VEB\_TOT`, `VEB\_TIPO\_CAMBIO\_USADO`, `VEB\_TOTAL\_MONEDA\_ORIG`, `VEB\_METODO\_PAGO`, `VEB\_OBS`, `VEB\_ESTADO`, `VEB\_FEC\_CAMB\_EST`, `VEB\_MOTIVO\_CAMB\_EST`.

**Relaciones:**

- `VEB.ITB\_ID` → `ITEM\_BOUTIQUE.ITB\_ID`;
- `VEB.USU\_ID` → `USUARIO.USU\_ID`;
- `VEB.CLI\_ID` → `CLIENTE.CLI\_ID`;
- `VEB.MON\_ID` → `MONEDA.MON\_ID`.

**Restricciones relevantes:**

- cantidad y precio unitario deben ser mayores a cero;
- el descuento no puede superar el subtotal;
- si hay descuento, el motivo es obligatorio;
- `VEB\_TOT` se calcula automáticamente;
- `VEB\_TOTAL\_MONEDA\_ORIG > 0`;
- si la venta está `CANCELADA` o `ANULADA`, debe existir fecha y motivo de cambio de estado.

**Lógica:**

La venta conserva el total base en Bs mediante `VEB\_TOT` y el total cobrado en moneda de origen mediante `VEB\_TOTAL\_MONEDA\_ORIG`. Al registrar una venta activa, el backend debe descontar stock y generar comprobante interno.

\---

### `FLETE\_VESTIDO`

Configura un artículo de boutique como vestido habilitado para flete.

**Campos principales:** `FLE\_ID`, `ITB\_ID`, `USU\_ID`, `FLE\_PRECIO\_FLETE\_REF`, `FLE\_MAX\_SALIDAS`, `FLE\_SALIDAS\_ACTUALES`, `FLE\_ESTADO`, `FLE\_FEC\_HAB\_FLETE`, `FLE\_OBS`, `FLE\_HAB`.

**Relaciones:**

- `FLE.ITB\_ID` → `ITEM\_BOUTIQUE.ITB\_ID`;
- `FLE.USU\_ID` → `USUARIO.USU\_ID`.

**Restricciones relevantes:**

- `ITB\_ID` es único, por tanto un ítem solo puede tener una configuración de flete;
- `FLE\_MAX\_SALIDAS` debe estar entre 1 y 4;
- `FLE\_SALIDAS\_ACTUALES` no puede superar `FLE\_MAX\_SALIDAS`;
- precio referencial de flete debe ser mayor a cero.

**Lógica:**

El backend debe validar que el ítem corresponda a un vestido apto para flete, usualmente de 15 años. Cuando alcance el máximo de salidas, debe pasar a estado `AGOTADO` o `PASADO\_PARA\_VENTA` según la política del negocio.

\---

### `SALIDA\_FLETE`

Registra cada salida individual de un vestido fletable.

**Campos principales:** `SFL\_ID`, `FLE\_ID`, `CLI\_ID`, `USU\_ID`, `MON\_ID`, `SFL\_NUM`, `SFL\_FEC\_REG`, `SFL\_FEC\_SALIDA`, `SFL\_FEC\_DEVOLUCION\_PREVISTA`, `SFL\_FEC\_DEVOLUCION\_REAL`, `SFL\_PRECIO`, `SFL\_DESCUENTO`, `SFL\_MOTIVO\_DESC`, `SFL\_METODO\_PAGO`, `SFL\_TIPO\_CAMBIO\_USADO`, `SFL\_TOTAL\_FLETE`, `SFL\_TOTAL\_FLETE\_MONEDA\_ORIG`, `SFL\_GARANTIA`, `SFL\_GARANTIA\_DEVUELTA`, `SFL\_ESTADO\_SALIDA`, `SFL\_FEC\_CAMB\_EST`, `SFL\_MOTIVO\_CAMB\_EST`, `SFL\_ESTADO\_ENTREGA`, `SFL\_ESTADO\_DEVOLUCION`, `SFL\_REQUIERE\_ARREGLO`, `SFL\_MONTO\_ARREGLO`, `SFL\_DESCRIPCION\_ARREGLO`, `SFL\_OBS\_ENTREGA`, `SFL\_OBS\_DEVOLUCION`, `SFL\_HAB`.

**Relaciones:**

- `SFL.FLE\_ID` → `FLETE\_VESTIDO.FLE\_ID`;
- `SFL.CLI\_ID` → `CLIENTE.CLI\_ID`;
- `SFL.USU\_ID` → `USUARIO.USU\_ID`;
- `SFL.MON\_ID` → `MONEDA.MON\_ID`.

**Restricciones relevantes:**

- precio del flete mayor a cero;
- descuento no puede superar el precio;
- si hay descuento, el motivo es obligatorio;
- `SFL\_TOTAL\_FLETE` se calcula automáticamente;
- la garantía y garantía devuelta no pueden ser negativas;
- la garantía devuelta no puede superar la garantía recibida;
- la fecha prevista y real de devolución no pueden ser anteriores a la fecha de salida;
- `SFL\_NUM` debe estar entre 1 y 4;
- `UNIQUE(FLE\_ID, SFL\_NUM)` evita repetir el número de salida para el mismo vestido;
- si la salida está anulada, debe existir fecha y motivo de cambio de estado.

**Lógica:**

`SFL\_TOTAL\_FLETE` representa el monto del servicio en Bs. `SFL\_TOTAL\_FLETE\_MONEDA\_ORIG` conserva el valor cobrado en la moneda seleccionada por el cliente. La garantía se maneja por separado y no debe considerarse ingreso real mientras sea reembolsable.

\---

### `TIPO\_INVENTARIO\_TALLER`

Catálogo de tipos de materiales o insumos de taller.

**Campos principales:** `TIT\_ID`, `TIT\_NOM`, `TIT\_DES`, `TIT\_HAB`, `TIT\_FEC\_REG`.

**Restricciones relevantes:**

- `TIT\_NOM` es único;
- se relaciona con `INVENTARIO\_TALLER`.

\---

### `INVENTARIO\_TALLER`

Tabla base del inventario de materiales e insumos del taller.

**Campos principales:** `INT\_ID`, `TIT\_ID`, `PRO\_ID`, `INT\_COD`, `INT\_NOM`, `INT\_COLOR`, `INT\_LARGO`, `INT\_ANCHO`, `INT\_MATERIAL`, `INT\_DES`, `INT\_COSTO\_REF`, `INT\_STOCK`, `INT\_UNI\_MED`, `INT\_STOCK\_MIN`, `INT\_ESTADO`, `INT\_OBS`, `INT\_FEC\_REG`.

**Relaciones:**

- `INT.TIT\_ID` → `TIPO\_INVENTARIO\_TALLER.TIT\_ID`;
- `INT.PRO\_ID` → `PROVEEDOR.PRO\_ID`.

**Restricciones relevantes:**

- `INT\_COD` es único;
- costo, stock y stock mínimo no pueden ser negativos;
- largo y ancho aceptan nulo o valores no negativos;
- unidad de medida es obligatoria.

**Lógica:**

`INT\_STOCK` representa el stock actual del material. Debe modificarse por entradas y salidas registradas, no por edición manual directa.

\---

### `ENTRADA\_INVENTARIO\_TALLER`

Registra ingresos de stock al inventario del taller.

**Campos principales:** `EMT\_ID`, `INT\_ID`, `USU\_ID`, `PRO\_ID`, `EMT\_FEC`, `EMT\_CAN`, `EMT\_UNI\_MED`, `EMT\_COSTO\_UNITARIO`, `EMT\_MOTIVO`, `EMT\_DOC\_REF`, `EMT\_OBS`, `EMT\_ESTADO`.

**Relaciones:**

- `EMT.INT\_ID` → `INVENTARIO\_TALLER.INT\_ID`;
- `EMT.USU\_ID` → `USUARIO.USU\_ID`;
- `EMT.PRO\_ID` → `PROVEEDOR.PRO\_ID`.

**Restricciones relevantes:**

- `EMT\_CAN > 0`;
- `EMT\_COSTO\_UNITARIO >= 0`;
- el motivo se controla por `MOTIVO\_ENTRADA\_TALLER`.

**Lógica:**

Al registrar una entrada, el backend debe aumentar `INVENTARIO\_TALLER.INT\_STOCK` dentro de una transacción.

\---

### `SALIDA\_MATERIAL\_TALLER`

Registra salidas de materiales o insumos del taller hacia costura, decoración, pedidos, áreas internas u otros destinos.

**Campos principales:** `SMT\_ID`, `INT\_ID`, `USU\_ID`, `SMT\_FEC`, `SMT\_CAN`, `SMT\_UNI\_MED`, `SMT\_DESTINO`, `SMT\_OBS1`, `SMT\_OBS2`, `SMT\_ESTADO`.

**Relaciones:**

- `SMT.INT\_ID` → `INVENTARIO\_TALLER.INT\_ID`;
- `SMT.USU\_ID` → `USUARIO.USU\_ID`.

**Restricciones relevantes:**

- `SMT\_CAN > 0`;
- debe existir material relacionado.

**Lógica:**

El backend debe validar stock suficiente antes de registrar una salida y descontar `INT\_STOCK` en la misma transacción.

\---

### `PEDIDO`

Tabla principal de pedidos de confección o componentes asociados.

**Campos principales:** `PED\_ID`, `CLI\_ID`, `PED\_COD`, `PED\_TIPO`, `PED\_FEC\_REG\_CONTRATO`, `PED\_USU\_ENCARGADO`, `PED\_FEC\_DE\_ENTREGA`, `PED\_FEC\_ENTREGA\_FINAL`, `PED\_VIAJE`, `PED\_PAIS\_DESTINO`, `PED\_CIUDAD\_DESTINO`, `PED\_PRECIO`, `PED\_DESCUENTO`, `PED\_MOTIVO\_DESCUENTO`, `PED\_PRE\_TOT`, `PED\_TOTAL\_PAGADO`, `PED\_SALDO`, `PED\_OBS`, `PED\_ESTADO\_GENERAL`, `PED\_FEC\_CAMB\_EST`, `PED\_MOTIVO\_CAMB\_EST`, `PED\_HAB`.

**Relaciones:**

- `PED.CLI\_ID` → `CLIENTE.CLI\_ID`;
- `PED.PED\_USU\_ENCARGADO` → `USUARIO.USU\_ID`;
- se relaciona con tablas detalle de pedido, pruebas y pagos.

**Restricciones relevantes:**

- código de pedido único;
- precio, total pagado y saldo no pueden ser negativos;
- descuento no puede superar el precio;
- si hay descuento, el motivo es obligatorio;
- `PED\_PRE\_TOT` se calcula automáticamente;
- si el pedido está cancelado, debe existir fecha y motivo de cambio de estado.

**Lógica:**

`PED\_TOTAL\_PAGADO` y `PED\_SALDO` deben actualizarse mediante backend a partir de pagos válidos en `PAGO\_PEDIDO`. No deben ser editados manualmente desde la interfaz.

\---

### `PEDIDO\_VESTIDO`

Registra detalles específicos cuando el pedido corresponde o incluye un vestido.

**Campos principales:** `PDV\_ID`, `PED\_ID`, `PDV\_TIPO\_VESTIDO`, `PDV\_COLOR\_PRIN`, `PDV\_COLOR\_SECU`, `PDV\_DESCR\_MATERIAL`, `PDV\_DESCR\_DISENO`, `PDV\_DESCRIPCION\_2`, medidas corporales y `PDV\_OBS`.

**Restricciones relevantes:**

- `PED\_ID` es único;
- las medidas aceptan nulo o valores no negativos.

\---

### `PEDIDO\_VELO`

Registra detalles específicos de velo asociado a un pedido.

**Campos principales:** `PDVE\_ID`, `PED\_ID`, `PDVE\_TIPO\_VELO`, `PDVE\_COLOR\_PRIN`, `PDVE\_COLOR\_SECU`, `PDVE\_LARGO`, `PDVE\_ANCHO`, `PDVE\_CAPAS`, `PDVE\_BORDE`, `PDVE\_DECORACION`, `PDVE\_MATERIAL`, `PDVE\_OBS`.

**Restricciones relevantes:**

- `PED\_ID` es único;
- largo debe ser mayor a cero;
- ancho acepta nulo o valor no negativo;
- capas acepta nulo o valor mayor a cero.

\---

### `PEDIDO\_COLA`

Registra detalles específicos de cola asociada a un pedido.

**Campos principales:** `PDCO\_ID`, `PED\_ID`, `PDCO\_TIPO\_COLA`, `PDCO\_COLOR\_PRIN`, `PDCO\_COLOR\_SECUN`, `PDCO\_LARGO`, `PDCO\_ANCHO`, `PDCO\_MATERIAL`, `PDCO\_DECORACION`, `PDCO\_OBS`.

**Restricciones relevantes:**

- `PED\_ID` es único;
- largo debe ser mayor a cero;
- ancho acepta nulo o valor no negativo.

\---

### `PEDIDO\_MANGA`

Registra detalles específicos de mangas asociadas a un pedido.

**Campos principales:** `PDMA\_ID`, `PED\_ID`, `PDMA\_TIPO\_MANGA`, `PDMA\_COLOR\_PRIN`, `PDMA\_COLOR\_SECUN`, `PDMA\_LAR\_MAN`, `PDMA\_BRA`, `PDMA\_PUN`, `PDMA\_MATERIAL`, `PDMA\_DECORACION`, `PDMA\_OBS`.

**Restricciones relevantes:**

- `PED\_ID` es único;
- largo de manga debe ser mayor a cero;
- brazo y puño no deben ser negativos.

\---

### `PEDIDO\_BOUQUET`

Registra detalles específicos de bouquet asociado a un pedido.

**Campos principales:** `PDB\_ID`, `PED\_ID`, `PDB\_TIPO\_BOUQUET`, `PDB\_COLOR\_PRIN`, `PDB\_COLOR\_SECUN`, `PDB\_LARGO`, `PDB\_ANCHO`, `PDB\_TIPO\_FLOR`, `PDB\_DECORACION`, `PDB\_OBS`.

**Restricciones relevantes:**

- `PED\_ID` es único;
- largo no debe ser negativo;
- ancho acepta nulo o valor no negativo.

\---

### `PRUEBA\_PEDIDO`

Registra las pruebas programadas o realizadas sobre un pedido.

**Campos principales:** `PRP\_ID`, `PED\_ID`, `PRP\_NUM`, `PRP\_FEC`, `PRP\_HOR`, `PRP\_ESTADO`, `PRP\_OBS`.

**Restricciones relevantes:**

- `PRP\_NUM > 0`;
- `UNIQUE(PED\_ID, PRP\_NUM)` evita repetir el mismo número de prueba para un pedido.

**Lógica:**

Permite una cantidad flexible de pruebas. El backend debe validar secuencia lógica y coherencia de fechas.

\---

### `PAGO\_PEDIDO`

Registra pagos parciales o totales sobre pedidos.

**Campos principales:** `PPD\_ID`, `PED\_ID`, `USU\_ID`, `MON\_ID`, `PPD\_FEC`, `PPD\_MONTO`, `PPD\_TIPO\_CAMBIO\_USADO`, `PPD\_MONTO\_BOB`, `PPD\_METODO`, `PPD\_OBS1`, `PPD\_ESTADO`, `PPD\_FEC\_CAMB\_EST`, `PPD\_MOTIVO\_CAMB\_EST`.

**Relaciones:**

- `PPD.PED\_ID` → `PEDIDO.PED\_ID`;
- `PPD.USU\_ID` → `USUARIO.USU\_ID`;
- `PPD.MON\_ID` → `MONEDA.MON\_ID`.

**Restricciones relevantes:**

- `PPD\_MONTO > 0`;
- `PPD\_TIPO\_CAMBIO\_USADO > 0`;
- `PPD\_MONTO\_BOB` se calcula automáticamente;
- si el pago está anulado, debe existir fecha y motivo de cambio.

**Lógica:**

Los pagos anulados no deben sumar al total pagado. Cuando se corrige un pago registrado por error, no se debe editar el monto: debe anularse el pago y registrar uno nuevo.

\---

### `TIPO\_COMPROBANTE`

Catálogo de tipos de comprobantes internos.

**Campos principales:** `TCO\_ID`, `TCO\_NOM`, `TCO\_DES`, `TCO\_ES\_FISCAL`, `TCO\_HAB`, `TCO\_FEC\_REG`.

**Restricciones relevantes:**

- `TCO\_NOM` es único;
- `TCO\_ES\_FISCAL` permite diferenciar si el tipo se considera fiscal o no, aunque en la versión actual los comprobantes se manejan como internos no fiscales.

\---

### `COMPROBANTE\_INTERNO`

Encabezado documental de comprobantes internos generados por ventas, pagos de pedido o fletes.

**Campos principales:** `COI\_ID`, `TCO\_ID`, `CLI\_ID`, `USU\_ID`, `VEB\_ID`, `PPD\_ID`, `SFL\_ID`, `MON\_ID`, `COI\_COD`, `COI\_FEC`, datos snapshot del cliente, `COI\_SUBTOTAL`, `COI\_DESCUENTO`, `COI\_TOTAL`, `COI\_TOTAL\_MONEDA\_ORIG`, `COI\_SALDO\_POSTERIOR`, `COI\_GARANTIA`, `COI\_TIPO\_CAMBIO\_USADO`, `COI\_METODO\_PAGO`, `COI\_ESTADO`, `COI\_FEC\_CAMB\_EST`, `COI\_MOTIVO\_CAMB\_EST`, `COI\_HAB`.

**Relaciones:**

- `COI.TCO\_ID` → `TIPO\_COMPROBANTE.TCO\_ID`;
- `COI.CLI\_ID` → `CLIENTE.CLI\_ID`;
- `COI.USU\_ID` → `USUARIO.USU\_ID`;
- `COI.MON\_ID` → `MONEDA.MON\_ID`;
- puede originarse en una sola de estas tablas: `VENTA\_BOUTIQUE`, `PAGO\_PEDIDO` o `SALIDA\_FLETE`.

**Restricciones relevantes:**

- `COI\_COD` es único;
- `CK\_COMPROBANTE\_UN\_ORIGEN` obliga a que el comprobante tenga un solo origen operativo;
- el descuento no puede superar el subtotal;
- el total debe ser subtotal menos descuento;
- los montos no pueden ser negativos;
- si el comprobante está anulado, debe existir fecha y motivo.

**Lógica:**

El comprobante debe generarse automáticamente desde backend. Conserva una copia histórica de los datos entregados al cliente. No debe ser el origen de ingresos, sino la constancia documental de una operación real.

\---

### `DETALLE\_COMPROBANTE`

Registra las líneas o conceptos de un comprobante interno.

**Campos principales:** `DCO\_ID`, `COI\_ID`, `DCO\_CONCEPTO`, `DCO\_CANTIDAD`, `DCO\_PRECIO\_UNIDAD`, `DCO\_DESCUENTO`, `DCO\_SUBTOTAL`, `DCO\_OBS`.

**Restricciones relevantes:**

- cantidad debe ser mayor a cero;
- precio y descuento no pueden ser negativos;
- descuento no puede superar cantidad × precio unitario;
- subtotal debe ser igual a cantidad × precio unitario − descuento.

\---

### `EGRESO`

Registra salidas de dinero de la empresa.

**Campos principales:** `EGR\_ID`, `USU\_ID`, `EGR\_FEC`, `EGR\_TIPO`, `EGR\_CONCEPTO`, `EGR\_CANTIDAD`, `EGR\_PRECIO\_UNIDAD`, `EGR\_BENEFICIARIO`, `EGR\_MONTO`, `EGR\_OBS1`, `EGR\_OBS2`, `EGR\_ESTADO`, `EGR\_FEC\_CAMB\_EST`, `EGR\_MOTIVO\_CAMB\_EST`.

**Restricciones relevantes:**

- cantidad y precio unitario deben ser mayores a cero;
- `EGR\_MONTO` se calcula automáticamente;
- si el egreso está anulado, debe existir fecha y motivo.

**Lógica:**

Los egresos anulados deben conservarse como historial, pero no deben sumar en reportes de egreso real.

\---

### `AUDITORIA\_SISTEMA`

Registra eventos importantes del sistema.

**Campos principales:** `AUD\_ID`, `USU\_ID`, `AUD\_FEC`, `AUD\_TABLA`, `AUD\_ID\_REGISTRO`, `AUD\_ACCION`, `AUD\_CAMPO`, `AUD\_VALOR\_ANTERIOR`, `AUD\_VALOR\_NUEVO`, `AUD\_DESCRIPCION`, `AUD\_IP`, `AUD\_DISPOSITIVO`.

**Lógica:**

Debe registrar inserciones, actualizaciones, eliminaciones lógicas, cambios de estado, anulaciones, cancelaciones, login y logout.

\---

### `NOTIFICACION`

Registra notificaciones internas dirigidas a usuarios del sistema.

**Campos principales:** `NOT\_ID`, `USU\_ID`, `NOT\_TIPO`, `NOT\_PRIORIDAD`, `NOT\_TITULO`, `NOT\_MENSAJE`, `NOT\_MODULO`, `NOT\_LEIDA`, `NOT\_FEC`, `NOT\_FEC\_LEIDA`.

**Relaciones:**

- `NOT.USU\_ID` → `USUARIO.USU\_ID`.

**Lógica:**

Sirve para alertar sobre stock agotado, pruebas programadas, entregas próximas, devoluciones de flete, saldos pendientes, pedidos atrasados u otros eventos operativos.

\---

## 6\. Relaciones clave del modelo

- `ROL` 1 : N `CUENTA`.
- `USUARIO` 1 : N `CUENTA`.
- `USUARIO` 1 : N operaciones registradas: ventas, pagos, fletes, entradas, egresos, auditorías y notificaciones.
- `CLIENTE` 1 : N `PEDIDO`.
- `CLIENTE` 1 : N `VENTA\_BOUTIQUE`.
- `CLIENTE` 1 : N `SALIDA\_FLETE`.
- `CLIENTE` 1 : N `COMPROBANTE\_INTERNO`.
- `PROVEEDOR` 1 : N `ITEM\_BOUTIQUE`.
- `PROVEEDOR` 1 : N `INVENTARIO\_TALLER`.
- `MONEDA` 1 : N `TIPO\_CAMBIO\_MONEDA`.
- `MONEDA` 1 : N `VENTA\_BOUTIQUE`, `PAGO\_PEDIDO`, `SALIDA\_FLETE`, `COMPROBANTE\_INTERNO`.
- `TIPO\_ITEM\_BOUTIQUE` 1 : N `ITEM\_BOUTIQUE`.
- `ITEM\_BOUTIQUE` 1 : 0..1 `DETALLE\_BRASSIER\_BOUTIQUE`.
- `ITEM\_BOUTIQUE` 1 : 0..1 `DETALLE\_VESTIDO\_BOUTIQUE`.
- `ITEM\_BOUTIQUE` 1 : 0..1 `DETALLE\_VELO\_BOUTIQUE`.
- `ITEM\_BOUTIQUE` 1 : 0..1 `DETALLE\_BOUQUET\_BOUTIQUE`.
- `ITEM\_BOUTIQUE` 1 : N `ENTRADA\_ITEM\_BOUTIQUE`.
- `ITEM\_BOUTIQUE` 1 : N `VENTA\_BOUTIQUE`.
- `ITEM\_BOUTIQUE` 1 : 0..1 `FLETE\_VESTIDO`.
- `FLETE\_VESTIDO` 1 : N `SALIDA\_FLETE`.
- `TIPO\_INVENTARIO\_TALLER` 1 : N `INVENTARIO\_TALLER`.
- `INVENTARIO\_TALLER` 1 : N `ENTRADA\_INVENTARIO\_TALLER`.
- `INVENTARIO\_TALLER` 1 : N `SALIDA\_MATERIAL\_TALLER`.
- `PEDIDO` 1 : 0..1 `PEDIDO\_VESTIDO`.
- `PEDIDO` 1 : 0..1 `PEDIDO\_VELO`.
- `PEDIDO` 1 : 0..1 `PEDIDO\_COLA`.
- `PEDIDO` 1 : 0..1 `PEDIDO\_MANGA`.
- `PEDIDO` 1 : 0..1 `PEDIDO\_BOUQUET`.
- `PEDIDO` 1 : N `PRUEBA\_PEDIDO`.
- `PEDIDO` 1 : N `PAGO\_PEDIDO`.
- `TIPO\_COMPROBANTE` 1 : N `COMPROBANTE\_INTERNO`.
- `COMPROBANTE\_INTERNO` 1 : N `DETALLE\_COMPROBANTE`.
- `VENTA\_BOUTIQUE`, `PAGO\_PEDIDO` y `SALIDA\_FLETE` pueden originar `COMPROBANTE\_INTERNO`, pero cada comprobante tiene un solo origen.

\---

## 7\. Reglas de control que debe aplicar el backend

### 7.1 Seguridad

- Las contraseñas de `CUENTA` deben guardarse en hash.
- No permitir login con cuenta, usuario o rol deshabilitado.
- Auditar login, logout y cambios de cuenta o rol.

### 7.2 Multimoneda

- Si la moneda seleccionada es la moneda base, el tipo de cambio usado debe ser 1.
- Si la moneda no es base, debe existir un tipo de cambio activo.
- No permitir operar con monedas deshabilitadas.
- Congelar el tipo de cambio usado en cada venta, flete, pago o comprobante.
- No recalcular operaciones históricas cuando cambie el tipo de cambio.

### 7.3 Inventario boutique

- Registrar producto con stock inicial 0 y crear una entrada con motivo `REGISTRO\_INICIAL` si corresponde.
- Toda entrada válida debe aumentar stock.
- Toda venta activa debe disminuir stock.
- No vender artículos deshabilitados o sin stock suficiente.
- Si la venta se anula, el backend debe definir si corresponde reversar stock.

### 7.4 Fletes

- Solo habilitar para flete artículos que sean vestidos y cumplan la regla comercial definida.
- No permitir más de una salida activa por vestido.
- No superar `FLE\_MAX\_SALIDAS`.
- Actualizar `FLE\_ESTADO` y `FLE\_SALIDAS\_ACTUALES` al registrar devoluciones válidas.
- No considerar la garantía como ingreso definitivo mientras sea reembolsable.
- Registrar observación y monto cuando exista arreglo.

### 7.5 Inventario taller

- Toda entrada válida debe aumentar `INT\_STOCK`.
- Toda salida válida debe disminuir `INT\_STOCK`.
- No permitir salidas sin stock suficiente.
- Validar coherencia de unidad de medida.

### 7.6 Pedidos

- El cliente y el usuario encargado deben existir.
- El descuento requiere motivo.
- `PED\_TOTAL\_PAGADO` y `PED\_SALDO` deben recalcularse desde pagos registrados y no anulados.
- No permitir pagos sobre pedidos cancelados.
- Controlar que las pruebas tengan secuencia lógica.
- Si el pedido se cancela, conservar fecha y motivo.

### 7.7 Pagos

- No editar montos de pagos registrados.
- Si un pago fue registrado con error, debe anularse y crearse un nuevo pago correcto.
- Los pagos anulados no deben afectar saldo ni total pagado.
- Cada pago registrado debe generar comprobante interno.

### 7.8 Comprobantes internos

- Deben generarse desde backend, no llenarse manualmente.
- Deben conservar snapshot del cliente, moneda, tipo de cambio, montos y saldo posterior.
- Deben tener un solo origen: venta, pago de pedido o salida de flete.
- Si se anulan, conservar fecha y motivo.
- Mostrar leyenda: “Documento de control interno. No constituye factura, nota fiscal ni documento equivalente. No válido para crédito fiscal ni descargo tributario.”

### 7.9 Egresos

- No editar montos calculados manualmente.
- Anular egresos con fecha y motivo, no eliminarlos físicamente.
- Los egresos anulados no deben sumar en reportes financieros.

### 7.10 Auditoría y notificaciones

- Auditar operaciones críticas: registros, actualizaciones, anulaciones, cancelaciones y cambios de estado.
- Generar notificaciones para stock agotado, entregas, pruebas, saldos pendientes, fletes próximos a devolución y pedidos atrasados.

\---

## 8\. Reportes recomendados

La base permite construir reportes sobre:

- ventas de boutique por fecha, método de pago, producto, cliente y estado;
- ingresos reales desde ventas, pagos y fletes;
- movimientos económicos incluyendo anulados y cancelados;
- saldos pendientes de pedidos;
- calendario de pruebas por día, semana y mes;
- pedidos por tipo y por tipo de vestido;
- pedidos de viaje por destino;
- fletes activos, devueltos, anulados y agotados;
- inventario boutique general y stock bajo;
- inventario taller general, entradas, salidas y stock bajo;
- egresos por tipo, fecha y usuario;
- comprobantes emitidos y anulados;
- auditoría de cambios de estado y operaciones sensibles.

\---

## 9\. Índices recomendados

La base ya genera índices automáticos en claves primarias y columnas únicas. Además, se recomienda crear índices sobre claves foráneas y columnas de consulta frecuente:

- `VENTA\_BOUTIQUE(VEB\_ESTADO, VEB\_FEC)`;
- `VENTA\_BOUTIQUE(MON\_ID, VEB\_FEC)`;
- `PAGO\_PEDIDO(PED\_ID, PPD\_FEC)`;
- `PAGO\_PEDIDO(PPD\_ESTADO, PPD\_FEC)`;
- `SALIDA\_FLETE(FLE\_ID, SFL\_NUM)`;
- `SALIDA\_FLETE(SFL\_ESTADO\_SALIDA, SFL\_FEC\_DEVOLUCION\_PREVISTA)`;
- `PEDIDO(PED\_ESTADO\_GENERAL, PED\_FEC\_DE\_ENTREGA)`;
- `PRUEBA\_PEDIDO(PRP\_FEC, PRP\_HOR)`;
- `ITEM\_BOUTIQUE(TIB\_ID)`;
- `ITEM\_BOUTIQUE(PRO\_ID)`;
- `INVENTARIO\_TALLER(TIT\_ID)`;
- `INVENTARIO\_TALLER(PRO\_ID)`;
- `COMPROBANTE\_INTERNO(COI\_ESTADO, COI\_FEC)`;
- `EGRESO(EGR\_ESTADO, EGR\_FEC)`;
- `AUDITORIA\_SISTEMA(AUD\_TABLA, AUD\_ID\_REGISTRO)`;
- `NOTIFICACION(USU\_ID, NOT\_LEIDA)`.

\---

## 10\. Recomendaciones operativas

- Usar transacciones en operaciones compuestas.
- No editar stock directamente desde formularios generales.
- No editar pagos registrados; anular y registrar nuevamente si hubo error.
- No eliminar físicamente ventas, pagos, comprobantes o egresos anulados.
- Generar comprobantes desde backend a partir de operaciones reales.
- Recalcular saldos de pedido desde pagos válidos.
- Congelar tipo de cambio en cada operación monetaria.
- Mantener reportes económicos en Bs como moneda base.
- Usar auditoría para registrar quién realizó cambios sensibles.
- Validar en backend aunque existan restricciones `CHECK` en la BD.

\---

## 11\. Conclusión

La Base de Datos V4 de BELLAARTE BOUTIQUE representa una estructura más completa, segura y alineada con el funcionamiento real del negocio. La versión integra inventario boutique, inventario taller, proveedores, multimoneda, tipos de cambio, ventas, fletes, pedidos, pruebas, pagos, comprobantes internos, egresos, auditoría y notificaciones.

Su diseño separa correctamente las tablas maestras, las operaciones, los detalles especializados y los documentos internos. Además, incorpora validaciones, relaciones, columnas generadas y trazabilidad de estados para reducir inconsistencias y mejorar el control administrativo.

El sistema debe apoyarse en el backend para ejecutar transacciones completas, validar reglas de negocio, actualizar saldos, actualizar stock, emitir comprobantes y registrar auditoría. Con esta base, BELLAARTE BOUTIQUE puede avanzar hacia un sistema web empresarial más ordenado, escalable y preparado para reportes operativos y gerenciales.
