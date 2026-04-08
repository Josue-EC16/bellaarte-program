README – BASE DE DATOS V.0.1

BELLAARTE BOUTIQUE
Motor: PostgreSQL 17

1. Descripción general

La base de datos v.0.1 fue diseñada para centralizar los procesos básicos de BELLAARTE BOUTIQUE en una primera versión funcional del sistema. Su propósito es reemplazar parcialmente el manejo disperso en archivos Excel y registros manuales, unificando en una sola estructura los siguientes módulos:

seguridad y acceso al sistema
clientes
inventario de boutique
inventario de taller
salidas de material de taller
pedidos de confección y otros pedidos especiales
pagos de pedidos
ventas directas de boutique
ingresos
egresos

Esta versión prioriza la simplicidad y la operatividad, manteniendo la menor cantidad de tablas necesaria, pero conservando trazabilidad suficiente para la futura evolución del sistema.

2. Estructura general de la base de datos

La base está organizada en 5 bloques:

2.1. Seguridad
ROL
USUARIO
CUENTA
2.2. Clientes y operación comercial
CLIENTE
PEDIDO
PAGO_PEDIDO
2.3. Inventario boutique
INVENTARIO_BOUTIQUE
VENTA_BOUTIQUE
2.4. Inventario y salidas de taller
INVENTARIO_TALLER
SALIDA_MATERIAL_TALLER
2.5. Finanzas
INGRESO
EGRESO 3. Diccionario de datos por tabla
3.1. TABLA: ROL
Propósito

Define los roles del sistema. Permite controlar permisos y perfiles de acceso, por ejemplo administrador, cajera, asesora de moda o encargada.

Campos

ROL_ID
Identificador único del rol. Clave primaria.

ROL_NOM
Nombre del rol. Debe ser único.

ROL_DES
Descripción breve del rol.

ROL_HAB
Indica si el rol está habilitado o no.

ROL_FEC_REG
Fecha y hora de registro del rol.

Validaciones recomendadas en backend
no permitir nombres de rol duplicados
normalizar nombre de rol en mayúsculas o formato uniforme
no permitir crear cuentas con roles inhabilitados
3.2. TABLA: USUARIO
Propósito

Guarda la información del personal interno que utiliza el sistema o registra operaciones.

Campos

USU_ID
Identificador único del usuario.

USU_NOM
Nombres del usuario.

USU_APE_PAT
Apellido paterno.

USU_APE_MAT
Apellido materno.

USU_CEL
Número de celular.

USU_CI
Carnet de identidad.

USU_COR
Correo electrónico.

USU_DIR
Dirección del usuario.

USU_HAB
Indica si el usuario está habilitado.

USU_FEC_REG
Fecha y hora de registro.

Validaciones recomendadas en backend
validar formato de correo si se registra
validar longitud mínima de nombre y apellidos
validar que USU_CEL y USU_CI, si se usan como únicos en negocio, no se repitan
no permitir operar en módulos críticos con usuarios inhabilitados
3.3. TABLA: CUENTA
Propósito

Representa el acceso al sistema. Relaciona un usuario con un rol y almacena credenciales.

Campos

CUE_ID
Identificador único de la cuenta.

USU_ID
Usuario dueño de la cuenta. FK a USUARIO.

ROL_ID
Rol asignado. FK a ROL.

CUE_NOM_USU
Nombre de usuario para iniciar sesión.

CUE_CON
Contraseña almacenada en formato hash.

CUE_HAB
Indica si la cuenta está habilitada.

CUE_FEC_CRE
Fecha de creación de la cuenta.

CUE_ULT_ACC
Último acceso registrado.

Validaciones recomendadas en backend
almacenar contraseñas con hash seguro, nunca en texto plano
no permitir nombres de usuario duplicados
no permitir login con cuentas inhabilitadas
actualizar CUE_ULT_ACC automáticamente al iniciar sesión
opcionalmente, limitar un usuario a una sola cuenta activa
3.4. TABLA: CLIENTE
Propósito

Guarda los datos básicos de la clienta o cliente que realiza compras, pedidos o pagos.

Campos

CLI_ID
Identificador único del cliente.

CLI_COD
Código interno del cliente.

CLI_NOM
Nombres del cliente.

CLI_APE_PAT
Apellido paterno.

CLI_APE_MAT
Apellido materno.

CLI_CEL
Celular principal.

CLI_CEL_REF
Celular de referencia.

CLI_NOM_CEL_REF
Nombre de la persona de referencia.

CLI_COR
Correo electrónico.

CLI_CI
Carnet de identidad.

CLI_NAC
Nacionalidad.

CLI_ZONA
Zona de residencia.

CLI_CALLE
Calle o dirección complementaria.

CLI_OBS
Observaciones adicionales.

CLI_HAB
Indica si el cliente está habilitado.

CLI_FEC_REG
Fecha de registro.

Validaciones recomendadas en backend
usar VARCHAR para CI y celulares
validar longitud y formato de celular
validar correo si se registra
no permitir duplicidad de CLI_COD
opcionalmente validar CI único si el negocio lo exige
permitir nombres con tildes y Ñ
3.5. TABLA: INVENTARIO_BOUTIQUE
Propósito

Registra los productos terminados, accesorios y artículos comercializados directamente en boutique.

Campos

INB_ID
Identificador único del producto.

INB_COD
Código interno único del producto.

INB_TIPO
Tipo de artículo según enum: vestidos, accesorios, fustes, velos, bouquet, etc.

INB_DES
Descripción general del artículo.

INB_COLOR
Color principal del producto.

INB_FORMA
Forma o estilo, si aplica.

INB_TAMANO
Tamaño del producto.

INB_COPA_TALLA
Copa o talla especial, si aplica.

INB_TALLA
Talla general.

INB_MATERIAL
Material principal.

INB_MEDIDAS
Medidas adicionales del producto.

INB_PROVEEDOR
Proveedor o procedencia.

INB_PRECIO_COMPRA
Costo de adquisición.

INB_PRECIO_VENTA
Precio de venta sugerido.

INB_STOCK
Cantidad disponible.

INB_ESTADO
Indica si el producto está activo.

INB_OBS
Observaciones adicionales.

INB_FEC_REG
Fecha de registro.

Validaciones recomendadas en backend
no permitir códigos duplicados
no permitir stock negativo
no permitir precios negativos
si el producto es único o de una sola pieza, controlar que INB_STOCK sea entero lógico aunque el campo sea numérico
validar que el tipo, talla o copa sean coherentes con el tipo de artículo
si una venta se registra, el backend debe descontar stock automáticamente
3.6. TABLA: VENTA_BOUTIQUE
Propósito

Registra las ventas directas realizadas en boutique.

Campos

VEB_ID
Identificador único de la venta.

INB_ID
Producto vendido. FK a INVENTARIO_BOUTIQUE.

USU_ID
Usuario que registró la venta. FK a USUARIO.

CLI_ID
Cliente asociado, si se registra. FK a CLIENTE.

VEB_FEC
Fecha y hora de la venta.

VEB_CAN
Cantidad vendida.

VEB_PRE_UNI
Precio unitario aplicado en la venta.

VEB_DESCUENTO
Monto de descuento aplicado, si existe.

VEB_MOTIVO_DESC
Motivo del descuento: rebaja o promoción.

VEB_TOT
Total final de la venta.

VEB_METODO_PAGO
Método de pago utilizado.

VEB_OBS
Observaciones.

VEB_ESTADO
Estado de la venta: activa, cancelada o anulada.

Validaciones recomendadas en backend
validar que exista stock suficiente antes de vender
calcular VEB_TOT automáticamente:
subtotal = cantidad × precio unitario
total = subtotal - descuento
no permitir descuento mayor al subtotal
si VEB_DESCUENTO tiene valor, exigir VEB_MOTIVO_DESC
si no hay descuento, ambos deben quedar nulos
al cancelar o anular una venta, decidir si el stock vuelve al inventario
al registrar una venta activa, crear automáticamente el ingreso correspondiente en INGRESO
no permitir ventas con productos inactivos
3.7. TABLA: INVENTARIO_TALLER
Propósito

Registra el material e insumos del taller, como telas, guipures, hilos, pedrería, cierres y otros elementos usados en producción. Esto coincide con la necesidad de control de materiales descrita para el taller.

Campos

INT_ID
Identificador único del material.

INT_COD
Código interno único.

INT_NOM
Nombre del material.

INT_TIPO
Tipo de material.

INT_DES1
Descripción principal.

INT_DES2
Descripción complementaria.

INT_COLOR
Color del material.

INT_TAMANO
Tamaño general.

INT_MATERIAL
Composición o material específico.

INT_PROVEEDOR
Proveedor del material.

INT_COSTO_REF
Costo referencial.

INT_STOCK
Cantidad disponible.

INT_UNI_MED
Unidad de medida.

INT_STOCK_MIN
Stock mínimo deseado.

INT_ESTADO
Indica si el material está activo.

INT_OBS
Observaciones.

INT_FEC_REG
Fecha de registro.

Validaciones recomendadas en backend
no permitir códigos duplicados
no permitir stock negativo
no permitir costo referencial negativo
validar que la unidad de medida sea coherente con el tipo de material
si se registra salida de material, descontar stock automáticamente
permitir texto descriptivo amplio en materiales complejos
3.8. TABLA: SALIDA_MATERIAL_TALLER
Propósito

Registra las salidas de materiales del taller hacia costureros, decoradores o personal externo. Esta tabla responde directamente al proceso real de reparto de materiales del taller.

Campos

SMT_ID
Identificador único de la salida.

INT_ID
Material entregado. FK a INVENTARIO_TALLER.

USU_ID
Usuario que registró la salida.

SMT_FEC
Fecha y hora de la salida.

SMT_CAN
Cantidad entregada.

SMT_UNI_MED
Unidad de medida usada en la salida.

SMT_DESTINO
Nombre de la persona o destino al que se entrega el material.

SMT_OBS1
Observación principal.

SMT_OBS2
Observación complementaria.

SMT_ESTADO
Indica si la salida del material está habilitado lógicamente.

Validaciones recomendadas en backend
validar que el material exista y esté activo
validar que haya stock suficiente
descontar automáticamente INT_STOCK
registrar destino obligatorio cuando el material sale
validar coherencia entre unidad de salida y unidad del material
impedir salidas con cantidades negativas o cero
3.9. TABLA: PEDIDO
Propósito

Es la tabla central del proceso de confección y pedidos especiales. Guarda datos del pedido, medidas, fechas de pruebas, estado por prueba y resumen financiero. Este diseño responde al flujo real de BellaArte, donde el vestido pasa por varias pruebas y puede requerir de 3 a 5 etapas, además de pagos por cuotas.

Campos generales

PED_ID
Identificador único del pedido.

CLI_ID
Cliente dueño del pedido. FK a CLIENTE.

PED_COD
Código interno del pedido.

PED_TIPO
Tipo de pedido: confección, velo, cola, bouquet, flete, etc.

PED_NOM_PEDIDO
Nombre general del pedido.

PED_VIAJE
Indica si el pedido tiene condición especial por viaje.

PED_COLOR_PRIMERO
Color principal.

PED_COLOR_SEGUNDO
Color secundario, si aplica.

PED_DESCRIPCION_MATERIAL
Descripción de telas, guipures y materiales.

PED_DESCRIPCION_DISENO
Descripción del diseño.

PED_DESCRIPCION_3
Descripción adicional.

PED_FEC_REG_CONTRATO
Fecha y hora del contrato.

PED_ENCARGADO_CONTRATO
Nombre o referencia de quien cerró el contrato.

PED_FEC_DE_ENTREGA
Fecha principal de entrega acordada.

PED_FEC_ENTREGA_FINAL
Fecha real o final de entrega.

Medidas

PED_ANE_ESP
Ancho de espalda.

PED_TAL_ESP
Talle de espalda.

PED_TAL_DEL
Talle delantero.

PED_CON_CIN
Contorno de cintura.

PED_CON_CAD
Contorno de cadera.

PED_LAR_FAL
Largo de falda.

PED_SISA
Sisa.

PED_ANB_BUS
Ancho de busto.

PED_SEP_BUS
Separación de busto.

PED_TAL_BUS
Talle busto.

PED_TAL_COS
Talle costado.

PED_LAR_MAN
Largo de manga.

PED_BRA
Brazo.

PED_PUN
Puño.

Pruebas

PED_PRU1_FEC / PED_PRU1_HOR / PED_PRU1_EST
Fecha, hora y estado de la primera prueba.

PED_PRU2_FEC / PED_PRU2_HOR / PED_PRU2_EST
Segunda prueba.

PED_PRU3_FEC / PED_PRU3_HOR / PED_PRU3_EST
Tercera prueba.

PED_PRU4_FEC / PED_PRU4_HOR / PED_PRU4_EST
Cuarta prueba.

PED_PRU5_FEC / PED_PRU5_HOR / PED_PRU5_EST
Quinta prueba, si aplica.

Finanzas resumen

PED_DESCUENTO
Monto de descuento del pedido.

PED_MOTIVO_DESCUENTO
Motivo del descuento.

PED_PRE_TOT
Precio total del pedido.

PED_TOTAL_PAGADO
Total pagado acumulado.

PED_SALDO
Saldo pendiente.

Estado y control

PED_OBS
Observaciones generales.

PED_ESTADO_GENERAL
Estado del pedido: activo, entregado o cancelado.

PED_HAB
Habilitación lógica.

Validaciones recomendadas en backend
no permitir PED_COD duplicado
validar que PED_FEC_DE_ENTREGA no sea anterior a la fecha de contrato
validar secuencia lógica de pruebas:
prueba 2 no debe quedar antes de prueba 1
prueba 3 no antes de prueba 2, etc.
si hay descuento, exigir motivo
no permitir descuento mayor al precio total
PED_TOTAL_PAGADO y PED_SALDO deben actualizarse automáticamente a partir de PAGO_PEDIDO
no permitir editar manualmente PED_TOTAL_PAGADO y PED_SALDO desde interfaz
para tipos de pedido que no requieren medidas, permitir campos de medidas nulos
al marcar PED_ESTADO_GENERAL = ENTREGADO, validar que el saldo sea 0, salvo regla de negocio distinta
3.10. TABLA: PAGO_PEDIDO
Propósito

Registra cada pago realizado sobre un pedido. Puede ser una cuota parcial o el pago final. En el negocio real, el cliente suele pagar por pruebas o por etapas.

Campos

PPD_ID
Identificador único del pago.

PED_ID
Pedido al que pertenece el pago. FK a PEDIDO.

USU_ID
Usuario que registró el pago.

PPD_FEC
Fecha y hora del pago.

PPD_MONTO
Monto pagado.

PPD_METODO
Método de pago.

PPD_OBS1
Observación principal.

PPD_OBS2
Observación secundaria.

Validaciones recomendadas en backend
no permitir montos menores o iguales a 0
no permitir registrar pago si el pedido está cancelado
no permitir registrar pago si con ese pago se excede el total permitido, salvo que el negocio permita saldos a favor
después de registrar, editar o eliminar un pago:
recalcular PED_TOTAL_PAGADO
recalcular PED_SALDO
si quieres distinguir entre “a cuenta” y “pago final”, eso debe calcularse desde backend comparando la suma acumulada contra PED_PRE_TOT
si el ingreso se centraliza, al registrar un pago se debe crear automáticamente un registro en INGRESO
3.11. TABLA: INGRESO
Propósito

Centraliza los ingresos económicos del sistema. Puede recibir ingresos originados en ventas de boutique, pagos de pedidos y otros conceptos. Su lógica se apoya en el origen real del dinero.

Campos

ING_ID
Identificador único del ingreso.

PPD_ID
Pago de pedido asociado, si el ingreso proviene de PAGO_PEDIDO.

VEB_ID
Venta asociada, si el ingreso proviene de VENTA_BOUTIQUE.

USU_ID
Usuario que registró o consolidó el ingreso.

ING_CONCEPTO
Concepto descriptivo del ingreso.

ING_FEC
Fecha y hora del ingreso.

ING_TIPO
Tipo de ingreso: venta boutique, pago pedido, flete, ticket o vale, otro.

ING_MONTO
Monto del ingreso.

ING_METODO
Método de pago del ingreso.

ING_OBS1
Observación principal.

ING_OBS2
Observación secundaria.

EGR_ESTADO
Indica si la salida del material está habilitado lógicamente.

Validaciones recomendadas en backend
si ING_TIPO = PAGO_PEDIDO, exigir PPD_ID y dejar VEB_ID nulo
si ING_TIPO = VENTA_BOUTIQUE, exigir VEB_ID y dejar PPD_ID nulo
si ING_TIPO = OTRO, FLETE o TICKET O VALE, ambos IDs pueden ir nulos
no permitir que el monto del ingreso difiera del monto del origen, salvo política especial
si un pago de pedido o venta boutique ya generó ingreso, no permitir duplicarlo
usar INGRESO como tabla central generada automáticamente desde backend, evitando doble registro manual por parte de caja
para ingresos extraordinarios, permitir inserción manual desde un módulo específico

Nota técnica: en tu último script compartido, INGRESO muestra PPD_ID, VEB_ID y USU_ID, pero también conserva una FK llamada FK_ING_PED hacia PED_ID sin que esa columna aparezca declarada en la tabla; eso debe corregirse en el SQL final.

3.12. TABLA: EGRESO
Propósito

Registra las salidas de dinero del negocio, como compras, pagos a costura, decorado, mantenimiento, servicios, sueldos y otros egresos.

Campos

EGR_ID
Identificador único del egreso.

USU_ID
Usuario que registró el egreso.

EGR_FEC
Fecha y hora del egreso.

EGR_TIPO
Tipo de egreso.

EGR_CONCEPTO
Concepto detallado del egreso.

EGR_CANTIDAD
Cantidad comprada o pagada.

EGR_PRECIO_UNIDAD
Precio unitario referencial del egreso.

EGR_BENEFICIARIO
Persona o entidad que recibió el pago.

EGR_MONTO
Monto total real del egreso.

EGR_OBS1
Observación principal.

EGR_OBS2
Observación secundaria.

EGR_OBS3
Observación adicional.

EGR_ESTADO
Indica si la salida del material está habilitado lógicamente.

Validaciones recomendadas en backend
no permitir montos menores o iguales a 0
no permitir cantidad ni precio unitario menores o iguales a 0
calcular automáticamente:
EGR_MONTO = EGR_CANTIDAD × EGR_PRECIO_UNIDAD
cuando el egreso sea cuantificable
si el tipo de egreso es sueldo o servicio fijo, permitir una lógica especial
no guardar “dinero entregado” ni “cambio” como egreso; el egreso real es solo el monto final
si el egreso corresponde a compra de inventario, luego puede integrarse con actualización de inventario en futuras versiones 4. Relaciones principales entre tablas
Seguridad
ROL 1:N CUENTA
USUARIO 1:N CUENTA
Clientes y pedidos
CLIENTE 1:N PEDIDO
PEDIDO 1:N PAGO_PEDIDO
Boutique
INVENTARIO_BOUTIQUE 1:N VENTA_BOUTIQUE
USUARIO 1:N VENTA_BOUTIQUE
CLIENTE 1:N VENTA_BOUTIQUE opcional
Taller
INVENTARIO_TALLER 1:N SALIDA_MATERIAL_TALLER
USUARIO 1:N SALIDA_MATERIAL_TALLER
Finanzas
PAGO_PEDIDO 1:1 o 1:N lógico con INGRESO según diseño de backend
VENTA_BOUTIQUE 1:1 o 1:N lógico con INGRESO
USUARIO 1:N INGRESO
USUARIO 1:N EGRESO 5. Reglas de negocio recomendadas en backend
5.1. Seguridad
hash de contraseñas
control de permisos por rol
bloqueo de cuentas inhabilitadas
5.2. Inventario boutique
venta descuenta stock
cancelación puede devolver stock
no vender productos sin stock
5.3. Inventario taller
salida de material descuenta stock
no permitir salida sin existencia suficiente
5.4. Pedidos
toda prueba debe respetar secuencia temporal
PED_TOTAL_PAGADO y PED_SALDO salen de PAGO_PEDIDO
no marcar entregado si sigue con saldo, salvo regla especial
5.5. Pagos de pedido
el backend calcula si un pago es parcial o final
si el pago completa el total, actualizar saldo a 0
registrar automáticamente el ingreso financiero asociado
5.6. Ingresos
evitar doble registro manual
generar automáticamente desde PAGO_PEDIDO y VENTA_BOUTIQUE
permitir manual solo para ingresos extraordinarios
5.7. Egresos
calcular monto automáticamente cuando haya cantidad y precio unitario
no registrar como egreso el dinero entregado bruto si hubo cambio; solo el gasto real 6. Recomendaciones técnicas adicionales
Codificación

Usar base de datos y conexión en UTF-8 para aceptar correctamente:

tildes
Ñ
nombres propios
textos descriptivos
Identificadores SQL

Aunque los datos sí pueden tener tildes y caracteres especiales, es mejor que los nombres técnicos de tablas, columnas, enums, funciones y triggers se mantengan sin tildes ni Ñ para evitar problemas de compatibilidad con backend y ORM.

Integridad

Las restricciones CHECK de PostgreSQL ayudan a proteger datos mínimos, pero no reemplazan la validación del backend. La lógica fuerte del negocio debe estar en el servidor de aplicación.

7. Observación final

Tu modelo v.0.1 ya cubre lo esencial de la operación real de BellaArte Boutique: ventas, control de productos, control de materiales, pedidos con pruebas, pagos por cuotas e ingresos/egresos. Es una base suficientemente buena para una primera implementación web, siempre que el backend asuma correctamente las validaciones, los cálculos automáticos y la centralización financiera.

8. LOGS DEL SISTEMA

AUD_ID

Identificador único del log.

USU_ID

Usuario que realizó la acción.
Si fue una acción automática del sistema, podría quedar nulo o usar un usuario técnico.

AUD_FEC

Fecha y hora exacta del evento.

AUD_TABLA

Nombre de la tabla afectada.

Ejemplos:

PEDIDO
PAGO_PEDIDO
VENTA_BOUTIQUE
INVENTARIO_TALLER
AUD_ID_REGISTRO

ID del registro afectado.

Ejemplos:

pedido 15
venta 8
pago 24

Lo dejo como VARCHAR(50) para flexibilidad.

AUD_ACCION

Tipo de acción realizada.

AUD_CAMPO

Campo específico que cambió, si aplica.

Ejemplo:

PED_SALDO
INB_STOCK
VEB_ESTADO

En un insert completo o login podría ser nulo.

AUD_VALOR_ANTERIOR

Valor antes del cambio.

AUD_VALOR_NUEVO

Valor después del cambio.

AUD_DESCRIPCION

Descripción más humana del evento.

Ejemplo:

“Se actualizó el saldo del pedido después de registrar pago”
“Se canceló venta boutique por devolución del producto”
“Inicio de sesión exitoso”
AUD_IP

IP desde donde se hizo la acción.

AUD_DISPOSITIVO

Información de navegador, equipo o cliente.

--------- ¿Para qué sirve?

Sirve para registrar:

inserciones
actualizaciones
eliminaciones lógicas
eliminaciones físicas, si existieran
inicios de sesión
cierres de sesión
cambios de estado
anulaciones
cancelaciones
cualquier acción importante del sistema

Es decir, una bitácora completa para:

control interno
supervisión
seguridad
auditoría
trazabilidad

--------------- Qué debería guardar

Una tabla de auditoría completa debería responder estas preguntas:

¿quién hizo la acción?
¿cuándo la hizo?
¿sobre qué tabla la hizo?
¿qué registro afectó?
¿qué tipo de acción fue?
¿qué valor tenía antes?
¿qué valor tiene ahora?
¿desde dónde se hizo?
¿por qué se hizo?, si aplica

----------------- Recomendaciones de backend

Cuando registres auditoría:

guardar siempre el usuario
guardar siempre fecha/hora
guardar tabla e id del registro
guardar acción
guardar antes/después en cambios sensibles
guardar descripción humana clara
guardar IP si puedes
guardar user-agent o dispositivo si puedes
