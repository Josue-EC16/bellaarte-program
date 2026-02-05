from core.database import SessionLocal
from models.models import Rol, User # Importamos tus clases actualizadas
from passlib.context import CryptContext

# Configuración del "hasheador"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")  

def seed_database():
    session = SessionLocal()
    try:
        print("--- 🌱 INICIANDO SEMBRADO PARA BELLAARTE ---")

        # 1. Crear los Roles (Usando name_rol)
        roles_lista = [
            "SUPERADMIN", 
            "ADMIN", 
            "ENCARGADO(A)_INVENTARIO", 
            "CAJERO(A)", 
            "MODISTA",
            "COSTURERO(A)",
            "DECORADOR(A)"
        ]

        for nombre in roles_lista:
            # Filtramos por tu columna exacta: name_rol
            rol_existente = session.query(Rol).filter(Rol.name_rol == nombre).first()
            if not rol_existente:
                nuevo_rol = Rol(name_rol=nombre)
                session.add(nuevo_rol)
                print(f"✅ Rol creado: {nombre}")
            else:
                print(f"ℹ️  El Rol '{nombre}' ya existe.")

        session.commit()

        # 2. Crear el Usuario SUPERADMIN (Usando tus sufijos _user)
        # Obtenemos el objeto del rol para sacar su id_rol
        rol_sa = session.query(Rol).filter(Rol.name_rol == "SUPERADMIN").first()

        if rol_sa is None:
            print("❌ Error crítico: No se encontró el rol SUPERADMIN en la base de datos.")
            return

        superadmin_email = "superadmin@bellaarte.com"
        alias = "SuperAdmin"
        # Filtramos por tu columna exacta: mail_user
        user_existente = session.query(User).filter(User.account_user == alias).first()

        if not user_existente:

            password_plana = "superadmin123"
            password_segura = pwd_context.hash(password_plana)

            super_user = User(
                id_rol=rol_sa.id_rol,
                names_user="SUPERADMINISTRADOR",
                p_ln_user="SUPERPRINCIPAL",
                m_ln_user="BOUTIQUE",
                ci_user=1234567,      # Integer según tu modelo
                cell_user=70000000,    # Integer según tu modelo
                zone_user="CENTRAL",
                address_user="CALLE FALSA 123",
                email_user=superadmin_email,
                account_user=alias,
                password_user=password_segura, # Luego lo cifraremos
                is_active_user=True
            )
            session.add(super_user)
            print(f"👤 Usuario '{alias}' creado exitosamente.")
        else:
            print(f"ℹ️  El usuario '{alias}' ya existe.")

        session.commit()
        print("--- ✨ SEMBRADO COMPLETADO ---")

    except Exception as e:
        session.rollback()
        print(f"❌ Error durante el sembrado: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    seed_database()