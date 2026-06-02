from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Computed, Date, DateTime, Enum as SqlEnum, ForeignKey, Identity, Index, Integer, Numeric, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.base import Base
from app.models.boutique_enums import EstadoFleteDevolucionEnum, EstadoFleteEntregaEnum, EstadoFleteEnum, EstadoSalidaFleteEnum, MetodoPagoEnum, MotivoDescFleteEnum


estado_flete_enum = SqlEnum(
    EstadoFleteEnum,
    name="estado_flete",
    values_callable=lambda enum_cls: [item.value for item in enum_cls],
    create_type=False,
)
motivo_desc_flete_enum = SqlEnum(
    MotivoDescFleteEnum,
    name="motivo_desc_flete",
    values_callable=lambda enum_cls: [item.value for item in enum_cls],
    create_type=False,
)
estado_salida_flete_enum = SqlEnum(
    EstadoSalidaFleteEnum,
    name="estado_salida_flete",
    values_callable=lambda enum_cls: [item.value for item in enum_cls],
    create_type=False,
)
estado_flete_entrega_enum = SqlEnum(
    EstadoFleteEntregaEnum,
    name="estado_flete_entrega",
    values_callable=lambda enum_cls: [item.value for item in enum_cls],
    create_type=False,
)
estado_flete_devolucion_enum = SqlEnum(
    EstadoFleteDevolucionEnum,
    name="estado_flete_devolucion",
    values_callable=lambda enum_cls: [item.value for item in enum_cls],
    create_type=False,
)
metodo_pago_enum = SqlEnum(
    MetodoPagoEnum,
    name="metodo_pago",
    values_callable=lambda enum_cls: [item.value for item in enum_cls],
    create_type=False,
)


class FleteVestido(Base):
    __tablename__ = "flete_vestido"
    __table_args__ = (
        CheckConstraint("fle_salidas_actuales >= 0 and fle_salidas_actuales <= fle_max_salidas", name="ck_flete_salidas_actuales"),
        CheckConstraint("fle_max_salidas between 1 and 4", name="ck_flete_max_salidas"),
        CheckConstraint("fle_precio_flete_ref > 0", name="ck_precio_flete_ref"),
        Index("ix_flete_itb_id", "itb_id"),
        Index("ix_flete_estado_hab", "fle_estado", "fle_hab"),
    )

    id: Mapped[int] = mapped_column("fle_id", BigInteger, Identity(always=True), primary_key=True)
    item_id: Mapped[int] = mapped_column(
        "itb_id",
        ForeignKey("item_boutique.itb_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    usuario_id: Mapped[int] = mapped_column(
        "usu_id",
        ForeignKey("usuarios.id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    precio_flete_referencial: Mapped[float] = mapped_column("fle_precio_flete_ref", Numeric(12, 2), nullable=False)
    max_salidas: Mapped[int] = mapped_column("fle_max_salidas", SmallInteger, nullable=False, default=3)
    salidas_actuales: Mapped[int] = mapped_column("fle_salidas_actuales", SmallInteger, nullable=False, default=0)
    estado: Mapped[EstadoFleteEnum] = mapped_column(
        "fle_estado",
        estado_flete_enum,
        nullable=False,
        default=EstadoFleteEnum.DISPONIBLE,
        server_default=EstadoFleteEnum.DISPONIBLE.value,
    )
    fecha_habilitacion: Mapped[datetime] = mapped_column("fle_fec_hab_flete", DateTime(timezone=True), nullable=False, server_default=func.now())
    observaciones: Mapped[str | None] = mapped_column("fle_obs", String(150))
    habilitado: Mapped[bool] = mapped_column("fle_hab", Boolean, nullable=False, default=True)

    item = relationship("ItemBoutique", back_populates="flete")
    usuario = relationship("Usuario")
    salidas = relationship("SalidaFlete", back_populates="flete")

    @validates("observaciones")
    def normalize_text(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()


class SalidaFlete(Base):
    __tablename__ = "salida_flete"
    __table_args__ = (
        CheckConstraint(
            "("
            "(sfl_estado_salida in ('reservado', 'en_flete', 'devuelto', 'devuelto_con_observacion', 'devuelto_con_arreglo') "
            "and sfl_fec_camb_est is null and sfl_motivo_camb_est is null)"
            " or "
            "(sfl_estado_salida = 'anulado' and sfl_fec_camb_est is not null and sfl_motivo_camb_est is not null)"
            ")",
            name="ck_sfl_cambio_estado_salida",
        ),
        CheckConstraint("sfl_precio > 0", name="ck_salida_flete_precio"),
        CheckConstraint("sfl_garantia >= 0", name="ck_salida_flete_garantia"),
        CheckConstraint("sfl_total_flete_moneda_orig > 0", name="ck_sfl_total_flete_moneda_orig"),
        CheckConstraint("sfl_garantia_devuelta >= 0 and sfl_garantia_devuelta <= sfl_garantia", name="ck_salida_flete_garantia_devuelta"),
        CheckConstraint("sfl_monto_arreglo >= 0", name="ck_salida_flete_monto_arreglo"),
        CheckConstraint("sfl_tipo_cambio_usado > 0", name="ck_sfl_tipo_cambio"),
        CheckConstraint("sfl_fec_devolucion_prevista >= sfl_fec_salida", name="ck_salida_flete_fechas"),
        CheckConstraint("sfl_num between 1 and 4", name="ck_salida_flete_num"),
        CheckConstraint(
            "("
            "(sfl_requiere_arreglo = false and sfl_monto_arreglo = 0 and sfl_descripcion_arreglo is null)"
            " or "
            "(sfl_requiere_arreglo = true and sfl_monto_arreglo >= 0 and sfl_descripcion_arreglo is not null)"
            ")",
            name="ck_sfl_arreglo",
        ),
        CheckConstraint(
            "sfl_fec_devolucion_real is null or sfl_fec_devolucion_real >= sfl_fec_salida",
            name="ck_salida_flete_fecha_real",
        ),
        CheckConstraint(
            "sfl_descuento is null or (sfl_descuento >= 0 and sfl_descuento <= sfl_precio)",
            name="ck_sfl_descuento",
        ),
        CheckConstraint(
            "(sfl_descuento is null and sfl_motivo_desc is null) or (sfl_descuento is not null and sfl_motivo_desc is not null)",
            name="ck_sfl_desc_motivo",
        ),
        Index("ix_sfl_estado_fechas", "sfl_estado_salida", "sfl_fec_salida", "sfl_fec_devolucion_prevista"),
        Index("ix_sfl_fle_num", "fle_id", "sfl_num", unique=True),
    )

    id: Mapped[int] = mapped_column("sfl_id", BigInteger, Identity(always=True), primary_key=True)
    flete_id: Mapped[int] = mapped_column(
        "fle_id",
        ForeignKey("flete_vestido.fle_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    cliente_id: Mapped[int] = mapped_column(
        "cli_id",
        ForeignKey("cliente.cli_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    usuario_id: Mapped[int] = mapped_column(
        "usu_id",
        ForeignKey("usuarios.id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    moneda_id: Mapped[int] = mapped_column(
        "mon_id",
        ForeignKey("moneda.mon_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    numero_salida: Mapped[int] = mapped_column("sfl_num", SmallInteger, nullable=False)
    fecha_registro: Mapped[datetime] = mapped_column("sfl_fec_reg", DateTime(timezone=True), nullable=False, server_default=func.now())
    fecha_salida: Mapped[date] = mapped_column("sfl_fec_salida", Date, nullable=False)
    fecha_devolucion_prevista: Mapped[date] = mapped_column("sfl_fec_devolucion_prevista", Date, nullable=False)
    fecha_devolucion_real: Mapped[date | None] = mapped_column("sfl_fec_devolucion_real", Date)
    precio: Mapped[float] = mapped_column("sfl_precio", Numeric(10, 2), nullable=False)
    descuento: Mapped[float | None] = mapped_column("sfl_descuento", Numeric(12, 2))
    motivo_descuento: Mapped[MotivoDescFleteEnum | None] = mapped_column("sfl_motivo_desc", motivo_desc_flete_enum)
    metodo_pago: Mapped[MetodoPagoEnum] = mapped_column("sfl_metodo_pago", metodo_pago_enum, nullable=False)
    tipo_cambio_usado: Mapped[float] = mapped_column("sfl_tipo_cambio_usado", Numeric(12, 4), nullable=False, default=1)
    total_flete: Mapped[float] = mapped_column(
        "sfl_total_flete",
        Numeric(12, 2),
        Computed("round((sfl_precio - coalesce(sfl_descuento, 0)), 2)", persisted=True),
        nullable=False,
    )
    total_flete_moneda_original: Mapped[float] = mapped_column("sfl_total_flete_moneda_orig", Numeric(12, 2), nullable=False)
    garantia: Mapped[float] = mapped_column("sfl_garantia", Numeric(10, 2), nullable=False, default=0)
    garantia_devuelta: Mapped[float] = mapped_column("sfl_garantia_devuelta", Numeric(10, 2), nullable=False, default=0)
    estado_salida: Mapped[EstadoSalidaFleteEnum] = mapped_column(
        "sfl_estado_salida",
        estado_salida_flete_enum,
        nullable=False,
        default=EstadoSalidaFleteEnum.RESERVADO,
        server_default=EstadoSalidaFleteEnum.RESERVADO.value,
    )
    fecha_cambio_estado: Mapped[datetime | None] = mapped_column("sfl_fec_camb_est", DateTime(timezone=True))
    motivo_cambio_estado: Mapped[str | None] = mapped_column("sfl_motivo_camb_est", Text)
    estado_entrega: Mapped[EstadoFleteEntregaEnum] = mapped_column("sfl_estado_entrega", estado_flete_entrega_enum, nullable=False)
    estado_devolucion: Mapped[EstadoFleteDevolucionEnum | None] = mapped_column("sfl_estado_devolucion", estado_flete_devolucion_enum)
    requiere_arreglo: Mapped[bool] = mapped_column("sfl_requiere_arreglo", Boolean, nullable=False, default=False)
    monto_arreglo: Mapped[float] = mapped_column("sfl_monto_arreglo", Numeric(10, 2), nullable=False, default=0)
    descripcion_arreglo: Mapped[str | None] = mapped_column("sfl_descripcion_arreglo", String(150))
    observaciones_entrega: Mapped[str | None] = mapped_column("sfl_obs_entrega", Text)
    observaciones_devolucion: Mapped[str | None] = mapped_column("sfl_obs_devolucion", Text)
    habilitado: Mapped[bool] = mapped_column("sfl_hab", Boolean, nullable=False, default=True)

    flete = relationship("FleteVestido", back_populates="salidas")
    cliente = relationship("Cliente")
    usuario = relationship("Usuario")
    moneda = relationship("Moneda")
    comprobante = relationship("ComprobanteInterno", back_populates="salida_flete", uselist=False)

    @validates(
        "motivo_cambio_estado",
        "descripcion_arreglo",
        "observaciones_entrega",
        "observaciones_devolucion",
    )
    def normalize_text(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()
