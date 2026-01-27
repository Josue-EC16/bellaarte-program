import os
import subprocess
from datetime import datetime
from dotenv import load_dotenv

# 1. Cargar configuración de seguridad
load_dotenv()

def ejecutar_respaldo():
    # Configuración desde el .env
    DB_USER = os.getenv("DB_USER")
    DB_NAME = os.getenv("DB_NAME")
    DB_PASS = os.getenv("DB_PASS")
    DB_HOST = os.getenv("DB_HOST")
    
    # 2. Crear carpeta de backups si no existe
    folder_name = "backups"
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
        print(f"📁 Carpeta '{folder_name}' creada.")

    # 3. Generar nombre de archivo con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(folder_name, f"backup_{DB_NAME}_{timestamp}.sql")

    # 4. Configurar la contraseña para pg_dump (Variable de entorno temporal)
    os.environ['PGPASSWORD'] = DB_PASS

    # 5. Comando pg_dump
    # Nota: Asegúrate de que la ruta de PostgreSQL esté en el PATH de Windows
    comando = [
        'pg_dump',
        '-h', DB_HOST,
        '-U', DB_USER,
        '-f', backup_file,
        DB_NAME
    ]

    try:
        print(f"⏳ Iniciando respaldo de {DB_NAME}...")
        subprocess.run(comando, check=True)
        print(f"✅ Respaldo completado con éxito: {backup_file}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al ejecutar pg_dump: {e}")
    except Exception as e:
        print(f"❌ Ocurrió un error inesperado: {e}")
    finally:
        # Limpiar la contraseña de la memoria por seguridad
        if 'PGPASSWORD' in os.environ:
            del os.environ['PGPASSWORD']

if __name__ == "__main__":
    ejecutar_respaldo()