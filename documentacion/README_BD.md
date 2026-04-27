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
Además, la parte documental se organiza mediante comprobantes internos, los cuales permiten dejar constancia de ventas directas, pagos de pedidos, fletes, garantías y otros movimientos comerciales no fiscales. Estos comprobantes no sustituyen una factura, nota fiscal ni documento equivalente tributario; su finalidad es servir como respaldo interno y constancia comercial para la boutique y el cliente.

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
- **Boutique:** `TIPO_ITEM_BOUTIQUE`, `ITEM_BOUTIQUE`, `DETALLE_VESTIDO_BOUTIQUE`, `DETALLE_VELO_BOUTIQUE`, `DETALLE_BOUQUET_BOUTIQUE`, `VENTA_BOUTIQUE`, `FLETE_VESTIDO`, `SALIDA_FLETE`
- **Taller:** `INVENTARIO_TALLER`, `SALIDA_MATERIAL_TALLER`
- **Fletes:** `FLETE_VESTIDO`, `SALIDA_FLETE`
- **Pedidos:** `PEDIDO`, `PEDIDO_VESTIDO`, `PEDIDO_VELO`, `PEDIDO_COLA`, `PEDIDO_MANGA`, `PEDIDO_BOUQUET`, `PRUEBA_PEDIDO`, `PAGO_PEDIDO`
- **Documentos internos:** `TIPO_COMPROBANTE`, `COMPROBANTE_INTERNO`, `DETALLE_COMPROBANTE`
- **Finanzas:** `EGRESO`
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
- Sirve como base comercial para generar ingresos y comprobantes internos.

### `FLETE_VESTIDO`

- Registra la configuración general de un vestido de boutique habilitado para flete.
- Permite controlar si un vestido está disponible, en flete, en revisión, agotado, pasado para venta o retirado.
- Guarda el precio referencial de flete, el máximo de salidas permitidas y la cantidad de salidas actuales.
- Sirve para evitar que un vestido sea fletado más veces de las permitidas.
- Se relaciona con `DETALLE_VESTIDO_BOUTIQUE`, porque solo los vestidos registrados en boutique pueden ser habilitados para flete.

### `SALIDA_FLETE`

- Registra cada salida individual de un vestido fletable.
- Guarda el cliente que se llevó el vestido, el usuario que registró la operación, el número de salida, fechas, precio, descuento, garantía y estado de devolución.
- Permite controlar la trazabilidad completa de cada flete realizado.
- Sirve para registrar si el vestido fue devuelto en buen estado, con observación, dañado, incompleto o con necesidad de arreglo.
- Permite generar recibos e ingresos por operaciones de flete.

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

### `TIPO_COMPROBANTE`

- Define los tipos de comprobantes internos que puede generar el sistema.
- Permite clasificar documentos como nota de venta, recibo de pago de pedido, comprobante de flete, comprobante de garantía u otros documentos internos.
- Sirve como catálogo documental para diferenciar el origen y finalidad de cada comprobante.
- Permite indicar si el tipo de comprobante corresponde o no a un documento fiscal, aunque en la versión actual los comprobantes serán manejados como documentos internos no fiscales.

### `COMPROBANTE_INTERNO`

- Guarda el encabezado de los comprobantes internos generados por el sistema.
- Registra cliente, usuario, código, fecha, datos mostrados del cliente, montos, método de pago, estado y observaciones.
- Puede estar asociado a una venta directa de boutique, a un pago de pedido o a una salida de flete.
- Sirve como constancia comercial interna para documentar pagos, ventas, fletes, garantías y saldos.
- No representa una factura, nota fiscal ni documento equivalente tributario.
- Conserva una copia histórica de los datos principales mostrados al cliente al momento de emitir el comprobante.

### `DETALLE_COMPROBANTE`

- Guarda el detalle interno de cada comprobante generado.
- Registra conceptos, cantidades, precios unitarios, descuentos y subtotales.
- Sirve para mostrar las líneas internas del comprobante entregado al cliente.
- Permite describir con claridad el motivo del cobro, por ejemplo venta de artículo, pago a cuenta, pago final, flete, garantía o arreglo.

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

### `FLETE_VESTIDO`

- `FLE_ID`: identificador único del registro de flete del vestido.
- `DVB_ID`: vestido de boutique asociado al flete.
- `USU_ID`: usuario interno que habilitó o registró el vestido como fletable.
- `FLE_PRECIO_FLETE_REF`: precio referencial sugerido para fletar el vestido.
- `FLE_MAX_SALIDAS`: cantidad máxima de salidas permitidas para el vestido.
- `FLE_SALIDAS_ACTUALES`: cantidad acumulada de veces que el vestido ya fue fletado.
- `FLE_ESTADO`: estado actual del vestido dentro del ciclo de flete.
- `FLE_FEC_HAB_FLETE`: fecha y hora en que el vestido fue habilitado para flete.
- `FLE_OBS`: observaciones generales sobre el vestido fletable.
- `FLE_HAB`: indica si el registro de flete se encuentra habilitado.

### `SALIDA_FLETE`

- `SFL_ID`: identificador único de la salida de flete.
- `FLE_ID`: vestido fletable asociado a la salida.
- `CLI_ID`: cliente que se llevó el vestido en flete.
- `USU_ID`: usuario interno que registró la salida.
- `SFL_NUM`: número de salida del vestido dentro de su ciclo de flete.
- `SFL_FEC_REG`: fecha y hora en que se registró la salida.
- `SFL_FEC_SALIDA`: fecha en que el vestido sale de boutique.
- `SFL_FEC_DEVOLUCION_PREVISTA`: fecha acordada para la devolución del vestido.
- `SFL_FEC_DEVOLUCION_REAL`: fecha real en que el vestido fue devuelto.
- `SFL_PRECIO`: precio cobrado por esa salida de flete.
- `SFL_DESCUENTO`: descuento aplicado al precio del flete, si corresponde.
- `SFL_MOTIVO_DESC`: motivo del descuento aplicado al flete.
- `SFL_GARANTIA`: monto recibido como garantía por la salida del vestido.
- `SFL_GARANTIA_DEVUELTA`: monto de garantía devuelto al cliente después de revisar el vestido.
- `SFL_ESTADO_SALIDA`: estado operativo de la salida de flete.
- `SFL_ESTADO_ENTREGA`: estado del vestido al momento de entregarlo al cliente.
- `SFL_ESTADO_DEVOLUCION`: estado del vestido al momento de ser devuelto.
- `SFL_REQUIERE_ARREGLO`: indica si el vestido requiere arreglo después de la devolución.
- `SFL_MONTO_ARREGLO`: monto cobrado o descontado por arreglo, daño o deterioro.
- `SFL_DESCRIPCION_ARREGLO`: descripción del daño, arreglo o situación detectada.
- `SFL_OBS_ENTREGA`: observaciones registradas al momento de entregar el vestido.
- `SFL_OBS_DEVOLUCION`: observaciones registradas al momento de devolver el vestido.
- `SFL_HAB`: indica si la salida de flete se encuentra habilitada.

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

### `TIPO_COMPROBANTE`

- `TCO_ID`: identificador único del tipo de comprobante.
- `TCO_NOM`: nombre del tipo de comprobante.
- `TCO_DES`: descripción del tipo de comprobante.
- `TCO_ES_FISCAL`: indica si el tipo de comprobante tiene finalidad fiscal. En la versión actual normalmente será falso.
- `TCO_HAB`: estado de habilitación del tipo de comprobante.
- `TCO_FEC_REG`: fecha y hora de registro.

### `COMPROBANTE_INTERNO`

- `COI_ID`: identificador único del comprobante interno.
- `TCO_ID`: tipo de comprobante interno asociado.
- `CLI_ID`: cliente asociado al comprobante, si corresponde.
- `USU_ID`: usuario que generó o registró el comprobante.
- `VEB_ID`: venta directa de boutique asociada, si el comprobante nace de una venta.
- `PPD_ID`: pago de pedido asociado, si el comprobante nace de un pago de pedido.
- `SFL_ID`: salida de flete asociada, si el comprobante nace de una operación de flete.
- `COI_COD`: código interno único del comprobante.
- `COI_FEC`: fecha y hora de emisión del comprobante.
- `COI_NOM_CLIENTE`: nombre del cliente mostrado en el comprobante.
- `COI_CI_NIT_CLIENTE`: CI o NIT del cliente mostrado en el comprobante.
- `COI_CEL_CLIENTE`: celular del cliente mostrado en el comprobante.
- `COI_SUBTOTAL`: subtotal documentado en el comprobante.
- `COI_DESCUENTO`: descuento documentado en el comprobante.
- `COI_TOTAL`: total final documentado en el comprobante.
- `COI_MONTO_PAGADO`: monto recibido en esa operación.
- `COI_SALDO_POSTERIOR`: saldo restante después del pago, si corresponde.
- `COI_GARANTIA`: monto de garantía registrado, si corresponde.
- `COI_METODO_PAGO`: método de pago utilizado.
- `COI_ESTADO`: estado del comprobante, por ejemplo emitido o anulado.
- `COI_OBS`: observaciones del comprobante.
- `COI_HAB`: habilitación lógica del comprobante.

### `DETALLE_COMPROBANTE`

- `DCO_ID`: identificador único del detalle del comprobante.
- `COI_ID`: comprobante interno al que pertenece el detalle.
- `DCO_CONCEPTO`: concepto o descripción de la línea del comprobante.
- `DCO_CANTIDAD`: cantidad correspondiente al concepto.
- `DCO_PRECIO_UNIDAD`: precio unitario del concepto.
- `DCO_DESCUENTO`: descuento aplicado a la línea del detalle.
- `DCO_SUBTOTAL`: subtotal calculado de la línea.
- `DCO_OBS`: observaciones específicas del detalle.

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

a tabla `FLETE_VESTIDO` se relaciona con `DETALLE_VESTIDO_BOUTIQUE`, ya que solo un vestido previamente registrado dentro del inventario de boutique puede ser habilitado para flete. Esta relación permite mantener separada la información general del vestido de su configuración específica como prenda fletable.

La tabla `FLETE_VESTIDO` también se relaciona con `USUARIO`, porque debe identificarse qué usuario interno habilitó o registró el vestido como disponible para flete. Esto permite mantener trazabilidad operativa sobre la gestión de inventario y decisiones comerciales.

La tabla `SALIDA_FLETE` se relaciona con `FLETE_VESTIDO`, ya que cada salida corresponde a un vestido fletable específico. Un mismo vestido puede tener varias salidas históricas, pero solo una salida activa a la vez.

La tabla `SALIDA_FLETE` se relaciona con `CLIENTE`, porque cada salida debe estar asociada al cliente que recibe temporalmente el vestido. Esto permite consultar el historial de fletes por cliente y saber quién tuvo el vestido en una determinada fecha.

La tabla `SALIDA_FLETE` se relaciona con `USUARIO`, ya que cada salida debe registrar al usuario interno responsable de realizar la operación. Esto permite controlar quién entregó, registró o gestionó el flete.

De forma documental, `SALIDA_FLETE` puede relacionarse con `RECIBO`, ya que una salida de flete puede generar un comprobante por el monto cobrado, la garantía recibida o algún cobro adicional por arreglo. Esta relación permite que los ingresos por flete formen parte de los reportes financieros del sistema.

La tabla `INVENTARIO_TALLER` se relaciona con `SALIDA_MATERIAL_TALLER`, ya que cada salida de material debe corresponder a un insumo existente en el inventario del taller. Esto permite controlar el flujo de materiales desde el stock hacia costureros, decoradores u otros destinos.

La tabla `PEDIDO` se relaciona con `CLIENTE` y funciona como tabla base del módulo de pedidos. A partir de ella se conectan `PEDIDO_VESTIDO`, `PEDIDO_VELO`, `PEDIDO_COLA`, `PEDIDO_MANGA` y `PEDIDO_BOUQUET`, que almacenan únicamente la información específica del componente pedido. Además, `PEDIDO` se relaciona con `PRUEBA_PEDIDO`, permitiendo registrar múltiples pruebas por pedido, y con `PAGO_PEDIDO`, que registra cada pago realizado sobre el pedido.

La tabla `PAGO_PEDIDO` se relaciona indirectamente con `COMPROBANTE_INTERNO`, ya que cada pago realizado sobre un pedido puede generar una constancia interna de pago. Esta constancia permite documentar el monto pagado, el método de pago y el saldo posterior del pedido.

La tabla `VENTA_BOUTIQUE` también se relaciona con `COMPROBANTE_INTERNO`, porque una venta directa puede generar una nota de venta interna. Esta nota permite dejar constancia del artículo vendido, el monto cobrado, el descuento aplicado y el usuario responsable de la operación.

La tabla `SALIDA_FLETE` puede relacionarse con `COMPROBANTE_INTERNO`, ya que una operación de flete puede generar comprobantes internos por el cobro del flete, la garantía recibida, una devolución de garantía o un arreglo cobrado por daño o deterioro.

La tabla `TIPO_COMPROBANTE` se relaciona con `COMPROBANTE_INTERNO`, clasificando cada documento emitido según su finalidad: nota de venta, recibo de pago de pedido, comprobante de flete, comprobante de garantía u otro documento interno.

La tabla `COMPROBANTE_INTERNO` se relaciona con `CLIENTE` y `USUARIO`, permitiendo identificar a quién corresponde el comprobante y quién lo generó. Además, se relaciona opcionalmente con `VENTA_BOUTIQUE`, `PAGO_PEDIDO` o `SALIDA_FLETE`, manteniendo un único origen operativo por comprobante.

La tabla `DETALLE_COMPROBANTE` se relaciona con `COMPROBANTE_INTERNO`, descomponiendo el contenido del documento en conceptos, cantidades, precios, descuentos y subtotales.

La tabla `EGRESO` se relaciona con `USUARIO`, ya que todo gasto registrado debe estar asociado al responsable que lo ingresó al sistema.

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

### Fletes

- Solo deben habilitarse para flete los vestidos registrados en `DETALLE_VESTIDO_BOUTIQUE`.
- El backend debe validar que el vestido corresponda a un tipo permitido para flete, principalmente vestidos de 15 años.
- No debe permitirse habilitar dos veces el mismo vestido como fletable.
- Un vestido fletable debe iniciar normalmente con estado `DISPONIBLE`.
- No debe permitirse registrar una salida si el vestido no está en estado `DISPONIBLE`.
- No debe permitirse registrar una nueva salida si el vestido ya tiene una salida activa en estado `RESERVADO` o `EN_FLETE`.
- El número de salida `SFL_NUM` debe ser único por cada vestido fletable.
- El backend debe calcular o validar que `SFL_NUM` siga una secuencia lógica según las salidas anteriores del vestido.
- No debe permitirse que `FLE_SALIDAS_ACTUALES` supere `FLE_MAX_SALIDAS`.
- Cuando se registra una salida efectiva, el estado del vestido debe cambiar a `EN_FLETE`.
- Cuando el vestido se devuelve, el backend debe registrar la fecha real de devolución y el estado de devolución.
- Cuando una salida queda como `DEVUELTO`, `DEVUELTO_CON_OBSERVACION` o `DEVUELTO_CON_ARREGLO`, debe actualizarse el contador `FLE_SALIDAS_ACTUALES`.
- Si el vestido todavía no alcanzó el máximo de salidas, puede volver a estado `DISPONIBLE` después de la revisión correspondiente.
- Si el vestido alcanzó el máximo de salidas permitidas, debe pasar a estado `AGOTADO`.
- Un vestido en estado `AGOTADO`, `PASADO_PARA_VENTA` o `RETIRADO` no debe poder registrar nuevas salidas de flete.
- Si el vestido vuelve con daño, observación o arreglo, deben registrarse las observaciones correspondientes.
- Si `SFL_REQUIERE_ARREGLO` es verdadero, debe existir descripción del arreglo y monto asociado.
- Si se aplica descuento en una salida de flete, debe registrarse obligatoriamente el motivo del descuento.
- No debe permitirse que el descuento sea mayor al precio del flete.
- La fecha de devolución prevista no debe ser anterior a la fecha de salida.
- La fecha de devolución real no debe ser anterior a la fecha de salida.
- La garantía devuelta no debe ser mayor a la garantía recibida.
- Las salidas anuladas no deben incrementar el contador de salidas actuales.
- Los cambios de estado relevantes deben registrarse en auditoría.

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

### Comprobantes internos

- **Los comprobantes internos deben generarse automáticamente desde el backend.**
- El usuario no debe llenar manualmente montos, saldo, totales ni detalle general del comprobante si estos datos provienen de una operación registrada.
- El comprobante interno no debe ser el origen de una venta, pago o flete; solo debe documentar una operación ya registrada.
- Cuando se registre una `VENTA_BOUTIQUE`, el backend debe generar automáticamente:
  - el registro en `COMPROBANTE_INTERNO`
  - sus filas en `DETALLE_COMPROBANTE`
- Cuando se registre un `PAGO_PEDIDO`, el backend debe generar automáticamente:
  - el registro en `COMPROBANTE_INTERNO`
  - sus filas en `DETALLE_COMPROBANTE`
- Cuando se registre una `SALIDA_FLETE` con cobro, el backend debe generar automáticamente:
  - el comprobante interno correspondiente al flete
  - el detalle del comprobante
- Si la operación de flete incluye garantía, el backend debe registrar la garantía en la operación correspondiente y documentarla en el comprobante interno según la lógica definida.
- El backend debe tomar automáticamente de las tablas relacionadas:
  - cliente
  - usuario
  - método de pago
  - montos
  - descuento
  - total
  - saldo posterior
  - garantía
  - fecha
  - concepto de la operación
- Cada comprobante interno debe tener un solo origen operativo:
  - `VENTA_BOUTIQUE`
  - `PAGO_PEDIDO`
  - `SALIDA_FLETE`
- No debe permitirse que un mismo comprobante esté asociado simultáneamente a una venta, a un pago de pedido y a una salida de flete.
- Los campos de montos guardados en `COMPROBANTE_INTERNO` y `DETALLE_COMPROBANTE` representan una copia histórica del documento emitido.
- La copia histórica del comprobante permite conservar los datos mostrados al cliente aunque después se modifiquen datos del cliente, producto, pedido o flete.
- Solo deberían permitirse ajustes manuales en datos documentales excepcionales como nombre mostrado del cliente, CI/NIT, celular u observaciones, si el flujo del negocio lo requiere.
- Todo comprobante interno debe mostrar desde frontend una leyenda clara indicando que no constituye factura, nota fiscal ni documento equivalente.
- La leyenda sugerida es: “Documento de control interno. No constituye factura, nota fiscal ni documento equivalente. No válido para crédito fiscal ni descargo tributario.”
- Los comprobantes anulados no deben eliminarse físicamente; deben conservarse con estado `ANULADO` para mantener trazabilidad.
- La anulación de un comprobante no debe anular automáticamente la operación original, salvo que el backend ejecute explícitamente una transacción de reversión controlada.

### Ingresos

- Los ingresos no se registran manualmente en una tabla independiente.
- Los ingresos se obtienen mediante reportes generados a partir de operaciones reales:
  - ventas directas registradas en `VENTA_BOUTIQUE`
  - pagos de pedidos registrados en `PAGO_PEDIDO`
  - cobros de fletes registrados en `SALIDA_FLETE`
  - cobros por arreglos o daños asociados a fletes, si corresponde
- Los comprobantes internos sirven como respaldo documental de estas operaciones, pero no deben ser considerados como el origen primario del ingreso.
- Las garantías de flete no deben considerarse ingreso definitivo mientras estén pendientes de devolución.
- Una garantía solo puede convertirse en ingreso si existe una justificación operativa, por ejemplo daño, arreglo, penalidad o incumplimiento de devolución.

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
  - anulaciones
  - cancelaciones
  - login y logout

---

## 8. Recomendaciones operativas

- Usar siempre transacciones en operaciones compuestas, por ejemplo:
  - venta + recibo + detalle_recibo
  - pago_pedido + actualización de pedido + recibo + detalle_recibo
- Validar en backend antes de insertar, aunque la BD ya tenga restricciones.
- Evitar ingreso manual repetido de datos ya existentes en relaciones.
- Usar UTF-8 para aceptar nombres, textos, tildes y caracteres especiales.
- Mantener control estricto del estado de registros activos, cancelados o anulados según el módulo.
- Usar transacciones en operaciones compuestas de comprobantes internos, por ejemplo:
  - venta_boutique + comprobante_interno + detalle_comprobante
  - pago_pedido + actualización de saldo + comprobante_interno + detalle_comprobante
  - salida_flete + comprobante_interno + detalle_comprobante
  - devolución de flete + ajuste de garantía + comprobante interno, si corresponde
- No permitir que el usuario edite manualmente montos generados desde operaciones reales.
- Mantener los comprobantes internos como documentos históricos, no como tablas operativas principales.
- La operación real debe registrarse primero en su módulo correspondiente y luego generar el comprobante.
- Los comprobantes internos deben conservarse incluso si son anulados, para mantener trazabilidad.
- El frontend debe mostrar claramente que el comprobante interno no tiene valor fiscal.

---

## 9. Index

Verificar los index que se sugieren en BASE_DE_DATOS.postgres

## 10. Reportes

Verificar los reportes que se sugieren en BASE_DE_DATOS.postgres

- MUY IMPORTANTE cambiar el dato correspondiente de la tabla "usuario" y sus atributos correspondientes en los reportes (para seguir un uso adecuado de la sintaxis).

## 11. Conclusión

La base de datos v.0.3 de BELLAARTE BOUTIQUE está organizada para soportar de manera más estructurada el funcionamiento real de la empresa: gestión de usuarios, clientes, artículos boutique, materiales de taller, pedidos especializados, pagos, recibos, egresos y auditoría. El diseño combina tablas base y tablas detalle para evitar mezclar atributos que no aplican a todos los casos, y además establece una lógica clara para que los módulos financieros y documentales se alimenten automáticamente desde las operaciones reales del sistema.
