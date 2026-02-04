from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from database import Base  # Importamos la base declarativa que configuraremos en database.py

class Rol(Base):
    __tablename__ = "rol"

    id_rol = Column(Integer, primary_key=True, index=True)
    name_rol = Column(String(50), unique=True, nullable=False)

    # Relación: Un rol puede tener muchos usuarios
    users = relationship("User", back_populates="rol")

    def __repr__(self):
        return f"<Rol(name='{self.name_rol}')>"

class User(Base):
    __tablename__ = "users"

    id_user = Column(Integer, primary_key=True, index=True)
    id_rol = Column(Integer, ForeignKey("rol.id_rol", ondelete="RESTRICT"), nullable=False)
    
    # Datos Personales
    names_user = Column(String(70), nullable=False)
    p_ln_user = Column(String(70), nullable=False)  # Apellido Paterno
    m_ln_user = Column(String(70), nullable=False)  # Apellido Materno
    ci_user = Column(Integer, unique=True, nullable=False)
    cell_user = Column(Integer, nullable=False)
    
    # Ubicación
    zone_user = Column(String(70), nullable=False)
    address_user = Column(Text)
    
    # Credenciales y Estado
    email_user = Column(String(100), unique=True)
    account_user = Column(String(50), unique=True, nullable=False)
    password_user = Column(String(255), nullable=False)
    is_active_user = Column(Boolean, default=True)
    
    # Metadatos automáticos
    created_at_user = Column(DateTime(timezone=True), server_default=func.now())
    updated_at_user = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relación inversa: Un usuario pertenece a un rol
    rol = relationship("Rol", back_populates="users")

    def __repr__(self):
        return f"<User(account='{self.account_user}', names='{self.names_user}')>"

    @validates('names_user', 'p_ln_user', 'm_ln_user', 'zone_user', 'address_user')
    def convert_upper(self, key, value):
        if value is not None and isinstance(value, str):
            return value.upper().strip() # .upper() lo vuelve mayúscula, .strip() quita espacios extra
        return value