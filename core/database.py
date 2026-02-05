import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# 1. Cargar variables de entorno del archivo .env
load_dotenv()

# 2. Configuración de la URL de conexión
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# Construcción de la URL para PostgreSQL
SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# 3. Crear el motor de la base de datos (Engine)
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# 4. Configurar la fábrica de sesiones para interactuar con la DB
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 5. Base para los modelos (Sintaxis moderna de SQLAlchemy 2.0)
Base = declarative_base()

# 6. Función para inicializar las tablas físicamente
def create_tables():
    """
    Importa los modelos y crea las tablas en PostgreSQL.
    El import de 'models' debe estar dentro de esta función para evitar
    errores de importación circular y asegurar que las tablas se registren.
    """
    try:
        import models 
        print("--- 🛠️  Sincronizando Base de Datos ---")
        
        # Crea las tablas que no existen basándose en los modelos
        Base.metadata.create_all(bind=engine)
        
        print("✅ Tablas verificadas/creadas exitosamente en PostgreSQL.")
    except Exception as e:
        print(f"❌ Error al intentar crear las tablas: {e}")

if __name__ == "__main__":
    create_tables()