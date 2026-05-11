from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Identity, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.base import Base


class ItemBoutique(Base):
    __tablename__ = "item_boutique"
    __table_args__ = (
        CheckConstraint("itb_largo IS NULL OR itb_largo >= 0", name="ck_itb_largo"),
        CheckConstraint("itb_ancho IS NULL OR itb_ancho >= 0", name="ck_itb_ancho"),
        CheckConstraint("itb_precio_compra >= 0", name="ck_itb_precio_compra"),
        CheckConstraint("itb_precio_venta >= 0", name="ck_itb_precio_venta"),
        CheckConstraint("itb_stock >= 0", name="ck_itb_stock"),
        CheckConstraint("itb_stock_min >= 0", name="ck_itb_stock_min"),
    )

    id: Mapped[int] = mapped_column("itb_id", BigInteger, Identity(always=True), primary_key=True)
    tipo_item_id: Mapped[int] = mapped_column(
        "tib_id",
        ForeignKey("tipo_item_boutique.tib_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    proveedor_id: Mapped[int | None] = mapped_column(
        "pro_id",
        ForeignKey("proveedor.pro_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=True,
    )
    codigo: Mapped[str] = mapped_column("itb_cod", String(40), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column("itb_nom", String(150), nullable=False)
    color_primario: Mapped[str] = mapped_column("itb_color_prim", String(60), nullable=False)
    color_secundario: Mapped[str | None] = mapped_column("itb_color_secun", String(60))
    material: Mapped[str] = mapped_column("itb_material", String(100), nullable=False)
    largo: Mapped[float | None] = mapped_column("itb_largo", Numeric(6, 2))
    ancho: Mapped[float | None] = mapped_column("itb_ancho", Numeric(6, 2))
    precio_compra: Mapped[float] = mapped_column("itb_precio_compra", Numeric(12, 2), default=0, nullable=False)
    precio_venta: Mapped[float] = mapped_column("itb_precio_venta", Numeric(12, 2), default=0, nullable=False)
    stock: Mapped[int] = mapped_column("itb_stock", Integer, default=0, nullable=False)
    stock_minimo: Mapped[int] = mapped_column("itb_stock_min", Integer, default=0, nullable=False)
    detalle: Mapped[str | None] = mapped_column("itb_detalle", Text)
    estado: Mapped[bool] = mapped_column("itb_estado", Boolean, default=True, nullable=False)
    fecha_registro: Mapped[datetime] = mapped_column(
        "itb_fec_reg",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    tipo_item = relationship("TipoItemBoutique", back_populates="items")
    proveedor_rel = relationship("Proveedor", back_populates="items")
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
    detalle_brassier = relationship(
        "DetalleBrassierBoutique",
        back_populates="item",
        uselist=False,
        cascade="all, delete-orphan",
    )
    entradas = relationship("EntradaItemBoutique", back_populates="item")

    @validates("codigo")
    def normalize_code(self, _key: str, value: str) -> str:
        return value.strip().upper()

    @validates("nombre", "color_primario", "color_secundario", "material", "detalle")
    def normalize_uppercase(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()
