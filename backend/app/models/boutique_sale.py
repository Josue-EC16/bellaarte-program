from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, Computed, DateTime, Enum as SqlEnum, ForeignKey, Identity, Index, Integer, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.base import Base
from app.models.boutique_enums import EstadoVentaBoutiqueEnum, MetodoPagoEnum, MotivoDescVentaBoutiqueEnum


metodo_pago_enum = SqlEnum(
    MetodoPagoEnum,
    name="metodo_pago",
    values_callable=lambda enum_cls: [item.value for item in enum_cls],
    create_type=False,
)
motivo_desc_venta_boutique_enum = SqlEnum(
    MotivoDescVentaBoutiqueEnum,
    name="motivo_desc_venta_boutique",
    values_callable=lambda enum_cls: [item.value for item in enum_cls],
    create_type=False,
)
estado_venta_boutique_enum = SqlEnum(
    EstadoVentaBoutiqueEnum,
    name="estado_venta_boutique",
    values_callable=lambda enum_cls: [item.value for item in enum_cls],
    create_type=False,
)


class VentaBoutique(Base):
    __tablename__ = "venta_boutique"
    __table_args__ = (
        CheckConstraint(
            "(veb_estado = 'activa' and veb_fec_camb_est IS NULL and veb_motivo_camb_est IS NULL) OR "
            "(veb_estado in ('cancelada', 'anulada') and veb_fec_camb_est IS NOT NULL and veb_motivo_camb_est IS NOT NULL)",
            name="ck_veb_cambio_estado",
        ),
        CheckConstraint("veb_cant > 0", name="ck_veb_cant"),
        CheckConstraint("veb_pre_uni > 0", name="ck_veb_pre_uni"),
        CheckConstraint(
            "veb_descuento IS NULL OR (veb_descuento >= 0 AND veb_descuento <= (veb_cant * veb_pre_uni))",
            name="ck_veb_descuento",
        ),
        CheckConstraint(
            "(veb_descuento IS NULL AND veb_motivo_desc IS NULL) OR "
            "(veb_descuento IS NOT NULL AND veb_motivo_desc IS NOT NULL)",
            name="ck_veb_desc_motivo",
        ),
        CheckConstraint("veb_tipo_cambio_usado > 0", name="ck_veb_tipo_cambio"),
        CheckConstraint("veb_total_moneda_orig > 0", name="ck_veb_total_moneda_orig"),
        Index("ix_veb_fec", "veb_fec"),
        Index("ix_veb_estado", "veb_estado"),
        Index("ix_veb_metodo_pago", "veb_metodo_pago"),
        Index("ix_veb_itb_id", "itb_id"),
        Index("ix_veb_cli_id", "cli_id"),
        Index("ix_veb_usu_id", "usu_id"),
        Index("ix_veb_mon_id", "mon_id"),
    )

    id: Mapped[int] = mapped_column("veb_id", BigInteger, Identity(always=True), primary_key=True)
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
    cliente_id: Mapped[int | None] = mapped_column(
        "cli_id",
        ForeignKey("cliente.cli_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=True,
    )
    moneda_id: Mapped[int] = mapped_column(
        "mon_id",
        ForeignKey("moneda.mon_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    fecha: Mapped[datetime] = mapped_column("veb_fec", DateTime(timezone=True), server_default=func.now(), nullable=False)
    cantidad: Mapped[int] = mapped_column("veb_cant", Integer, nullable=False)
    precio_unitario: Mapped[float] = mapped_column("veb_pre_uni", Numeric(12, 2), nullable=False)
    descuento: Mapped[float | None] = mapped_column("veb_descuento", Numeric(12, 2))
    motivo_descuento: Mapped[MotivoDescVentaBoutiqueEnum | None] = mapped_column("veb_motivo_desc", motivo_desc_venta_boutique_enum)
    total: Mapped[float] = mapped_column(
        "veb_tot",
        Numeric(12, 2),
        Computed("round(veb_cant * veb_pre_uni - coalesce(veb_descuento, 0), 2)", persisted=True),
        nullable=False,
    )
    tipo_cambio_usado: Mapped[float] = mapped_column("veb_tipo_cambio_usado", Numeric(12, 4), nullable=False, default=1)
    total_moneda_original: Mapped[float] = mapped_column("veb_total_moneda_orig", Numeric(12, 2), nullable=False)
    metodo_pago: Mapped[MetodoPagoEnum] = mapped_column("veb_metodo_pago", metodo_pago_enum, nullable=False)
    observaciones: Mapped[str | None] = mapped_column("veb_obs", Text)
    estado: Mapped[EstadoVentaBoutiqueEnum] = mapped_column(
        "veb_estado",
        estado_venta_boutique_enum,
        nullable=False,
        default=EstadoVentaBoutiqueEnum.ACTIVA,
        server_default=EstadoVentaBoutiqueEnum.ACTIVA.value,
    )
    fecha_cambio_estado: Mapped[datetime | None] = mapped_column("veb_fec_camb_est", DateTime(timezone=True))
    motivo_cambio_estado: Mapped[str | None] = mapped_column("veb_motivo_camb_est", Text)

    item = relationship("ItemBoutique")
    usuario = relationship("Usuario")
    cliente = relationship("Cliente")
    moneda = relationship("Moneda")

    @validates("observaciones", "motivo_cambio_estado")
    def normalize_text(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()
