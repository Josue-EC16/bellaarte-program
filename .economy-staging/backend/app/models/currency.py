from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Identity, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.base import Base


class Moneda(Base):
    __tablename__ = "moneda"
    __table_args__ = (
        Index("uq_moneda_base", "mon_es_base", unique=True, postgresql_where=text("mon_es_base = true")),
    )

    id: Mapped[int] = mapped_column("mon_id", BigInteger, Identity(always=True), primary_key=True)
    codigo: Mapped[str] = mapped_column("mon_cod", String(10), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column("mon_nom", String(80), nullable=False)
    simbolo: Mapped[str | None] = mapped_column("mon_simbolo", String(10))
    es_base: Mapped[bool] = mapped_column("mon_es_base", Boolean, default=False, nullable=False)
    habilitado: Mapped[bool] = mapped_column("mon_hab", Boolean, default=True, nullable=False)
    fecha_registro: Mapped[datetime] = mapped_column(
        "mon_fec_reg",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    tipos_cambio = relationship("TipoCambioMoneda", back_populates="moneda")

    @validates("codigo", "nombre", "simbolo")
    def normalize_text(self, key: str, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if key in {"codigo", "nombre"}:
            return normalized.upper()
        return normalized
