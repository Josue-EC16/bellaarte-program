from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum as SqlEnum, ForeignKey, Identity, Integer, Numeric, String, Text, CheckConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.base import Base
from app.models.boutique_enums import MotivoEntradaItemEnum


motivo_entrada_item_enum = SqlEnum(
    MotivoEntradaItemEnum,
    name="motivo_entrada_item",
    values_callable=lambda enum_cls: [item.value for item in enum_cls],
)


class EntradaItemBoutique(Base):
    __tablename__ = "entrada_item_boutique"
    __table_args__ = (
        CheckConstraint("eib_cant > 0", name="ck_eib_cant"),
        CheckConstraint("eib_costo_unitario >= 0", name="ck_eib_costo_unitario"),
    )

    id: Mapped[int] = mapped_column("eib_id", BigInteger, Identity(always=True), primary_key=True)
    item_id: Mapped[int] = mapped_column(
        "itb_id",
        ForeignKey("item_boutique.itb_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    usuario_id: Mapped[int] = mapped_column(
        "usu_id",
        ForeignKey("usuarios.id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    proveedor_id: Mapped[int | None] = mapped_column(
        "pro_id",
        ForeignKey("proveedor.pro_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=True,
    )
    fecha: Mapped[datetime] = mapped_column("eib_fec", DateTime(timezone=True), server_default=func.now(), nullable=False)
    cantidad: Mapped[int] = mapped_column("eib_cant", Integer, nullable=False)
    costo_unitario: Mapped[float] = mapped_column("eib_costo_unitario", Numeric(12, 2), default=0, nullable=False)
    motivo: Mapped[MotivoEntradaItemEnum] = mapped_column(
        "eib_motivo",
        motivo_entrada_item_enum,
        default=MotivoEntradaItemEnum.ENTRADA_STOCK,
        nullable=False,
    )
    documento_referencia: Mapped[str | None] = mapped_column("eib_doc_ref", String(80))
    observaciones: Mapped[str | None] = mapped_column("eib_obs", Text)
    estado: Mapped[bool] = mapped_column("eib_estado", Boolean, default=True, nullable=False)

    item = relationship("ItemBoutique", back_populates="entradas")
    usuario = relationship("Usuario")
    proveedor = relationship("Proveedor")

    @validates("documento_referencia", "observaciones")
    def normalize_uppercase(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()
