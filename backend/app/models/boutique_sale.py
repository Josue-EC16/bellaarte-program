from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, Computed, DateTime, ForeignKey, Identity, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.base import Base
from app.models.boutique_enums import EstadoVentaBoutiqueEnum, MetodoPagoEnum, MotivoDescVentaBoutiqueEnum


metodo_pago_enum = ENUM(
    MetodoPagoEnum,
    name="METODO_PAGO",
    values_callable=lambda enum_cls: [item.value for item in enum_cls],
    create_type=False,
)
motivo_desc_venta_boutique_enum = ENUM(
    MotivoDescVentaBoutiqueEnum,
    name="MOTIVO_DESC_VENTA_BOUTIQUE",
    values_callable=lambda enum_cls: [item.value for item in enum_cls],
    create_type=False,
)
estado_venta_boutique_enum = ENUM(
    EstadoVentaBoutiqueEnum,
    name="ESTADO_VENTA_BOUTIQUE",
    values_callable=lambda enum_cls: [item.value for item in enum_cls],
    create_type=False,
)


class VentaBoutique(Base):
    __tablename__ = "VENTA_BOUTIQUE"
    __table_args__ = (
        CheckConstraint('"VEB_CANT" > 0', name="CK_VEB_CANT"),
        CheckConstraint('"VEB_PRE_UNI" >= 0', name="CK_VEB_PRE_UNI"),
        CheckConstraint(
            '"VEB_DESCUENTO" IS NULL OR ("VEB_DESCUENTO" >= 0 AND "VEB_DESCUENTO" <= ("VEB_CANT" * "VEB_PRE_UNI"))',
            name="CK_VEB_DESCUENTO",
        ),
        CheckConstraint(
            '("VEB_DESCUENTO" IS NULL AND "VEB_MOTIVO_DESC" IS NULL) OR ("VEB_DESCUENTO" IS NOT NULL AND "VEB_MOTIVO_DESC" IS NOT NULL)',
            name="CK_VEB_DESC_MOTIVO",
        ),
        Index("IX_VEB_FEC", "VEB_FEC"),
        Index("IX_VEB_ESTADO", "VEB_ESTADO"),
        Index("IX_VEB_METODO_PAGO", "VEB_METODO_PAGO"),
        Index("IX_VEB_ITB_ID", "ITB_ID"),
        Index("IX_VEB_CLI_ID", "CLI_ID"),
        Index("IX_VEB_USU_ID", "USU_ID"),
    )

    id: Mapped[int] = mapped_column("VEB_ID", BigInteger, Identity(always=True), primary_key=True)
    item_id: Mapped[int] = mapped_column(
        "ITB_ID",
        ForeignKey("ITEM_BOUTIQUE.ITB_ID", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    usuario_id: Mapped[int] = mapped_column(
        "USU_ID",
        ForeignKey("usuarios.id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    cliente_id: Mapped[int | None] = mapped_column(
        "CLI_ID",
        ForeignKey("CLIENTE.CLI_ID", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=True,
    )
    fecha: Mapped[datetime] = mapped_column(
        "VEB_FEC",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    cantidad: Mapped[float] = mapped_column("VEB_CANT", Numeric(12, 2), nullable=False)
    precio_unitario: Mapped[float] = mapped_column("VEB_PRE_UNI", Numeric(12, 2), nullable=False)
    descuento: Mapped[float | None] = mapped_column("VEB_DESCUENTO", Numeric(12, 2))
    motivo_descuento: Mapped[MotivoDescVentaBoutiqueEnum | None] = mapped_column(
        "VEB_MOTIVO_DESC",
        motivo_desc_venta_boutique_enum,
    )
    total: Mapped[float] = mapped_column(
        "VEB_TOT",
        Numeric(12, 2),
        Computed('ROUND("VEB_CANT" * "VEB_PRE_UNI" - COALESCE("VEB_DESCUENTO", 0), 2)', persisted=True),
        nullable=False,
    )
    metodo_pago: Mapped[MetodoPagoEnum] = mapped_column("VEB_METODO_PAGO", metodo_pago_enum, nullable=False)
    observaciones: Mapped[str | None] = mapped_column("VEB_OBS", Text)
    estado: Mapped[EstadoVentaBoutiqueEnum] = mapped_column(
        "VEB_ESTADO",
        estado_venta_boutique_enum,
        nullable=False,
        default=EstadoVentaBoutiqueEnum.ACTIVA,
        server_default=EstadoVentaBoutiqueEnum.ACTIVA.value,
    )

    item = relationship("ItemBoutique")
    usuario = relationship("Usuario")
    cliente = relationship("Cliente")

    @validates("observaciones")
    def normalize_text(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()
