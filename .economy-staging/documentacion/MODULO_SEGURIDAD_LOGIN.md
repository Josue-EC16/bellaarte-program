# Módulo de Seguridad y Accesos - BellaArte Boutique

Este documento unifica y actualiza todas las especificaciones operativas, técnicas y de seguridad del sistema BellaArte Boutique. Representa la versión definitiva del núcleo de gestión de usuarios, roles y autenticación.

## 1. Objetivo del Módulo
Proveer una base sólida, segura y automatizada para el control de acceso al sistema, garantizando la integridad de los datos y la trazabilidad de cada acción mediante auditoría.

---

## 2. Arquitectura de Seguridad

*   **Autenticación**: Basada en JWT (JSON Web Tokens).
    *   **Access Token**: Tiempo de vida corto, enviado en cabecera Bearer.
    *   **Refresh Token**: Almacenado en Cookie `HttpOnly` para mayor seguridad.
*   **Autorización**: Implementada con Casbin utilizando el modelo RBAC (Control de Acceso Basado en Roles).
*   **Cifrado**: Contraseñas almacenadas irreversibles mediante **Bcrypt** con salting dinámico.
*   **Auditoría**: Registro automático de eventos (Logins, Cambios de clave, Creaciones, Ediciones).

---

## 3. Flujos de Gestión de Usuarios

### 3.1. Creación Automática de Credenciales
Para simplificar la administración y reducir errores humanos, el sistema autogenera los accesos basándose en la identidad del colaborador:

*   **Nombre de Usuario**: Formado por la primera letra del Nombre + Primera letra del Apellido Paterno + CI (Ej: `ME12345678`).
    *   *Nota*: Se almacena y valida estrictamente en **MAYÚSCULAS**.
*   **Contraseña Temporal**: Es exactamente el número de Cédula de Identidad (CI).
*   **Validación de Unicidad**: El sistema impide duplicados de CI, Correo Electrónico y Nombre de Usuario.

### 3.2. Notificación por Correo (Servicio SMTP)
Al crear o actualizar un usuario (si nunca ha ingresado), el sistema despacha un correo de bienvenida profesional utilizando **Gmail SMTP con SSL (Puerto 465)**.

*   **Diseño HTML**: Plantilla elegante con los colores corporativos de BellaArte.
*   **Logo Embebido**: El logo de la empresa se adjunta directamente al correo para garantizar su visualización sin depender de servidores externos.
*   **Contenido**: Incluye el nombre del colaborador, sus credenciales exactas (Usuario y Clave) y las instrucciones de seguridad.

### 3.3. Primer Inicio de Sesión y Seguridad
*   **Cambio Obligatorio**: Toda cuenta nueva nace con la bandera `must_change_password = true`. El sistema bloquea la navegación hasta que el usuario defina su propia clave personal.
*   **Complejidad de Contraseña (Regex)**: Se exige un mínimo de 8 caracteres, incluyendo al menos 1 Mayúscula, 1 Minúscula, 1 Número y 1 Carácter Especial.
*   **Sensibilidad estricta**: El login es sensible a mayúsculas y minúsculas para el nombre de usuario y la contraseña por motivos de seguridad industrial.

---

## 4. Gestión Administrativa (Panel Admin)

### 4.1. CRUD de Roles
*   Permite definir nombres y códigos técnicos de roles (EJ: `INV_TALLER`, `MODISTA`).
*   Control de estado: No se puede desactivar un rol si todavía tiene cuentas asociadas activas.

### 4.2. CRUD de Usuarios
*   Formulario unificado: Se editan datos personales (`Usuario`) y permisos de sistema (`Cuenta`) en una sola operación.
*   **Re-envío de Correo**: Si un administrador corrige el correo de un usuario que aún no ha iniciado sesión, el sistema detecta el cambio y re-envía automáticamente las credenciales al nuevo destino.

### 4.3. Restablecimiento de Clave
*   **Acción**: Botón "Reset Clave" en la lista de usuarios.
*   **Flujo**: Abre un Modal de confirmación (Ant Design). Al confirmar, la contraseña se resetea automáticamente al número de CI del usuario y se le vuelve a marcar el cambio obligatorio de clave.

---

## 5. Auditoría del Sistema
Se registran las siguientes acciones para trazabilidad:
*   `LOGIN_SUCCESS` / `LOGIN_FAILED`: Intentos de acceso.
*   `USER_CREATED` / `USER_UPDATED`: Cambios en personal.
*   `PASSWORD_CHANGED`: Cuando un usuario cambia su clave temporal por una propia.
*   `PASSWORD_RESET`: Cuando un administrador fuerza el reseteo de una cuenta.
*   `ACCOUNT_STATUS_CHANGED`: Activación/Desactivación de accesos.

---

## 6. Configuración Técnica (Variables de Entorno)

El sistema requiere las siguientes variables en el archivo `.env`:

```env
# Base de Datos
DATABASE_URL=...

# Seguridad JWT
JWT_SECRET_KEY=...
ACCESS_TOKEN_MINUTES=30

# Correo (Gmail SMTP)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=465
SMTP_USERNAME=tu_correo@gmail.com
SMTP_PASSWORD=tu_app_password_de_google
```

---

## 7. Roles Base Pre-cargados
1.  **ADMIN**: Control total del sistema.
2.  **INV_TALLER**: Gestión de telas e insumos.
3.  **INV_BOUTIQUE**: Gestión de prendas terminadas.
4.  **CAJA**: Control de ventas y pagos.
5.  **MODISTA**: Visualización de pedidos y órdenes de trabajo.
