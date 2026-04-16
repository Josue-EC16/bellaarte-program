from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Identity, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.base import Base


UPPERCASE_FIELDS = {
    "nombre",
    "color",
    "forma",
    "material",
    "proveedor",
    "descripcion",
    "observaciones",
}


class ItemBoutique(Base):
    __tablename__ = "ITEM_BOUTIQUE"
    __table_args__ = (
        CheckConstraint('"ITB_PRECIO_COMPRA" >= 0', name="CK_ITB_PRECIO_COMPRA"),
        CheckConstraint('"ITB_PRECIO_VENTA" >= 0', name="CK_ITB_PRECIO_VENTA"),
        CheckConstraint('"ITB_STOCK" >= 0', name="CK_ITB_STOCK"),
        CheckConstraint('"ITB_STOCK_MIN" >= 0', name="CK_ITB_STOCK_MIN"),
    )

    id: Mapped[int] = mapped_column("ITB_ID", BigInteger, Identity(always=True), primary_key=True)
    tipo_item_id: Mapped[int] = mapped_column(
        "TIB_ID",
        ForeignKey("TIPO_ITEM_BOUTIQUE.TIB_ID", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    codigo: Mapped[str] = mapped_column("ITB_COD", String(40), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column("ITB_NOM", String(150), nullable=False)
    color: Mapped[str] = mapped_column("ITB_COLOR", String(60), nullable=False)
    forma: Mapped[str | None] = mapped_column("ITB_FORMA", String(60))
    material: Mapped[str] = mapped_column("ITB_MATERIAL", String(100), nullable=False)
    medidas: Mapped[str | None] = mapped_column("ITB_MEDIDAS", Text)
    proveedor: Mapped[str | None] = mapped_column("ITB_PROVEEDOR", String(100))
    descripcion: Mapped[str | None] = mapped_column("ITB_DES", Text)
    precio_compra: Mapped[float] = mapped_column("ITB_PRECIO_COMPRA", Numeric(12, 2), default=0, nullable=False)
    precio_venta: Mapped[float] = mapped_column("ITB_PRECIO_VENTA", Numeric(12, 2), default=0, nullable=False)
    stock: Mapped[float] = mapped_column("ITB_STOCK", Numeric(12, 2), default=0, nullable=False)
    stock_minimo: Mapped[float] = mapped_column("ITB_STOCK_MIN", Numeric(12, 2), default=0, nullable=False)
    estado: Mapped[bool] = mapped_column("ITB_ESTADO", Boolean, default=True, nullable=False)
    observaciones: Mapped[str | None] = mapped_column("ITB_OBS", Text)
    fecha_registro: Mapped[datetime] = mapped_column(
        "ITB_FEC_REG",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    tipo_item = relationship("TipoItemBoutique", back_populates="items")
    detalle_vestido = relationship(
        "DetalleVestidoBoutique",
        back_populates="item",
        uselist=False,
        cascade="all, delete-orphan",
    )
    detalle_velo = relationship(
        "DetalleVeloBoutique",
        back_populates="item",
        uselist=False,
        cascade="all, delete-orphan",
    )
    detalle_bouquet = relationship(
        "DetalleBouquetBoutique",
        back_populates="item",
        uselist=False,
        cascade="all, delete-orphan",
    )

    @validates("codigo")
    def normalize_code(self, _key: str, value: str) -> str:
        return value.strip().upper()

    @validates("nombre", "color", "forma", "material", "proveedor", "descripcion", "observaciones")
    def normalize_uppercase(self, key: str, value: str | None) -> str | None:
        if value is None:
            return None
        if key not in UPPERCASE_FIELDS:
            return value.strip()
        return value.strip().upper()

    @validates("medidas")
    def normalize_measures(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()
