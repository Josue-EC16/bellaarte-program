# BELLAARTE Boutique -  Sistema de Gestión 

### GUÍA DE INICIO RÁPIDO.

- ACTIVAR EL ENTORNO VIRTUAL, ABRE LA TERMINAL EN LA CARPETA DEL PROYECTO Y EJECUTA:

.\venv\Scripts\activate

- INSTALAR DEPENDENCIAS (solo la primera vez):

pip install -r requirements.txt

- EJECUTAR LA APLICACIÓN:

streamlit run app.py

### ¿Cómo trabajarás de ahora en adelante?

- Enciendes Laragon (Botón "Start All").

- Activas tu venv en la terminal de Cursor.

- Ejecutas streamlit run app.py.

- ¡Empiezas a digitalizar BELLAARTE!

--- A CONSIDERAR PARA EL BACKUP ---

2. Consideraciones de Ingeniería para el Mantenimiento
A. El PATH de PostgreSQL
Para que este script funcione, Windows debe saber dónde está el ejecutable pg_dump.

Como usas Laragon, la ruta suele ser: C:\laragon\bin\postgresql\postgresql-14.5\bin.

Debes agregar esa ruta a las Variables de Entorno de tu sistema (en la sección Path).

B. Automatización Total (Nivel Producción)
Una vez que el sistema esté en la laptop de la boutique, no querrás correr este script a mano. Como ingeniero, puedes usar el Programador de Tareas de Windows:

Crea una tarea básica que se ejecute cada noche a las 11:00 PM.

La acción será: python C:\laragon\www\bellaarte-program\backup_manager.py.

¡Listo! Tendrás un respaldo diario sin mover un dedo.

C. Estrategia de Almacenamiento
Local: Los backups se quedan en tu carpeta /backups.

Nube: Una técnica común es sincronizar esa carpeta con Google Drive o Dropbox. Así, si la laptop de la boutique falla físicamente, los datos de BellaArteBoutique están a salvo en la nube.

3. Seguridad del Repositorio
Recuerda que tu archivo .gitignore debe incluir la carpeta backups/. Nunca subas tus respaldos con datos reales de clientes a GitHub, incluso si el repositorio es privado. Es una regla de oro de ciberseguridad.