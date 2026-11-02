# Guía UX/UI de Formularios

## Objetivo

Esta guía define el patrón oficial de validaciones, alertas y feedback visual para los formularios del sistema `bellaarte-program`.

Su propósito es:

- mantener una experiencia consistente en todos los módulos
- reducir errores de llenado antes de llegar a la base de datos
- diferenciar con claridad los errores de campo y los errores de proceso
- reutilizar el mismo tono de mensajes en español latino

## Principios base

- La validación del frontend no reemplaza la validación del backend.
- Las restricciones agresivas de entrada se mantienen para proteger la consistencia de la BD.
- El usuario debe entender qué ocurrió, dónde ocurrió y cómo corregirlo.
- Si el error pertenece a un campo, debe mostrarse en el campo.
- Si el error afecta al formulario completo, debe mostrarse en una alerta de proceso.
- Los toasts deben usarse para éxitos y acciones puntuales, no como reemplazo del error del formulario.

## Jerarquía oficial de feedback

### 1. Error de campo

Usar debajo del input mediante `Form.Item` o `form.setFields(...)`.

Aplica para:

- obligatorios
- formato inválido
- mínimos y máximos
- relaciones claras entre backend y campo visible

Ejemplos:

- `Debe ingresar el nombre del rol.`
- `Debe seleccionar el método de pago.`
- `La Cédula de Identidad debe tener al menos 6 caracteres.`

### 2. Error de proceso del formulario

Usar `FormProcessAlert` arriba del formulario o dentro del drawer/modal donde se está editando.

Aplica para:

- conflictos no atribuibles con certeza a un solo campo
- errores de negocio que afectan varias partes del formulario
- respuestas de backend ambiguas

Ejemplos:

- `No fue posible guardar la información del usuario.`
- `No fue posible registrar la venta.`

### 3. Toast

Usar `message.success(...)` o `message.error(...)` solo cuando el usuario no está corrigiendo un formulario abierto o cuando la acción no pertenece a un campo específico.

Aplica para:

- activación o desactivación
- carga de detalle
- reset de contraseña
- cancelación o anulación
- confirmaciones de éxito

## Tono oficial de mensajes

Todos los mensajes deben escribirse en español latino y seguir estas reglas:

- usar verbos directos: `Debe ingresar`, `Debe seleccionar`, `Debe completar`
- evitar mensajes genéricos sin contexto
- evitar inglés en labels, placeholders, errores o ayudas
- usar confirmaciones breves y claras

### Mensajes de error recomendados

- `Debe ingresar ...`
- `Debe seleccionar ...`
- `Debe completar ...`
- `No fue posible ...`

### Mensajes de éxito recomendados

- `Se creó ... correctamente.`
- `Se guardaron los cambios ... correctamente.`
- `Se registró ... correctamente.`
- `... activado correctamente.`
- `... desactivado correctamente.`

## Ayudas preventivas

Cada formulario largo debe incluir `extra` en los campos críticos.

Las ayudas deben:

- ser cortas
- orientar antes del error
- aclarar reglas de negocio importantes
- explicar formatos o consecuencias

Ejemplos:

- `Usa solo letras mayúsculas y guiones bajos.`
- `Si lo dejas vacío, el sistema generará el código automáticamente.`
- `Debe ser mayor al precio de compra para respetar la regla comercial.`
- `Se habilita solo cuando registras un descuento.`

## Placeholders

Reglas:

- usar ejemplos reales y breves
- preferir `Ej.` o frases directas
- no repetir exactamente el label

Ejemplos:

- `Ej. CLI-00001`
- `Ej. 70000000`
- `Selecciona el rol operativo`
- `Busca y selecciona el producto a vender`

## Componentes compartidos oficiales

### `FORM_COMMON_PROPS`

Se usa como configuración base de todos los formularios:

- `layout="vertical"`
- `scrollToFirstError`
- `validateTrigger` uniforme

### `FORM_VALIDATE_MESSAGES`

Define mensajes globales por defecto en español latino para validaciones comunes.

### `FORM_SUBMIT_PROPS`

Base para botones de envío simples.

### `FORM_DRAWER_SUBMIT_PROPS`

Base para botones principales de formularios en drawers o formularios largos.

### `FormProcessAlert`

Componente oficial para errores de proceso en formularios.

### `applyFormApiError`

Helper oficial para:

- leer errores normalizados del backend
- mapearlos a campos cuando sea claro
- devolver error global cuando el problema no pertenece a un solo input

## Reglas para mapear errores del backend

Mapear a campo solo si la relación es inequívoca.

Sí mapear:

- código duplicado de cliente -> `codigo`
- CI duplicado de cliente -> `ci`
- rol deshabilitado -> `role_code`
- método de pago inválido -> `payment_method`
- stock insuficiente -> `quantity`

No mapear automáticamente si el backend no distingue el campo real.

Ejemplo:

- `Ya existe un rol con el mismo codigo o nombre.`

Ese caso debe quedar como error de proceso hasta que el backend lo distinga mejor.

## Botones y acciones

Reglas:

- usar `Button` de Ant Design para envíos y acciones principales
- evitar botones HTML manuales estilizados si existe un patrón compartido
- usar texto consistente

Ejemplos:

- `Crear cliente`
- `Guardar cambios`
- `Registrar venta`
- `Confirmar cancelación`

## Modales y drawers

Reglas:

- si el modal o drawer contiene formulario, debe poder mostrar `FormProcessAlert`
- si el modal solo confirma una acción simple, puede usar `Alert` informativa + toast al finalizar
- al cerrar, limpiar el estado de error del formulario

## Checklist para futuros módulos

Antes de cerrar un nuevo formulario, verificar:

1. Todos los campos obligatorios tienen mensaje explícito en español latino.
2. Los campos críticos tienen `extra` o ayuda preventiva.
3. Los placeholders orientan y no repiten el label sin valor.
4. Los errores de backend atribuibles a campo se pintan en el campo.
5. Los errores ambiguos se muestran con `FormProcessAlert`.
6. Los toasts se usan solo para éxito o acciones no ligadas al formulario abierto.
7. El botón principal usa el patrón compartido.
8. El formulario usa `FORM_COMMON_PROPS`.
9. No se debilitan las restricciones documentadas de la BD o del backend.
10. Toda la mensajería queda en español latino.

## Archivos base de referencia

La implementación oficial de este patrón vive en:

- `frontend/src/components/forms/formConfig.js`
- `frontend/src/components/forms/FormProcessAlert.jsx`
- `frontend/src/components/forms/formErrorUtils.js`

Todo módulo nuevo debe reutilizar estas piezas antes de crear variantes propias.
