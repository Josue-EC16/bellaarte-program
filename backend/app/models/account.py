from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.base import Base, TimestampMixin


class Cuenta(TimestampMixin, Base):
    __tablename__ = "cuentas"
    __table_args__ = (CheckConstraint("auth_version >= 0", name="ck_cuentas_auth_version"),
                      CheckConstraint("security_version >= 0", name="ck_cuentas_security_version"))

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"), unique=True, nullable=False)
    rol_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auth_version: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"), nullable=False)
    security_version: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"), nullable=False)

    usuario = relationship("Usuario", back_populates="cuenta")
    rol = relationship("Rol", back_populates="cuentas")

    @validates("username")
    def normalize_username(self, _key: str, value: str) -> str:
        return value.strip()
