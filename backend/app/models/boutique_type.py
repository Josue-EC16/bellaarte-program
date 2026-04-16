from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Identity, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.base import Base


class TipoItemBoutique(Base):
    __tablename__ = "TIPO_ITEM_BOUTIQUE"

    id: Mapped[int] = mapped_column("TIB_ID", BigInteger, Identity(always=True), primary_key=True)
    nombre: Mapped[str] = mapped_column("TIB_NOM", String(100), unique=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column("TIB_DES", String(200))
    habilitado: Mapped[bool] = mapped_column("TIB_HAB", Boolean, default=True, nullable=False)
    fecha_registro: Mapped[datetime] = mapped_column(
        "TIB_FEC_REG",
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
