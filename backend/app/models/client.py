from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Identity, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.models.base import Base


class Cliente(Base):
    __tablename__ = "cliente"

    id: Mapped[int] = mapped_column("cli_id", BigInteger, Identity(always=True), primary_key=True)
    codigo: Mapped[str] = mapped_column("cli_cod", String(20), unique=True, nullable=False)
    nombres: Mapped[str] = mapped_column("cli_nom", String(100), nullable=False)
    apellido_paterno: Mapped[str] = mapped_column("cli_ape_pat", String(100), nullable=False)
    apellido_materno: Mapped[str | None] = mapped_column("cli_ape_mat", String(100))
    celular: Mapped[str] = mapped_column("cli_cel", String(30), nullable=False)
    celular_referencia: Mapped[str | None] = mapped_column("cli_cel_ref", String(30))
    nombre_referencia: Mapped[str | None] = mapped_column("cli_nom_cel_ref", String(120))
    correo: Mapped[str | None] = mapped_column("cli_cor", String(100), unique=True)
    ci: Mapped[str | None] = mapped_column("cli_ci", String(30), unique=True)
    fecha_nacimiento: Mapped[date | None] = mapped_column("cli_fecha_nac", Date)
    pais: Mapped[str | None] = mapped_column("cli_pais", String(100))
    ciudad: Mapped[str | None] = mapped_column("cli_ciudad", String(100))
    zona: Mapped[str | None] = mapped_column("cli_zona", String(100))
    calle: Mapped[str | None] = mapped_column("cli_calle", String(100))
    observaciones: Mapped[str | None] = mapped_column("cli_obs", Text)
    habilitado: Mapped[bool] = mapped_column("cli_hab", Boolean, default=True, nullable=False)
    fecha_registro: Mapped[datetime] = mapped_column(
        "cli_fec_reg",
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
        "pais",
        "ciudad",
        "zona",
        "calle",
        "observaciones",
    )
    def normalize_uppercase(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()

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
