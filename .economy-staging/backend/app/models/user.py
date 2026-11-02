from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.base import Base, TimestampMixin


class Usuario(TimestampMixin, Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nombres: Mapped[str] = mapped_column(String(120), nullable=False)
    apellido_paterno: Mapped[str] = mapped_column(String(120), nullable=False)
    apellido_materno: Mapped[str | None] = mapped_column(String(120))
    ci: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)
    celular: Mapped[str] = mapped_column(String(30), nullable=False)
    correo: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    zona: Mapped[str] = mapped_column(String(120), nullable=False)
    direccion: Mapped[str | None] = mapped_column(Text())
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    cuenta = relationship("Cuenta", back_populates="usuario", uselist=False)

    @validates("nombres", "apellido_paterno", "apellido_materno", "zona", "direccion")
    def normalize_uppercase(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()

    @validates("correo")
    def normalize_email(self, _key: str, value: str) -> str:
        return value.strip().lower()

    @validates("ci", "celular")
    def normalize_plain_strings(self, _key: str, value: str) -> str:
        return value.strip()

    @property
    def nombre_completo(self) -> str:
        parts = [self.nombres, self.apellido_paterno]
        if self.apellido_materno:
            parts.append(self.apellido_materno)
        return " ".join(parts)

