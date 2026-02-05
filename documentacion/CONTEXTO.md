### 👰 CONTEXTO DEL PROYECTO: BELLAARTE BOUTIQUE.

El sistema, denominado técnicamente bellaarte-program, nace de la necesidad de gestionar de forma eficiente y segura una boutique de vestidos de novia. No se trata solo de guardar nombres; es una herramienta integral para el control de inventarios, pedidos personalizados y gestión de personal especializado (como modistas y decoradores) bajo una arquitectura robusta de software.

### 🛠️ EL STACK TECNOLÓGICO (Herramientas).

Para este desarrollo, estamos utilizando un conjunto de herramientas de nivel profesional:

- Python: El lenguaje de programación principal, elegido por su versatilidad y potencia en la gestión de datos.

- SQLAlchemy: Actúa como nuestro ORM (Object Relational Mapper). Es el "traductor" que permite que tu código Python hable con la base de datos sin escribir SQL puro manualmente.

- PostgreSQL: El motor de base de datos relacional de nivel empresarial, conocido por su fiabilidad y manejo de datos complejos.

- Laragon: Entorno de desarrollo local en Windows que nos proporciona el servidor de PostgreSQL y la herramienta Adminer para visualizar las tablas.

- Streamlit: La librería que utilizaremos para la Interfaz de Usuario (UI), permitiendo crear una aplicación web rápida y moderna para el personal de la boutique.

- Bcrypt: Herramienta de seguridad para el hashing de contraseñas. Transforma claves como "admin123" en códigos indescifrables para proteger la privacidad del sistema.

### 🏗️ LOGROS DE INGENIERÍA ALCANZADOS.

Hasta ahora, hemos implementado pilares fundamentales que garantizan la integridad del sistema:

- Seguridad por Diseño: Las contraseñas no se guardan como texto; se protegen mediante algoritmos de hash.

- Normalización Automática: Implementamos validadores en los modelos para que todo registro de texto (nombres, cuentas, roles) se guarde automáticamente en MAYÚSCULAS, evitando duplicidad y desorden en los datos.

- Arquitectura Modular: El proyecto está organizado en carpetas (core, models, services, ui, pages) para facilitar el mantenimiento y el crecimiento a futuro.

- Gestión de Roles: El sistema ya distingue entre diferentes niveles de acceso, desde el SUPERADMIN hasta roles operativos como MODISTA o CAJERO(A).
