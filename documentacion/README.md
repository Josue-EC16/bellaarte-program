# BELLAARTE Boutique - Sistema de Gestión

Este sistema ha evolucionado de un monolito en Streamlit a una Arquitectura Desacoplada profesional, separando el Frontend (React) del Backend (FastAPI) para garantizar escalabilidad y seguridad.

### 🏛️ ESTRUCTURA DEL PROYECTO

/backend: API construida con FastAPI 0.115.6 y Python 3.14.2.

/frontend: Interfaz de usuario con React 19.0.0 y Vite 6.0.

/documentacion: Detalles técnicos y manuales del sistema.

### 🛠️ REQUISITOS PREVIOS (Versiones Dic-2025)

Para que el sistema funcione correctamente en Bolivia, asegúrate de tener:

- Node.js: v22.12.0 (Gestionado con fnm).

- pnpm: v10.33.0 (Gestor de paquetes del frontend).

- Python: v3.14.2 (Con entorno virtual activado).

- Laragon: v6.0 con PostgreSQL 17.

### 🚀 GUÍA DE INICIO RÁPIDO

1. Preparar la Base de Datos (Laragon)
   Enciende Laragon y presiona "Start All".

Asegúrate de que PostgreSQL esté corriendo en el puerto 5432.

2. Levantar el Backend (El Cerebro)
   Abre una terminal en la raíz y ejecuta:

PowerShell
cd backend
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
La API estará disponible en: http://localhost:8000.

3. Levantar el Frontend (La Cara)
   Abre una segunda terminal (sin venv de Python) y ejecuta:

PowerShell
cd frontend
pnpm install
pnpm run dev
El sistema será visible en: http://localhost:5173.

### 🔧 MANTENIMIENTO E INGENIERÍA

Sincronización de Base de Datos (flujo oficial)
Cada vez que agregues o modifiques modelos ORM en `backend/app/models/`, la evolución de la base de datos se realiza con Alembic:
PowerShell
cd backend
.\venv\Scripts\activate
python -m alembic -c alembic.ini upgrade head
Seeds (roles/admin/políticas):
PowerShell
python scripts/seed_security.py

- Automatización: Configura el Programador de Tareas para ejecutar backup_manager.py cada noche a las 11:00 PM.

Ejecución de Scripts Globales
Para ejecutar herramientas de soporte desde la raíz del backend, usa siempre el parámetro -m para respetar los módulos:

PowerShell
python -m scripts.seed_data
🔒 SEGURIDAD Y REGLAS DE ORO
Variables de Entorno: Nunca subas el archivo .env a GitHub. Contiene las credenciales de la base de datos.

- GitIgnore: Verifica que existan archivos .gitignore tanto en la raíz como en /frontend para evitar subir carpetas pesadas como node_modules o venv.

- Hashing: Las contraseñas de los empleados (Modistas, Cajeros) siempre se procesan con Bcrypt 4.2.0 antes de entrar a la base de datos.

### Desarrollado por: Marcelo Josue Escobar Chipana - Ingeniería de Sistemas
