import psycopg2
from dotenv import load_dotenv
import os

# 1. Cargar las variables desde el archivo .env
load_dotenv()

def probar_conexion():
    try:
        # 2. Intentar la conexión usando las variables de entorno
        conexion = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            port=os.getenv("DB_PORT")
        )
        
        # 3. Si llegamos aquí, la conexión fue exitosa
        print("✅ ¡Conexión Exitosa! Python ya puede hablar con PostgreSQL en Laragon.")
        
        # Cerrar la conexión
        conexion.close()
        
    except Exception as e:
        print(f"❌ Error al conectar: {e}")
        print("Revisa que Laragon esté encendido y tus credenciales en el .env sean correctas.")

if __name__ == "__main__":
    probar_conexion()