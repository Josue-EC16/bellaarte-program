# reconstruir_todo.py
from core.database import engine, Base
import models.models  # <--- Esto registra las clases en la Base
from sqlalchemy import inspect

def construir():
    print("--- 🏗️ RECONSTRUCCIÓN TOTAL ---")
    
    # 1. Borrar todo lo que exista (Para empezar de cero y limpio)
    print("Eliminando tablas viejas (si existían)...")
    Base.metadata.drop_all(bind=engine)
    
    # 2. Crear todo de nuevo
    print("Creando tablas nuevas desde models.py...")
    Base.metadata.create_all(bind=engine)
    
    # 3. Verificación inmediata en el código
    inspector = inspect(engine)
    tablas = inspector.get_table_names()
    
    if tablas:
        print(f"✅ ¡ÉXITO! Tablas creadas físicamente: {tablas}")
        print("Ahora puedes ir a Adminer y deberían aparecer.")
    else:
        print("❌ ERROR: El motor dice que no hay tablas. Revisa la herencia de Base.")

if __name__ == "__main__":
    construir()