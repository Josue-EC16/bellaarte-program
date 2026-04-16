# README – BASE DE DATOS V.0.3  
## BELLAARTE BOUTIQUE  
**Motor de base de datos:** PostgreSQL 17

---

## 1. Descripción general

La base de datos v.0.3 fue diseñada para centralizar los procesos principales de **BELLAARTE BOUTIQUE** en una estructura más modular, ordenada y escalable.  
Esta versión organiza la información en módulos funcionales: seguridad del sistema, clientes, inventario de boutique, inventario de taller, pedidos especializados, pruebas, pagos, recibos, ingresos, egresos y auditoría.

A diferencia de versiones anteriores, esta estructura separa mejor la información general de la información específica.  
Por ejemplo, en boutique se usa una tabla base para artículos y tablas detalle para vestidos, velos y bouquets.  
En pedidos se aplica el mismo enfoque: existe una tabla base `PEDIDO` y tablas complementarias para vestido, velo, cola, manga y bouquet.  
Además, la parte documental se organiza con recibos y la parte financiera con ingresos y egresos.

---

## 2. Objetivo de la base de datos

El objetivo principal de esta base de datos es:

- centralizar la información operativa y administrativa
- reducir el uso disperso de archivos Excel y registros manuales
- mejorar el control de ventas, pedidos, pagos, inventario e insumos
- generar trazabilidad documental y financiera
- permitir crecimiento progresivo del sistema sin rediseñar toda la estructura

---

## 3. Estructura general por módulos

La base se divide en los siguientes bloques:

- **Seguridad:** `ROL`, `USUARIO`, `CUENTA`
- **Clientes:** `CLIENTE`
- **Boutique:** `TIPO_ITEM_BOUTIQUE`, `ITEM_BOUTIQUE`, `DETALLE_VESTIDO_BOUTIQUE`, `DETALLE_VELO_BOUTIQUE`, `DETALLE_BOUQUET_BOUTIQUE`, `VENTA_BOUTIQUE`
- **Taller:** `INVENTARIO_TALLER`, `SALIDA_MATERIAL_TALLER`
- **Pedidos:** `PEDIDO`, `PEDIDO_VESTIDO`, `PEDIDO_VELO`, `PEDIDO_COLA`, `PEDIDO_MANGA`, `PEDIDO_BOUQUET`, `PRUEBA_PEDIDO`, `PAGO_PEDIDO`
- **Documentos:** `TIPO_RECIBO`, `RECIBO`, `DETALLE_RECIBO`
- **Finanzas:** `INGRESO`, `EGRESO`
- **Auditoría:** `AUDITORIA_SISTEMA`

---

## 4. Para qué sirve cada tabla

### `ROL`
- Define los roles del sistema.
- Permite clasificar el nivel de acceso de cada cuenta.
- Sirve para la gestión de permisos generales.

### `USUARIO`
- Guarda los datos del personal que utiliza el sistema.
- Representa a la persona que registra operaciones.
- Sirve como referencia en ventas, pagos, salidas de material, ingresos, egresos y auditoría.

### `CUENTA`
- Almacena las credenciales de acceso al sistema.
- Relaciona un usuario con un rol.
- Permite controlar login, habilitación de cuenta y último acceso.

### `CLIENTE`
- Guarda la información personal y de contacto de los clientes.
- Sirve para asociar pedidos, ventas y recibos.
- Centraliza los datos comerciales del cliente.

### `TIPO_ITEM_BOUTIQUE`
- Define los tipos de artículos que maneja la boutique.
- Permite clasificar los artículos del inventario.
- Hace más flexible el mantenimiento de los ítems boutique.

### `ITEM_BOUTIQUE`
- Es la tabla base del inventario de boutique.
- Guarda la información general de cualquier artículo boutique.
- Registra código, nombre, color, forma, material, proveedor, precios y stock.

### `DETALLE_VESTIDO_BOUTIQUE`
- Guarda la información específica de los vestidos de boutique.
- Complementa a `ITEM_BOUTIQUE` cuando el artículo es un vestido.
- Permite registrar tipo de vestido, escote, corte de falda, talla, copa y largo.

### `DETALLE_VELO_BOUTIQUE`
- Guarda la información específica de los velos de boutique.
- Complementa a `ITEM_BOUTIQUE` cuando el artículo es un velo.
- Registra largo, tamaño, capas, borde y decoración.

### `DETALLE_BOUQUET_BOUTIQUE`
- Guarda la información específica de los bouquets de boutique.
- Complementa a `ITEM_BOUTIQUE` cuando el artículo es un bouquet.
- Registra tamaño, tipo de flor y decoración.

### `VENTA_BOUTIQUE`
- Registra las ventas directas de artículos boutique.
- Guarda cliente, usuario, artículo, cantidad, precio, descuento, total, método de pago y estado.
- Sirve como base comercial para generar ingresos y recibos.

### `INVENTARIO_TALLER`
- Registra los materiales e insumos del taller.
- Controla telas, guipures, hilos, cierres, pedrería y otros materiales.
- Sirve para monitorear stock, costo referencial y proveedor.

### `SALIDA_MATERIAL_TALLER`
- Registra las salidas de materiales del taller.
- Permite saber qué material salió, cuánto salió y a qué destino fue entregado.
- Ayuda a controlar consumo y distribución de insumos.

### `PEDIDO`
- Es la tabla base de los pedidos.
- Guarda la información general común a cualquier pedido.
- Registra cliente, código, tipo de pedido, fechas, descuento, precio total, total pagado, saldo y estado.

### `PEDIDO_VESTIDO`
- Guarda la información específica de pedidos de vestido.
- Complementa a `PEDIDO` cuando el pedido corresponde a un vestido.
- Registra color, materiales, diseño y medidas del cuerpo.

### `PEDIDO_VELO`
- Guarda la información específica de pedidos de velo.
- Complementa a `PEDIDO` cuando el pedido incluye o corresponde a un velo.
- Registra largo, capas, borde, material y decoración.

### `PEDIDO_COLA`
- Guarda la información específica de pedidos de cola.
- Complementa a `PEDIDO` cuando el pedido incluye una cola.
- Registra largo, material, color y decoración.

### `PEDIDO_MANGA`
- Guarda la información específica de pedidos de manga.
- Complementa a `PEDIDO` cuando el pedido incluye mangas.
- Registra medidas de manga, material y decoración.

### `PEDIDO_BOUQUET`
- Guarda la información específica de pedidos de bouquet.
- Complementa a `PEDIDO` cuando el pedido corresponde a bouquet.
- Registra tipo, color, tamaño, flores y decoración.

### `PRUEBA_PEDIDO`
- Registra las pruebas asociadas a un pedido.
- Permite guardar una cantidad flexible de pruebas.
- Almacena número, fecha, hora, estado y observaciones de cada prueba.

### `PAGO_PEDIDO`
- Registra cada pago realizado sobre un pedido.
- Guarda el historial real de cuotas o pagos del cliente.
- Sirve para recalcular total pagado y saldo pendiente.

### `TIPO_RECIBO`
- Define los tipos de recibo que puede generar el sistema.
- Permite clasificar comprobantes según su origen.
- Sirve como catálogo documental.

### `RECIBO`
- Guarda el encabezado de los recibos emitidos.
- Registra cliente, usuario, origen, código, fecha, nombre o razón social, CI/NIT, montos y saldo posterior.
- Sirve como comprobante histórico de la operación.

### `DETALLE_RECIBO`
- Guarda el detalle del contenido de cada recibo.
- Registra concepto, cantidad, precio unitario y subtotal.
- Sirve para mostrar las líneas internas del comprobante.

### `INGRESO`
- Registra entradas de dinero del sistema.
- Centraliza ingresos provenientes de ventas, pagos de pedido u otros conceptos.
- Sirve como apoyo para reportes financieros y control de caja.

### `EGRESO`
- Registra salidas de dinero del sistema.
- Controla gastos de operación, compras, servicios, pagos y otros egresos.
- Sirve para análisis de costos y flujo financiero.

### `AUDITORIA_SISTEMA`
- Registra eventos relevantes del sistema.
- Guarda quién hizo una acción, cuándo la hizo, sobre qué tabla y qué cambió.
- Sirve para trazabilidad, control interno y auditoría.

---

## 5. Significado de columnas por tabla

### `ROL`
- `ROL_ID`: identificador único del rol.
- `ROL_NOM`: nombre del rol.
- `ROL_DES`: descripción del rol.
- `ROL_HAB`: indica si el rol está habilitado.
- `ROL_FEC_REG`: fecha y hora de registro.

### `USUARIO`
- `USU_ID`: identificador único del usuario.
- `USU_NOM`: nombres del usuario.
- `USU_APE_PAT`: apellido paterno.
- `USU_APE_MAT`: apellido materno.
- `USU_CEL`: celular.
- `USU_CI`: carnet de identidad.
- `USU_COR`: correo.
- `USU_DIR`: dirección.
- `USU_HAB`: estado de habilitación.
- `USU_FEC_REG`: fecha de registro.

### `CUENTA`
- `CUE_ID`: identificador de la cuenta.
- `USU_ID`: usuario propietario de la cuenta.
- `ROL_ID`: rol asignado.
- `CUE_NOM_USU`: nombre de usuario para login.
- `CUE_CON`: contraseña almacenada.
- `CUE_HAB`: estado de habilitación de la cuenta.
- `CUE_FEC_CRE`: fecha de creación.
- `CUE_ULT_ACC`: último acceso registrado.

### `CLIENTE`
- `CLI_ID`: identificador del cliente.
- `CLI_COD`: código interno del cliente.
- `CLI_NOM`: nombres.
- `CLI_APE_PAT`: apellido paterno.
- `CLI_APE_MAT`: apellido materno.
- `CLI_CEL`: celular principal.
- `CLI_CEL_REF`: celular de referencia.
- `CLI_NOM_CEL_REF`: nombre de la referencia.
- `CLI_COR`: correo electrónico.
- `CLI_CI`: carnet de identidad.
- `CLI_NAC`: nacionalidad.
- `CLI_ZONA`: zona.
- `CLI_CALLE`: calle o dirección.
- `CLI_OBS`: observaciones.
- `CLI_HAB`: estado de habilitación.
- `CLI_FEC_REG`: fecha de registro.

### `TIPO_ITEM_BOUTIQUE`
- `TIB_ID`: identificador del tipo de artículo.
- `TIB_NOM`: nombre del tipo.
- `TIB_DES`: descripción del tipo.
- `TIB_HAB`: estado de habilitación.
- `TIB_FEC_REG`: fecha de registro.

### `ITEM_BOUTIQUE`
- `ITB_ID`: identificador del artículo.
- `TIB_ID`: tipo de artículo boutique.
- `ITB_COD`: código interno.
- `ITB_NOM`: nombre del artículo.
- `ITB_COLOR`: color principal.
- `ITB_FORMA`: forma o estilo.
- `ITB_MATERIAL`: material principal.
- `ITB_MEDIDAS`: medidas generales.
- `ITB_PROVEEDOR`: proveedor.
- `ITB_DES`: descripción.
- `ITB_PRECIO_COMPRA`: costo de compra.
- `ITB_PRECIO_VENTA`: precio de venta.
- `ITB_STOCK`: stock disponible.
- `ITB_STOCK_MIN`: stock mínimo recomendado.
- `ITB_ESTADO`: habilitación del artículo.
- `ITB_OBS`: observaciones.
- `ITB_FEC_REG`: fecha de registro.

### `DETALLE_VESTIDO_BOUTIQUE`
- `DVB_ID`: identificador del detalle.
- `ITB_ID`: artículo boutique asociado.
- `DVB_TIPO_VESTIDO`: tipo de vestido.
- `DVB_CORTE_FALDA`: corte de falda.
- `DVB_TIPO_ESCOTE`: tipo de escote.
- `DVB_TIENE_COLA`: indica si tiene cola.
- `DVB_TIENE_MANGA`: indica si tiene manga.
- `DVB_TIENE_PEDRERIA`: indica si tiene pedrería.
- `DVB_COPA_TALLA`: copa del vestido.
- `DVB_TALLA`: talla del vestido.
- `DVB_LARGO_FALDA`: largo de falda.
- `DVB_OBS`: observaciones.

### `DETALLE_VELO_BOUTIQUE`
- `DVE_ID`: identificador del detalle.
- `ITB_ID`: artículo boutique asociado.
- `DVE_TIPO_VELO`: tipo de velo.
- `DVE_LARGO`: largo del velo.
- `DVE_TAMANO`: tamaño.
- `DVE_CAPAS`: número de capas.
- `DVE_BORDE`: tipo de borde.
- `DVE_DECORACION`: decoración.
- `DVE_OBS`: observaciones.

### `DETALLE_BOUQUET_BOUTIQUE`
- `DBO_ID`: identificador del detalle.
- `ITB_ID`: artículo boutique asociado.
- `DBO_TIPO_BOUQUET`: tipo de bouquet.
- `DBO_TAMANO`: tamaño.
- `DBO_TIPO_FLOR`: tipo de flor.
- `DBO_DECORACION`: decoración.
- `DBO_OBS`: observaciones.

### `VENTA_BOUTIQUE`
- `VEB_ID`: identificador de la venta.
- `ITB_ID`: artículo vendido.
- `USU_ID`: usuario que registró la venta.
- `CLI_ID`: cliente asociado.
- `VEB_FEC`: fecha y hora de la venta.
- `VEB_CANT`: cantidad vendida.
- `VEB_PRE_UNI`: precio unitario.
- `VEB_DESCUENTO`: descuento aplicado.
- `VEB_MOTIVO_DESC`: motivo del descuento.
- `VEB_TOT`: total calculado de la venta.
- `VEB_METODO_PAGO`: método de pago.
- `VEB_OBS`: observaciones.
- `VEB_ESTADO`: estado de la venta.

### `INVENTARIO_TALLER`
- `INT_ID`: identificador del material.
- `INT_COD`: código interno.
- `INT_NOM`: nombre del material.
- `INT_TIPO`: tipo de material.
- `INT_DES1`: descripción principal.
- `INT_DES2`: descripción complementaria.
- `INT_COLOR`: color.
- `INT_TAMANO`: tamaño.
- `INT_MATERIAL`: material o composición.
- `INT_PROVEEDOR`: proveedor.
- `INT_COSTO_REF`: costo referencial.
- `INT_STOCK`: stock.
- `INT_UNI_MED`: unidad de medida.
- `INT_STOCK_MIN`: stock mínimo.
- `INT_ESTADO`: habilitación del material.
- `INT_OBS`: observaciones.
- `INT_FEC_REG`: fecha de registro.

### `SALIDA_MATERIAL_TALLER`
- `SMT_ID`: identificador de la salida.
- `INT_ID`: material que salió.
- `USU_ID`: usuario que registró la salida.
- `SMT_FEC`: fecha y hora de salida.
- `SMT_CAN`: cantidad entregada.
- `SMT_UNI_MED`: unidad de medida.
- `SMT_DESTINO`: destino o persona receptora.
- `SMT_OBS1`: observación principal.
- `SMT_OBS2`: observación secundaria.
- `SMT_ESTADO`: estado del registro.

### `PEDIDO`
- `PED_ID`: identificador del pedido.
- `CLI_ID`: cliente del pedido.
- `PED_COD`: código interno del pedido.
- `PED_TIPO`: tipo general del pedido.
- `PED_FEC_REG_CONTRATO`: fecha de contrato.
- `PED_ENCARGADO_CONTRATO`: persona que cerró el contrato.
- `PED_FEC_DE_ENTREGA`: fecha comprometida de entrega.
- `PED_FEC_ENTREGA_FINAL`: fecha real/final de entrega.
- `PED_VIAJE`: indica si el pedido tiene condición de viaje.
- `PED_DESTINO`: destino del pedido si aplica.
- `PED_DESCUENTO`: descuento del pedido.
- `PED_MOTIVO_DESCUENTO`: motivo del descuento.
- `PED_PRE_TOT`: precio total del pedido.
- `PED_TOTAL_PAGADO`: total pagado acumulado.
- `PED_SALDO`: saldo pendiente.
- `PED_OBS`: observaciones.
- `PED_ESTADO_GENERAL`: estado general del pedido.
- `PED_HAB`: habilitación lógica.

### `PEDIDO_VESTIDO`
- `PDV_ID`: identificador del detalle.
- `PED_ID`: pedido asociado.
- `PDV_TIPO_VESTIDO`: tipo de vestido pedido.
- `PDV_COLOR`: color principal.
- `PDV_DESCRIPCION_MATERIAL`: descripción de materiales.
- `PDV_DESCRIPCION_DISENO`: descripción de diseño.
- `PDV_DESCRIPCION_2`: descripción adicional.
- `PDV_ANE_ESP`, `PDV_TAL_ESP`, `PDV_TAL_DEL`, `PDV_CON_CIN`, `PDV_CON_CAD`, `PDV_LAR_FAL`, `PDV_SISA`, `PDV_ANB_BUS`, `PDV_SEP_BUS`, `PDV_TAL_BUS`, `PDV_TAL_COS`: medidas del cuerpo o vestido.
- `PDV_OBS`: observaciones.

### `PEDIDO_VELO`
- `PDVE_ID`: identificador del detalle.
- `PED_ID`: pedido asociado.
- `PDVE_TIPO_VELO`: tipo de velo.
- `PDVE_COLOR`: color.
- `PDVE_LARGO`: largo.
- `PDVE_CAPAS`: número de capas.
- `PDVE_BORDE`: borde.
- `PDVE_DECORACION`: decoración.
- `PDVE_MATERIAL`: material.
- `PDVE_OBS`: observaciones.

### `PEDIDO_COLA`
- `PDCO_ID`: identificador del detalle.
- `PED_ID`: pedido asociado.
- `PDCO_TIPO_COLA`: tipo de cola.
- `PDCO_COLOR`: color.
- `PDCO_LARGO`: largo.
- `PDCO_MATERIAL`: material.
- `PDCO_DECORACION`: decoración.
- `PDCO_OBS`: observaciones.

### `PEDIDO_MANGA`
- `PDMA_ID`: identificador del detalle.
- `PED_ID`: pedido asociado.
- `PDMA_TIPO_MANGA`: tipo de manga.
- `PDMA_LAR_MAN`: largo de manga.
- `PDMA_BRA`: medida de brazo.
- `PDMA_PUN`: medida de puño.
- `PDMA_MATERIAL`: material.
- `PDMA_DECORACION`: decoración.
- `PDMA_OBS`: observaciones.

### `PEDIDO_BOUQUET`
- `PDB_ID`: identificador del detalle.
- `PED_ID`: pedido asociado.
- `PDB_TIPO_BOUQUET`: tipo de bouquet.
- `PDB_COLOR`: color.
- `PDB_TAMANO`: tamaño.
- `PDB_TIPO_FLOR`: tipo de flor.
- `PDB_DECORACION`: decoración.
- `PDB_OBS`: observaciones.

### `PRUEBA_PEDIDO`
- `PRP_ID`: identificador de la prueba.
- `PED_ID`: pedido asociado.
- `PRP_NUM`: número de prueba.
- `PRP_FEC`: fecha de prueba.
- `PRP_HOR`: hora de prueba.
- `PRP_ESTADO`: estado de la prueba.
- `PRP_OBS`: observaciones.
- `PRP_HAB`: habilitación lógica.

### `PAGO_PEDIDO`
- `PPD_ID`: identificador del pago.
- `PED_ID`: pedido al que pertenece el pago.
- `USU_ID`: usuario que registró el pago.
- `PPD_FEC`: fecha y hora del pago.
- `PPD_MONTO`: monto pagado.
- `PPD_METODO`: método de pago.
- `PPD_OBS1`: observación principal.
- `PPD_OBS2`: observación secundaria.

### `TIPO_RECIBO`
- `TIR_ID`: identificador del tipo de recibo.
- `TIR_NOM`: nombre del tipo.
- `TIR_DES`: descripción.
- `TIR_HAB`: estado de habilitación.
- `TIR_FEC_REG`: fecha de registro.

### `RECIBO`
- `REC_ID`: identificador del recibo.
- `TIR_ID`: tipo de recibo.
- `CLI_ID`: cliente asociado.
- `USU_ID`: usuario que generó o registró el recibo.
- `VEB_ID`: venta de boutique asociada, si aplica.
- `PPD_ID`: pago de pedido asociado, si aplica.
- `REC_COD`: código del recibo.
- `REC_FEC`: fecha y hora del recibo.
- `REC_NOM_RAZON_SOCIAL`: nombre o razón social mostrada en el recibo.
- `REC_CI_NIT`: CI o NIT mostrado en el recibo.
- `REC_TOTAL`: total general del recibo.
- `REC_TOTAL_PEDIDO`: total del pedido, si corresponde.
- `REC_MONTO_PAGADO`: monto pagado en esa operación.
- `REC_SALDO_POSTERIOR`: saldo restante posterior al pago.
- `REC_METODO_PAGO`: método de pago mostrado.
- `REC_ESTADO`: estado del recibo.
- `REC_OBS`: observaciones.

### `DETALLE_RECIBO`
- `DER_ID`: identificador del detalle.
- `REC_ID`: recibo al que pertenece.
- `DER_CONCEPTO`: concepto del detalle.
- `DER_CANTIDAD`: cantidad.
- `DER_PRECIO_UNIDAD`: precio unitario.
- `DER_SUBTOTAL`: subtotal calculado.
- `DER_OBS`: observaciones.

### `INGRESO`
- `ING_ID`: identificador del ingreso.
- `PPD_ID`: pago de pedido asociado, si aplica.
- `VEB_ID`: venta asociada, si aplica.
- `USU_ID`: usuario que registró o consolidó el ingreso.
- `ING_CONCEPTO`: concepto del ingreso.
- `ING_FEC`: fecha y hora.
- `ING_TIPO`: tipo de ingreso.
- `ING_MONTO`: monto ingresado.
- `ING_METODO`: método de pago.
- `ING_OBS1`: observación principal.
- `ING_OBS2`: observación secundaria.
- `ING_ESTADO`: estado del registro.

### `EGRESO`
- `EGR_ID`: identificador del egreso.
- `USU_ID`: usuario que registró el egreso.
- `EGR_FEC`: fecha y hora.
- `EGR_TIPO`: tipo de egreso.
- `EGR_CONCEPTO`: concepto del gasto.
- `EGR_CANTIDAD`: cantidad.
- `EGR_PRECIO_UNIDAD`: precio unitario.
- `EGR_BENEFICIARIO`: persona o entidad beneficiaria.
- `EGR_MONTO`: monto calculado del egreso.
- `EGR_OBS1`, `EGR_OBS2`, `EGR_OBS3`: observaciones.
- `EGR_ESTADO`: estado del registro.

### `AUDITORIA_SISTEMA`
- `AUD_ID`: identificador del log.
- `USU_ID`: usuario que hizo la acción.
- `AUD_FEC`: fecha y hora del evento.
- `AUD_TABLA`: tabla afectada.
- `AUD_ID_REGISTRO`: identificador del registro afectado.
- `AUD_ACCION`: tipo de acción.
- `AUD_CAMPO`: campo afectado, si aplica.
- `AUD_VALOR_ANTERIOR`: valor previo.
- `AUD_VALOR_NUEVO`: valor nuevo.
- `AUD_DESCRIPCION`: descripción del evento.
- `AUD_IP`: IP de origen.
- `AUD_DISPOSITIVO`: dispositivo o cliente usado.

---

## 6. Relaciones entre tablas

La tabla `ROL` se relaciona con `CUENTA`, ya que cada cuenta necesita un rol para determinar su nivel de acceso dentro del sistema. La tabla `USUARIO` se relaciona también con `CUENTA`, porque una cuenta pertenece a un usuario específico, y además participa en módulos operativos como ventas, pagos, salidas de material, ingresos, egresos, recibos y auditoría, permitiendo identificar quién ejecutó cada acción.

La tabla `CLIENTE` se relaciona con `PEDIDO`, `VENTA_BOUTIQUE` y `RECIBO`. Esto permite que un cliente pueda tener varios pedidos, varias compras directas y varios comprobantes emitidos a su nombre. De esta manera, el sistema conserva trazabilidad comercial y documental.

La tabla `TIPO_ITEM_BOUTIQUE` se relaciona con `ITEM_BOUTIQUE`, ya que cada artículo de boutique debe pertenecer a un tipo definido. A su vez, `ITEM_BOUTIQUE` se relaciona con `DETALLE_VESTIDO_BOUTIQUE`, `DETALLE_VELO_BOUTIQUE` y `DETALLE_BOUQUET_BOUTIQUE`, permitiendo que el artículo base tenga información especializada solo cuando corresponde. También se relaciona con `VENTA_BOUTIQUE`, porque las ventas se realizan sobre los artículos registrados en boutique.

La tabla `INVENTARIO_TALLER` se relaciona con `SALIDA_MATERIAL_TALLER`, ya que cada salida de material debe corresponder a un insumo existente en el inventario del taller. Esto permite controlar el flujo de materiales desde el stock hacia costureros, decoradores u otros destinos.

La tabla `PEDIDO` se relaciona con `CLIENTE` y funciona como tabla base del módulo de pedidos. A partir de ella se conectan `PEDIDO_VESTIDO`, `PEDIDO_VELO`, `PEDIDO_COLA`, `PEDIDO_MANGA` y `PEDIDO_BOUQUET`, que almacenan únicamente la información específica del componente pedido. Además, `PEDIDO` se relaciona con `PRUEBA_PEDIDO`, permitiendo registrar múltiples pruebas por pedido, y con `PAGO_PEDIDO`, que registra cada pago realizado sobre el pedido.

La tabla `PAGO_PEDIDO` se relaciona indirectamente con `RECIBO` e `INGRESO`, ya que un pago puede dar origen a un recibo y a un ingreso financiero registrado por el sistema. La tabla `VENTA_BOUTIQUE` también se relaciona indirectamente con `RECIBO` e `INGRESO`, porque una venta directa debe generar comprobante e ingreso correspondiente.

La tabla `TIPO_RECIBO` se relaciona con `RECIBO`, clasificando cada comprobante emitido. `RECIBO` se relaciona con `CLIENTE`, `USUARIO`, `VENTA_BOUTIQUE` y `PAGO_PEDIDO`, permitiendo identificar el origen documental de cada recibo. A su vez, `DETALLE_RECIBO` se relaciona con `RECIBO`, descomponiendo el contenido del comprobante en conceptos y subtotales.

La tabla `INGRESO` se relaciona con `PAGO_PEDIDO`, `VENTA_BOUTIQUE` y `USUARIO`. Esto permite centralizar entradas de dinero provenientes de ventas o pagos de pedidos, registrando además qué usuario consolidó el movimiento. La tabla `EGRESO` se relaciona con `USUARIO`, ya que todo gasto registrado debe estar asociado al responsable que lo ingresó al sistema.

Finalmente, `AUDITORIA_SISTEMA` se relaciona con `USUARIO` y de forma lógica con todas las demás tablas, ya que su función es registrar eventos relevantes que ocurren sobre ellas. De esta manera, el sistema puede dejar constancia de inserciones, actualizaciones, eliminaciones lógicas, cambios de estado y accesos.

---

## 7. Reglas de control que debe aplicar el backend

### Seguridad
- Las contraseñas de `CUENTA` deben guardarse en hash, nunca en texto plano.
- No se debe permitir iniciar sesión con cuentas deshabilitadas.
- No se debe permitir operar con usuarios deshabilitados.
- La confirmación de contraseña se valida en frontend y backend, pero no se almacena en la BD.

### Boutique
- Al registrar un `ITEM_BOUTIQUE`, el backend debe validar que el `TIB_ID` exista y esté habilitado.
- Si el artículo es vestido, velo o bouquet, el backend debe guardar primero `ITEM_BOUTIQUE` y luego su tabla detalle correspondiente dentro de una misma transacción.
- No debe permitirse vender un artículo sin stock suficiente.
- `VEB_TOT` se calcula automáticamente en la BD, pero el backend debe validar que el descuento no supere el subtotal.
- Si hay descuento, debe exigirse motivo; si no hay descuento, el motivo debe quedar nulo.
- No debe permitirse vender artículos deshabilitados.

### Taller
- No debe permitirse registrar salidas de material si el stock disponible es insuficiente.
- Cada salida de material debe descontar stock automáticamente desde el backend o mediante la lógica que implementes.
- La unidad de medida usada en la salida debe ser coherente con la del material.

### Pedidos
- Al crear un pedido, debe existir un cliente válido.
- `PED_TOTAL_PAGADO` y `PED_SALDO` deben recalcularse automáticamente a partir de `PAGO_PEDIDO`.
- No debe permitirse editar manualmente desde interfaz los campos resumen del pedido si estos dependen de pagos reales.
- Si el pedido tiene descuento, debe existir motivo del descuento.
- No debe permitirse que el descuento supere el precio total del pedido.
- Las tablas hijas `PEDIDO_VESTIDO`, `PEDIDO_VELO`, `PEDIDO_COLA`, `PEDIDO_MANGA` y `PEDIDO_BOUQUET` solo deben llenarse si aplican al tipo real del pedido.
- En `PRUEBA_PEDIDO`, el backend debe evitar duplicar el mismo número de prueba para un mismo pedido.
- El backend debe validar que la secuencia de pruebas tenga sentido cronológico.

### Pagos de pedido
- No debe permitirse registrar pagos con monto menor o igual a cero.
- No debe permitirse registrar pagos sobre pedidos cancelados.
- Después de registrar, editar o eliminar un pago, el backend debe recalcular:
  - `PED_TOTAL_PAGADO`
  - `PED_SALDO`
- Si manejas clasificación de pago como “a cuenta” o “pago final”, esta debe calcularse automáticamente desde backend según el saldo posterior.

### Recibos
- **Los recibos deben llenarse automáticamente desde el backend.**
- El usuario no debe llenar manualmente montos, saldo, totales ni detalle general del recibo.
- Cuando se registre una `VENTA_BOUTIQUE`, el backend debe generar automáticamente:
  - el registro en `RECIBO`
  - sus filas en `DETALLE_RECIBO`
- Cuando se registre un `PAGO_PEDIDO`, el backend debe generar automáticamente:
  - el registro en `RECIBO`
  - sus filas en `DETALLE_RECIBO`
- El backend debe tomar automáticamente de las tablas relacionadas:
  - cliente
  - método de pago
  - montos
  - total del pedido
  - saldo posterior
  - usuario
  - fecha
- Solo deberían permitirse ajustes manuales en datos documentales excepcionales como nombre/razón social o CI/NIT, si el flujo del negocio lo requiere.

### Ingresos
- **La tabla `INGRESO` debe llenarse automáticamente desde el backend.**
- No debe registrarse manualmente un ingreso cuando ya proviene de una venta o de un pago de pedido.
- Al registrar una `VENTA_BOUTIQUE`, el backend debe crear automáticamente su `INGRESO`.
- Al registrar un `PAGO_PEDIDO`, el backend debe crear automáticamente su `INGRESO`.
- El backend debe impedir duplicar ingresos para una misma venta o un mismo pago.
- Solo deberían poder registrarse manualmente ingresos extraordinarios de tipo `OTRO`, `FLETE` o casos definidos por la lógica del negocio.

### Egresos
- `EGR_MONTO` se calcula automáticamente en la BD.
- El backend debe validar que cantidad y precio unitario sean positivos.
- No debe registrarse como egreso el dinero entregado bruto si hubo cambio; solo el gasto real.
- El backend debe validar la coherencia entre tipo de egreso y concepto.

### Auditoría
- Las operaciones críticas del sistema deben registrar automáticamente eventos en `AUDITORIA_SISTEMA`.
- Se recomienda auditar:
  - creación y modificación de clientes
  - creación y cambio de cuentas
  - ventas
  - pagos
  - cambios de estado
  - egresos
  - ingresos extraordinarios
  - anulaciones
  - cancelaciones
  - login y logout

---

## 8. Recomendaciones operativas

- Usar siempre transacciones en operaciones compuestas, por ejemplo:
  - venta + ingreso + recibo + detalle_recibo
  - pago_pedido + actualización de pedido + ingreso + recibo + detalle_recibo
- Validar en backend antes de insertar, aunque la BD ya tenga restricciones.
- Evitar ingreso manual repetido de datos ya existentes en relaciones.
- Usar UTF-8 para aceptar nombres, textos, tildes y caracteres especiales.
- Mantener control estricto del estado de registros activos, cancelados o anulados según el módulo.

---

## 9. Conclusión

La base de datos v.0.3 de BELLAARTE BOUTIQUE está organizada para soportar de manera más estructurada el funcionamiento real de la empresa: gestión de usuarios, clientes, artículos boutique, materiales de taller, pedidos especializados, pagos, recibos, ingresos, egresos y auditoría. El diseño combina tablas base y tablas detalle para evitar mezclar atributos que no aplican a todos los casos, y además establece una lógica clara para que los módulos financieros y documentales se alimenten automáticamente desde las operaciones reales del sistema.