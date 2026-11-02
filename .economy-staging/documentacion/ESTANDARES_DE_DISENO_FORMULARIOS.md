# ESTÁNDARES DE DISEÑO Y MAQUETACIÓN EN FORMULARIOS

Este documento establece las reglas obligatorias sobre cómo estructurar y alinear los elementos de un formulario (específicamente utilizando Ant Design u otros sistemas de componentes web), asegurando que la interfaz no se descuadre ("se parta") ante la aparición de alertas de error en tiempo real.

---

## 1. El Problema del Descuadre Visual

Al crear formularios donde dos o más campos comparten la misma fila (por ejemplo "Nombres" y "Apellidos" ó "Celular" y "Cédula de Identidad"), es común utilizar contenedores flexbox genéricos como `<Space style={{ display: 'flex' }}>`.

### ¿Por qué NO usar `<Space>` para columnas de inputs?
El componente `<Space>` de Ant Design centra y alinea los elementos a nivel vertical por defecto (o depende del flex-basis directo).
Si un usuario ingresa información incorrecta, la validación del sistema lanzará un mensaje de error **debajo** de la caja de texto. 
Esto hace que ese campo en específico "crezca" hacia abajo.
Como están en un `<Space>`, el contenedor flexbox intentará compensar la altura total, empujando o desfasando visualmente la caja de texto compañera que NO tiene error. Esto crea una interfaz asimétrica, partida y desordenada.

---

## 2. La Solución: El Sistema de Grillas (Grid)

Para maquetar distribuciones lado a lado se **debe emplear estrictamente el sistema de grillas nativo** de la UI, en este caso los componentes `<Row>` y `<Col>`.

### ¿Por qué usar `<Row>` y `<Col>`?
El sistema Grid está diseñado predeterminadamente para que los elementos dentro de sus celdas compartan una **alineación superior fija**. 
Si uno de los elementos crece verticalmente debido a una alerta de error de validación, la columna correspondiente se expandirá aisladamente hacia abajo. La caja de texto adyacente permanecerá fija y alineada simétricamente en la parte superior sin verse afectada.

---

## 3. Guía de Ejecución

Esta es la forma correcta y única de implementar múltiples campos en una sola fila.

### ❌ Forma Incorrecta (Prohibido)
Nunca alinear los `Form.Item` usando `Space` si estos pueden generar alertas:

```jsx
// ESTO GENERARÁ DESCUADRE CUANDO EXISTA UN ERROR
<Space style={{ display: 'flex' }} size={12}>
  <Form.Item label="Celular" name="celular" style={{ flex: 1 }}>
    <Input />
  </Form.Item>
  <Form.Item label="Cédula de Identidad" name="ci" style={{ flex: 1 }}>
    <Input />
  </Form.Item>
</Space>
```

### ✅ Forma Correcta (Obligatorio)
Utiliza `<Row gutter={...}>` para la fila y `<Col span={...}>` para dictar el ancho de los elementos. El grid de Ant Design es de 24 columnas, por lo que `span={12}` los divide exactamente a la mitad.

```jsx
// FORMA CORRECTA QUE RESPETA EL DISEÑO AUNQUE EXISTAN ALERTAS
<Row gutter={12}>
  <Col span={12}>
    <Form.Item label="Celular" name="celular">
      <Input />
    </Form.Item>
  </Col>
  <Col span={12}>
    <Form.Item label="Cédula de Identidad" name="ci">
      <Input />
    </Form.Item>
  </Col>
</Row>
```

## 4. Distribución de Alertas en el Diseño

- **Espaciado Inteligente:** Los formularios deben prever el espacio para la aparición de alertas; utilizar `<Row gutter={12}>` (o mayor) asegura no solo separación lateral (eje X), sino armonía visual.
- **Evitar saltos de Layout Shift (CLS):** La interfaz no debe encoger otros paneles cuando un texto de error aparece. Mantén los contenedores padres flexibles (`overflow-y: auto` o scroll predefinido, usando Modales y Drawers para los registros).
- **Una única vía:** Al diseñar con la grilla, permitimos que el formulario de Ant Design maneje la etiqueta (label), el campo de entrada (input) y el contenedor de errores nativos como un bloque atómico.
