# REGLAS DE INTEGRIDAD Y MANEJO DE DATOS (CRUD)

Este documento establece las directrices obligatorias para la implementación de operaciones CRUD (Crear, Leer, Actualizar, Borrar) en el sistema BellaArte, garantizando que la comunicación entre el Frontend (React/AntD) y el Backend (FastAPI/Pydantic) sea fluida y libre de errores silenciosos.

---

## 1. Mapeo de Nombres de Campos (Frontend vs Backend)

Es CRÍTICO que el atributo `name` en los componentes `<Form.Item>` coincida EXACTAMENTE con el nombre esperado por el esquema de Pydantic en el Backend.

- **Error común:** Usar `name="name"` en el frontend cuando el backend espera `nombre`.
- **Consecuencia:** El backend ignora el campo o lanza un error de "campo requerido" (422), y los datos no se guardan en la base de datos.
- **Regla:** Siempre verifica los archivos en `backend/app/schemas/` antes de definir los nombres en el formulario.

---

## 2. Manejo Global de Errores de Validación (422 Unprocessable Entity)

El backend utiliza Pydantic para validar los datos. Cuando falla una validación (ej. un campo es muy corto o falta un dato obligatorio), el backend responde con un código **422** y un array complejo de errores.

### Interceptor del `apiClient`

Hemos configurado de forma global en `frontend/src/api/client.js` un interceptor que procesa estos errores automáticamente:

```javascript
// Este código ya está en apiClient.js
if (
  error.response?.status === 422 &&
  Array.isArray(error.response.data.detail)
) {
  const msgs = error.response.data.detail.map((err) => {
    const field = err.loc[err.loc.length - 1]; // Obtiene el nombre del campo fallido
    return `[${field}] ${err.msg}`;
  });
  // Convierte el array en un string legible para message.error()
  error.response.data.detail = `Errores de validación: ${msgs.join(", ")}`;
}
```

**Regla de Oro:** Siempre usa el bloque `catch` en tus peticiones para mostrar este mensaje al usuario:

```javascript
try {
  await apiClient.post("/ruta", values);
} catch (error) {
  // error.response.data.detail ahora contiene un texto amigable gracias al interceptor
  message.error(error.response?.data?.detail || "Error desconocido");
}
```

---

## 3. Normalización de Campos Numéricos (`InputNumber`)

Los componentes `<InputNumber>` de Ant Design pueden enviar valores vacíos o nulos que causan conflictos si se procesan incorrectamente en el `normalize` del `Form.Item`.

### El problema del String Vacío (`""`)

Si un `normalize` devuelve una cadena vacía `""` para un campo que el Backend espera como un número (Float/Int), la petición fallará. Pydantic no acepta `""` como un número válido.

### La Solución Correcta

Se debe asegurar que si el campo no tiene valor, devuelva `null` de forma explícita.

```jsx
// EJEMPLO OBLIGATORIO PARA CAMPOS NUMÉRICOS
<Form.Item
  label="Precio"
  name="precio"
  normalize={(value) => {
    // Si el usuario borra el dato, devolver null o el valor vacío correcto
    if (value === null || value === undefined || value === "") return null;
    // Realizar limpieza (eliminar letras/espacios) y retornar
    return value.toString().replace(/[^0-9.]/g, "");
  }}
>
  <InputNumber />
</Form.Item>
```

---

## 4. Visualización de Detalles (Modo "Ver")

Para garantizar que el usuario vea la información completa de cada campo y actualizada de la Base de Datos (referente a la tabla que corresponden esos datos), se deben seguir estas reglas en el botón de acción "Ver":

### A. Carga de Datos desde el Backend

**NUNCA** utilices el objeto `record` que viene directamente de la tabla para llenar el visualizador de detalles. Las listas/tablas suelen usar esquemas resumidos (resúmenes) para ahorrar ancho de banda.

- **Acción:** Crea una función `openView(record)` que realice una petición `GET` específica al endpoint del item (ej. `apiClient.get('/clientes/' + record.id)`). Esto asegura que campos largos como "Observaciones" o "Dirección" se muestren completos.

### B. Persistencia Visual (Cierre de Modales)

Para evitar que el usuario pierda de vista la información por un clic accidental fuera del área de contenido, todos los Modales de detalle y Drawers de formulario deben tener bloqueado el cierre por clic en la máscara.

- **Propiedad:** `maskClosable={false}`.

```jsx
<Modal
  title="Detalles"
  open={!!selected}
  onCancel={() => setSelected(null)}
  maskClosable={false} // OBLIGATORIO
>
  {/* Contenido */}
</Modal>
```

---

## 5. Checklist para Nuevos Módulos CRUD

Al crear un nuevo módulo, verifica estos puntos:

1. [ ] **Backend Schema:** ¿Qué campos son obligatorios y cómo se llaman? (`backend/app/schemas/`)
2. [ ] **Frontend Names:** ¿Los `name` del `Form.Item` coinciden con el esquema?
3. [ ] **Normalización:** ¿Los campos numéricos devuelven `null` si están vacíos?
4. [ ] **Feedback 422:** ¿El código de guardado tiene un `message.error` que lea el `detail` de la respuesta?
5. [ ] **Integridad en Detalles:** ¿El botón "Ver" pide los datos frescos al Backend en lugar de usar los de la tabla?
6. [ ] **Seguridad de Cierre:** ¿Los Modales tienen `maskClosable={false}`?
7. [ ] **Audit Logs:** ¿El servicio del backend registra el evento (`register_audit_event`) y hace `db.commit()`?

---

> [!IMPORTANT]
> Seguir estas reglas evita el error de "darle clic al botón y que no pase nada". Si un guardado falla, ahora el sistema siempre te dirá EXACTAMENTE qué campo está mal.
