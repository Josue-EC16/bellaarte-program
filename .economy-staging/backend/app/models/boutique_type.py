from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Identity, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.base import Base


class TipoItemBoutique(Base):
    __tablename__ = "tipo_item_boutique"

    id: Mapped[int] = mapped_column("tib_id", BigInteger, Identity(always=True), primary_key=True)
    nombre: Mapped[str] = mapped_column("tib_nom", String(100), unique=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column("tib_des", String(200))
    habilitado: Mapped[bool] = mapped_column("tib_hab", Boolean, default=True, nullable=False)
    fecha_registro: Mapped[datetime] = mapped_column(
        "tib_fec_reg",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    items = relationship("ItemBoutique", back_populates="tipo_item")

    @validates("nombre", "descripcion")
    def normalize_text(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()
