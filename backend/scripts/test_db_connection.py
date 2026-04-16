from core.database import engine
from sqlalchemy import text

def verificar_conexion():
    try:
        # Intentamos conectar y ejecutar una consulta simple de sistema
        with engine.connect() as connection:
            # Consultamos al motor de PostgreSQL su nombre y versión
            result = connection.execute(text("SELECT current_database(), version();"))
            db_name, db_version = result.fetchone()
            
            print("--- 💡 REPORTE DE CONEXIÓN ---")
            print(f"✅ Conexión exitosa!")
            print(f"📂 Base de Datos actual: {db_name}")
            print(f"⚙️  Versión de Postgres: {db_version}")
            print("------------------------------")
            
    except Exception as e:
        print("--- ❌ ERROR DE CONEXIÓN ---")
        print(f"No se pudo conectar a PostgreSQL.")
        print(f"Error técnico: {e}")
        print("----------------------------")

if __name__ == "__main__":
    verificar_conexion()