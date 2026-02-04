from database import engine, Base
import models # Esto es vital para que Base las reconozca

print("--- 🔨 FORZANDO CREACIÓN ---")
try:
    # Esto creará las tablas físicamente en la conexión que define tu .env
    Base.metadata.create_all(bind=engine)
    
    # Verificación inmediata por código
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tablas = inspector.get_table_names()
    
    print(f"Puerto detectado en conexión: {engine.url.port}")
    print(f"Base de datos: {engine.url.database}")
    print(f"Tablas encontradas por Python: {tablas}")
    
except Exception as e:
    print(f"❌ Error al crear: {e}")