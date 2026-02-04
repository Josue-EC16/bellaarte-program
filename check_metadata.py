from database import Base
# IMPORTANTE: Debemos importar los modelos para que se "registren"
import models 

print("--- 🔍 INSPECCIÓN DE METADATOS ---")
tablas_detectadas = Base.metadata.tables.keys()

if not tablas_detectadas:
    print("❌ SQLAlchemy NO ha detectado ninguna clase/tabla.")
    print("Revisa que tus clases en models.py hereden de 'Base'.")
else:
    print(f"✅ Tablas listas para crear: {list(tablas_detectadas)}")
print("----------------------------------")