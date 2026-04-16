from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Identity, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.models.base import Base


class Cliente(Base):
    __tablename__ = "CLIENTE"

    id: Mapped[int] = mapped_column("CLI_ID", BigInteger, Identity(always=True), primary_key=True)
    codigo: Mapped[str] = mapped_column("CLI_COD", String(20), unique=True, nullable=False)
    nombres: Mapped[str] = mapped_column("CLI_NOM", String(100), nullable=False)
    apellido_paterno: Mapped[str] = mapped_column("CLI_APE_PAT", String(100), nullable=False)
    apellido_materno: Mapped[str | None] = mapped_column("CLI_APE_MAT", String(100))
    celular: Mapped[str] = mapped_column("CLI_CEL", String(30), nullable=False)
    celular_referencia: Mapped[str | None] = mapped_column("CLI_CEL_REF", String(30))
    nombre_referencia: Mapped[str | None] = mapped_column("CLI_NOM_CEL_REF", String(120))
    correo: Mapped[str | None] = mapped_column("CLI_COR", String(120))
    ci: Mapped[str | None] = mapped_column("CLI_CI", String(30))
    nacionalidad: Mapped[str | None] = mapped_column("CLI_NAC", String(100))
    zona: Mapped[str | None] = mapped_column("CLI_ZONA", String(100))
    calle: Mapped[str | None] = mapped_column("CLI_CALLE", String(100))
    observaciones: Mapped[str | None] = mapped_column("CLI_OBS", Text)
    habilitado: Mapped[bool] = mapped_column("CLI_HAB", Boolean, default=True, nullable=False)
    fecha_registro: Mapped[datetime] = mapped_column(
        "CLI_FEC_REG",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    @validates(
        "codigo",
        "nombres",
        "apellido_paterno",
        "apellido_materno",
        "nombre_referencia",
        "nacionalidad",
        "zona",
        "calle",
        "observaciones",
    )
    def normalize_uppercase(self, key: str, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if key == "codigo":
            return normalized.upper()
        return normalized.upper()

    @validates("correo")
    def normalize_email(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().lower()

    @validates("celular", "celular_referencia", "ci")
    def normalize_plain(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @property
    def nombre_completo(self) -> str:
        parts = [self.nombres, self.apellido_paterno]
        if self.apellido_materno:
            parts.append(self.apellido_materno)
        return " ".join(parts)
