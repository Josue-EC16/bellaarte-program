# GUÍA DE VALIDACIONES Y USABILIDAD - BellaArte Boutique

Este documento establece los estándares obligatorios para la creación de formularios en el sistema. El objetivo es garantizar la limpieza de los datos (normalización) y mejorar la experiencia del usuario (usabilidad).

---

## 1. Instrucciones Generales

### A. Normalización de Datos (Propiedad `normalize`)

Cada campo debe interceptar la entrada del usuario para garantizar que los datos se guarden en el formato correcto antes de ser procesados por el backend.

- **Forzar Mayúsculas:** Todo texto (nombres, direcciones, zonas) debe convertirse automáticamente a MAYÚSCULAS.
- **Restricción de Caracteres:**
  - Campos de nombre, apellido paterno o materno: Solo letras y espacios.
  - Campos numéricos: Solo números (sin puntos, comas ni espacios).
  - Campos de identidad (CI): Letras y números, sin espacios.
  - Campos de correo: Forzar minúsculas y sin espacios.
  - Campos númericos: Solo números (sin puntos, comas ni espacios).
  - Campos de texto: Solo letras y espacios.
  - Campos de medidas: Solo números y puntos (sin comas ni espacios).
  - Campos monetarios (dinero): Solo números y puntos (sin comas, ni espacios, no números negativos, no caracteres especiales) y mostrar todo en Bolivianos (Bs).
  - Campos de Códigos: Debe validarse que no se ingresen códigos iguales a otros códigos ya existentes (que siga la regla de UNIQUE).
  - Campos de tallas: Solo números y puntos (sin comas ni espacios).

### B. Guía Visual (Propiedad `placeholder`)

Ningún campo debe estar vacío de contexto. Cada `Form.Item` debe incluir un `placeholder` que explique brevemente qué información se espera que se llene (Ej. "Ingresar el nombre o nombres del cliente" o "Ej. 70000000")
Es decir brindar una información de lo que se debe llenar en el campo de manera general y si es el caso y aplica brindar un ejemplo de lo que se debe llenar en el campo.

---

## 2. Ejemplo de Implementación (Módulo de Usuarios)

A continuación se detallan las reglas aplicadas en el CRUD de Usuarios, las cuales sirven como plantilla para futuros módulos:

| Campo                   | Restricción Técnica (Regex)              | Acción de Usabilidad (Placeholder)           |
| :---------------------- | :--------------------------------------- | :------------------------------------------- |
| **Nombres**             | `/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g` + Uppercase | "Introducir el o los Nombres del Usuario"    |
| **Apellido Paterno**    | `/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g` + Uppercase | "Introducir el Apellido Paterno del Usuario" |
| **Cédula de Identidad** | `/[^0-9A-Z]/g` + Uppercase               | "Ej. 1234567"                                |
| **Celular**             | `/[^0-9]/g` (Solo números)               | "Ej. 70000000"                               |
| **Correo**              | Sin espacios + Lowercase + `@gmail.com`  | "usuario@gmail.com"                          |
| **Zona**                | Uppercase                                | "Ej. ZONA SUR"                               |
| **Dirección**           | Uppercase                                | "Descripción detallada de la dirección"      |
| **Username**            | Sin espacios (normalmente heredado)      | "Nombre de acceso al sistema"                |

### Ejemplo de código (Ant Design):

```javascript
<Form.Item
  label="Nombres"
  name="nombres"
  rules={[{ required: true }]}
  normalize={(value) =>
    (value || "").replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, "").toUpperCase()
  }
>
  <Input placeholder="Introducir el o los Nombres del Usuario" />
</Form.Item>
```

---

## 3. Reglas Específicas del Correo

Para el dominio `@gmail.com`, se deben aplicar tres niveles de control:

1.  **Pre-llenado:** Al abrir un formulario de creación, el campo debe iniciar con el valor `@gmail.com`.
2.  **Limpieza:** Eliminar espacios y forzar minúsculas.
3.  **Validación de Patrón:** Usar la regla `pattern: /^[a-zA-Z0-9._%+-]+@gmail\.com$/`.

---

## 4. Reglas Específicas sobre campos donde se ingresen valores monetarios.

- Todo dato se debe mostrar estrictamente en bolivianos (Bs).
- Se debe validar que no se ingresen caracteres no numericos y números negativos no estan permitidos.

## 5. MANDATO DE DESARROLLO

> [!IMPORTANT]
> **ESTE FORMATO ES OBLIGATORIO.**
> Cada vez que se desarrolle un nuevo módulo, submódulo o CRUD en el sistema (Ventas, Inventario Taller, Pedidos, etc.), se debe aplicar estrictamente esta política de normalización de datos y placeholders. No se aceptarán campos de texto "libres" sin validación de caracteres o sin guía de usuario.

## 6. FORMATO Y REGLAS DE ALERTAS EN LOS FORMULARIOS POR LLENAR INCORRECTAMENTE O NO LLENAR EL CAMPO.

- Las alertas que manda el sistema deben ser específicas del campo que no se esta llenando o se esta llenando incorrectamente.
- Las alertas deben ser únicas por campo, no pueden generalizarse, por ejemplo no se puede poner una alerta que diga "Por favor llene todos los campos" o "El campo CI o Correo Electrónico ya están en uso", deben ser específicas como por ejemplo "El CI ya esta en uso" o "El campo Correo Electrónico ya esta en uso".
- Las alertas deben ser claras y concisas, no deben ser ambiguas.
