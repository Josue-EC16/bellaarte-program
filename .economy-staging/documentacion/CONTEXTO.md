### 👰 CONTEXTO DEL PROYECTO: BELLAARTE BOUTIQUE.

El sistema, denominado técnicamente bellaarte-program, nace de la necesidad de gestionar de forma eficiente y segura una boutique de vestidos de novia. No se trata solo de guardar nombres; es una herramienta integral para el control de inventarios, pedidos personalizados y gestión de personal especializado (como modistas y decoradores) bajo una arquitectura robusta de software.

### 🛠️ EL STACK TECNOLÓGICO (Herramientas).

Para esta fase de producción, el sistema ha evolucionado hacia un stack desacoplado de alto rendimiento:

- Frontend (React 19 & Vite 6): Utilizamos la versión más reciente de React (diciembre 2025) para construir una interfaz de usuario dinámica, rápida y segura. Vite actúa como el motor de desarrollo de última generación.

- Backend (FastAPI & Python 3.14): El "cerebro" del sistema es una API asíncrona construida con FastAPI, diseñada para manejar múltiples peticiones de la boutique simultáneamente con una latencia mínima.

- Laragon 6.0 Entorno de desarrollo local en Windows que nos proporciona el servidor de PostgreSQL y la herramienta Adminer para visualizar las tablas.

- Gestor de Paquetes (pnpm 10): Implementamos pnpm para la gestión de dependencias del frontend, optimizando el espacio en disco y garantizando instalaciones deterministas.

- SQLAlchemy 2.0: Mantenemos este ORM avanzado como el traductor principal entre nuestros modelos de Python y la base de datos, aprovechando sus capacidades de tipado fuerte.

- PostgreSQL 17: El motor de base de datos relacional más avanzado del mercado, gestionado localmente a través de Laragon 6.0 para un entorno de desarrollo robusto en Windows.

- Seguridad (Bcrypt & JWT): Además del hashing de contraseñas con Bcrypt, el sistema ahora implementa JSON Web Tokens (JWT) para gestionar sesiones seguras entre React y la API.

- AccessControl Casbin (PyCasbin).Casbin: Es un framework de control de acceso poderoso. Te permite definir un modelo RBAC (Control de Acceso Basado en Roles) para separar quién puede ver qué:
  - Vendedora (Boutique): Puede crear contratos y registrar medidas.
  - Administrador (Tú/Dueña): Acceso total a los KPIs financieros de ingresos y egresos.
- FastAPI Users: Es otra librería muy popular que ya trae integrado el manejo de registros, login (JWT) y roles de forma sencilla y segura.

### 🏗️ LOGROS DE INGENIERÍA ALCANZADOS.

Con la nueva arquitectura, hemos consolidado pilares de nivel empresarial:

- Desacoplamiento Total (Frontend/Backend): La interfaz y la lógica de negocio son ahora independientes. Esto permite que el sistema crezca o cambie de diseño sin afectar la integridad de los datos.

- Seguridad por Diseño (Zero-Trust): Implementamos validación de esquemas con Pydantic en el backend y protección contra vulnerabilidades detectadas en diciembre de 2025 mediante el uso de React 19.0.0.

- Normalización Estricta de Datos: Se mantienen los validadores automáticos para que registros como nombres, roles y estados se almacenen siempre en MAYÚSCULAS, garantizando la limpieza de la base de datos.

- Gestión de Versiones Profesional: Implementamos el uso de fnm para el control de versiones de Node.js y entornos virtuales (venv) para Python, asegurando que el proyecto sea reproducible en cualquier máquina de la boutique.

- Arquitectura Orientada a Servicios: El proyecto está organizado en una estructura de carpetas modular (backend/ y frontend/) que facilita la futura implementación de contenedores con Docker.
