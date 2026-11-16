from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Identity, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.base import Base


class Proveedor(Base):
    __tablename__ = "proveedor"

    id: Mapped[int] = mapped_column("pro_id", BigInteger, Identity(always=True), primary_key=True)
    nombres: Mapped[str] = mapped_column("pro_nom", String(100), nullable=False)
    apellido_paterno: Mapped[str | None] = mapped_column("pro_ape_pat", String(50))
    apellido_materno: Mapped[str | None] = mapped_column("pro_ape_mat", String(50))
    nombre_comercial: Mapped[str | None] = mapped_column("pro_nom_comercial", String(120))
    celular: Mapped[str | None] = mapped_column("pro_cel", String(30), unique=True)
    celular_secundario: Mapped[str | None] = mapped_column("pro_cel_sec", String(30))
    correo: Mapped[str | None] = mapped_column("pro_cor", String(120), unique=True)
    pais: Mapped[str | None] = mapped_column("pro_pais", String(50))
    ciudad: Mapped[str | None] = mapped_column("pro_ciudad", String(70))
    direccion: Mapped[str | None] = mapped_column("pro_dir", String(150))
    observaciones: Mapped[str | None] = mapped_column("pro_obs", Text)
    habilitado: Mapped[bool] = mapped_column("pro_hab", Boolean, default=True, nullable=False)
    fecha_registro: Mapped[datetime] = mapped_column(
        "pro_fec_reg",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    items = relationship("ItemBoutique", back_populates="proveedor_rel")

    @validates(
        "nombres",
        "apellido_paterno",
        "apellido_materno",
        "nombre_comercial",
        "pais",
        "ciudad",
        "direccion",
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

    @validates("celular", "celular_secundario")
    def normalize_phone(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @property
    def nombre_completo(self) -> str:
        parts = [self.nombres]
        if self.apellido_paterno:
            parts.append(self.apellido_paterno)
        if self.apellido_materno:
            parts.append(self.apellido_materno)
        return " ".join(parts)
