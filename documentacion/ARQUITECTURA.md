Esta es una Arquitectura Modular Orientada a Servicios, una estructura profesional que evoluciona el patrón MVC (Modelo-Vista-Controlador) para adaptarlo a las necesidades de Python y Streamlit.

A continuación, presento el desglose técnico para tu documentación:

🏛️ Descripción General de la Arquitectura.

El objetivo de esta estructura es la Separación de Responsabilidades. Cada carpeta actúa como una "capa" independiente, lo que permite que, si cambias algo en la base de datos, no tengas que reescribir toda la interfaz visual.

📂 Desglose de Carpetas y Documentos.

1. core/ (El Cerebro)
   Contiene la lógica central y la infraestructura de la aplicación.
   Es el "corazón" técnico del sistema. Contiene las configuraciones globales y conexiones base.

core/database.py: Configura la conexión a PostgreSQL. Es el puente entre tu código Python y la base de datos.
core/config.py: (Opcional, pero recomendado) Maneja variables de entorno y configuración global.
core/security.py: (Futuro) Manejará el cifrado de contraseñas y la autenticación.

2. models/ (La Memoria)
   Define la estructura de los datos. Cada archivo .py aquí es una tabla de la base de datos.
   Define la estructura de los datos (El Modelo). Es el plano de construcción de tus tablas en PostgreSQL.

models/models.py: Define las tablas Rol y User.
models/clientes.py: (Futuro) Definirá la tabla de clientes.
models/productos.py: (Futuro) Definirá la tabla de productos.

3. pages/ (La Cara)
   Contiene la interfaz de usuario. Como usamos Streamlit, aquí están los archivos de las páginas.
   Contiene la "Lógica de Negocio" (El Controlador). Aquí es donde se decide qué hacer con los datos antes de guardarlos.

4. assets/ (Los Recursos)
   Contiene los recursos estáticos de la aplicación.
   Almacena recursos estáticos que no cambian y son de acceso público para la aplicación.

assets/images/: (Futuro) Imágenes de los productos.
assets/docs/: (Futuro) Archivos que el usuario final necesite descargar, como guías de usuario o plantillas de documentos.

5. services/ (Las Manos)
   Contiene la lógica de negocio. Son las funciones que manipulan los datos.
   Contiene la "Lógica de Negocio" (El Controlador). Aquí es donde se decide qué hacer con los datos antes de guardarlos.

services/auth_service.py: (Futuro) Lógica para iniciar sesión, cerrar sesión y verificar permisos.
services/inventario_service.py: (Futuro) Funciones para agregar/quitar productos.

6. app.py (La Cara)
   Contiene la interfaz de usuario. Como usamos Streamlit, aquí están los archivos de las páginas.

app/login.py: La pantalla de inicio de sesión.
app/dashboard.py: El panel principal.
app/inventario.py: La vista de productos.
app/clientes.py: La vista de clientes.

7. scripts/ (Las Herramientas)
   Scripts auxiliares para tareas de mantenimiento.
   Herramientas de soporte y mantenimiento para el desarrollador.

scripts/seed_data.py: Script para poblar la base de datos con datos iniciales.
scripts/backup_manager.py: (Futuro) Script para respaldar la base de datos.

8. .env y .gitignore (La Seguridad)
   .env: Archivo secreto que contiene las contraseñas y credenciales de la base de datos. NO debe subirse a GitHub.
   .gitignore: Lista de archivos y carpetas que Git debe ignorar (como .env, backups/, **pycache**/).

9. requirements.txt (Las Dependencias)
   Contiene la lista de todas las librerías externas que necesita el proyecto para funcionar.

10. ui/ (La Interfaz)
    Contiene la interfaz de usuario. Como usamos Streamlit, aquí están los archivos de las páginas.
    Contiene la "Lógica de Negocio" (El Controlador). Aquí es donde se decide qué hacer con los datos antes de guardarlos.
    Define la estética y componentes visuales reutilizables.
