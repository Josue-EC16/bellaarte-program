from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, Enum as SqlEnum, ForeignKey, Identity, Index, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.base import Base
from app.models.boutique_enums import EstadoComprobanteEnum, MetodoPagoEnum


metodo_pago_enum = SqlEnum(
    MetodoPagoEnum,
    name="metodo_pago",
    values_callable=lambda enum_cls: [item.value for item in enum_cls],
    create_type=False,
)
estado_comprobante_enum = SqlEnum(
    EstadoComprobanteEnum,
    name="estado_comprobante",
    values_callable=lambda enum_cls: [item.value for item in enum_cls],
    create_type=False,
)


class TipoComprobante(Base):
    __tablename__ = "tipo_comprobante"

    id: Mapped[int] = mapped_column("tco_id", BigInteger, Identity(always=True), primary_key=True)
    nombre: Mapped[str] = mapped_column("tco_nom", String(50), nullable=False, unique=True)
    descripcion: Mapped[str | None] = mapped_column("tco_des", String(100))
    es_fiscal: Mapped[bool] = mapped_column("tco_es_fiscal", Boolean, default=False, nullable=False)
    habilitado: Mapped[bool] = mapped_column("tco_hab", Boolean, default=True, nullable=False)
    fecha_registro: Mapped[datetime] = mapped_column("tco_fec_reg", DateTime(timezone=True), server_default=func.now(), nullable=False)

    comprobantes = relationship("ComprobanteInterno", back_populates="tipo_comprobante")

    @validates("nombre", "descripcion")
    def normalize_text(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()


class ComprobanteInterno(Base):
    __tablename__ = "comprobante_interno"
    __table_args__ = (
        CheckConstraint(
            "(coi_estado = 'emitido' and coi_fec_camb_est IS NULL and coi_motivo_camb_est IS NULL) OR "
            "(coi_estado = 'anulado' and coi_fec_camb_est IS NOT NULL and coi_motivo_camb_est IS NOT NULL)",
            name="ck_coi_cambio_estado",
        ),
        CheckConstraint("coi_descuento <= coi_subtotal", name="ck_comprobante_descuento"),
        CheckConstraint(
            "("
            "case when veb_id is not null then 1 else 0 end + "
            "case when ppd_id is not null then 1 else 0 end + "
            "case when sfl_id is not null then 1 else 0 end"
            ") = 1",
            name="ck_comprobante_un_origen",
        ),
        CheckConstraint("coi_total = round(coi_subtotal - coi_descuento, 2)", name="ck_comprobante_totales"),
        CheckConstraint(
            "coi_subtotal >= 0 and coi_descuento >= 0 and coi_total >= 0 and "
            "coi_total_moneda_orig >= 0 and coi_saldo_posterior >= 0 and coi_garantia >= 0 and "
            "coi_tipo_cambio_usado > 0",
            name="ck_comprobante_montos",
        ),
        Index("ix_coi_estado_fec", "coi_estado", "coi_fec"),
        Index("ix_coi_cod", "coi_cod"),
        Index("ix_coi_fec", "coi_fec"),
        Index("ix_coi_mon_id", "mon_id"),
        Index("ix_coi_cli_id", "cli_id"),
        Index("ix_coi_usu_id", "usu_id"),
        Index("ix_coi_sfl_id", "sfl_id"),
        Index("idx_coi_tco_fec", "tco_id", "coi_fec"),
        Index("idx_coi_cli_fec", "cli_id", "coi_fec"),
        Index("idx_coi_usu_fec", "usu_id", "coi_fec"),
        Index("idx_coi_mon_fec", "mon_id", "coi_fec"),
        Index("idx_coi_metodo_fec", "coi_metodo_pago", "coi_fec"),
    )

    id: Mapped[int] = mapped_column("coi_id", BigInteger, Identity(always=True), primary_key=True)
    tipo_comprobante_id: Mapped[int] = mapped_column(
        "tco_id",
        ForeignKey("tipo_comprobante.tco_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    cliente_id: Mapped[int | None] = mapped_column(
        "cli_id",
        ForeignKey("cliente.cli_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=True,
    )
    usuario_id: Mapped[int] = mapped_column(
        "usu_id",
        ForeignKey("usuarios.id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    venta_boutique_id: Mapped[int | None] = mapped_column(
        "veb_id",
        ForeignKey("venta_boutique.veb_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=True,
    )
    pago_pedido_id: Mapped[int | None] = mapped_column(
        "ppd_id",
        ForeignKey("pago_pedido.ppd_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=True,
    )
    salida_flete_id: Mapped[int | None] = mapped_column(
        "sfl_id",
        ForeignKey("salida_flete.sfl_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=True,
    )
    moneda_id: Mapped[int | None] = mapped_column(
        "mon_id",
        ForeignKey("moneda.mon_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=True,
    )
    codigo: Mapped[str] = mapped_column("coi_cod", String(30), nullable=False, unique=True)
    fecha: Mapped[datetime] = mapped_column("coi_fec", DateTime(timezone=True), server_default=func.now(), nullable=False)
    nombre_cliente: Mapped[str | None] = mapped_column("coi_nom_cliente", String(150))
    ci_nit_cliente: Mapped[str | None] = mapped_column("coi_ci_nit_cliente", String(30))
    celular_cliente: Mapped[str | None] = mapped_column("coi_cel_cliente", String(30))
    subtotal: Mapped[float] = mapped_column("coi_subtotal", Numeric(10, 2), nullable=False, default=0)
    descuento: Mapped[float] = mapped_column("coi_descuento", Numeric(10, 2), nullable=False, default=0)
    total: Mapped[float] = mapped_column("coi_total", Numeric(10, 2), nullable=False, default=0)
    total_moneda_original: Mapped[float] = mapped_column("coi_total_moneda_orig", Numeric(10, 2), nullable=False, default=0)
    saldo_posterior: Mapped[float] = mapped_column("coi_saldo_posterior", Numeric(10, 2), nullable=False, default=0)
    garantia: Mapped[float] = mapped_column("coi_garantia", Numeric(10, 2), nullable=False, default=0)
    tipo_cambio_usado: Mapped[float] = mapped_column("coi_tipo_cambio_usado", Numeric(12, 4), nullable=False, default=1)
    metodo_pago: Mapped[MetodoPagoEnum | None] = mapped_column("coi_metodo_pago", metodo_pago_enum)
    estado: Mapped[EstadoComprobanteEnum] = mapped_column(
        "coi_estado",
        estado_comprobante_enum,
        nullable=False,
        default=EstadoComprobanteEnum.EMITIDO,
        server_default=EstadoComprobanteEnum.EMITIDO.value,
    )
    fecha_cambio_estado: Mapped[datetime | None] = mapped_column("coi_fec_camb_est", DateTime(timezone=True))
    motivo_cambio_estado: Mapped[str | None] = mapped_column("coi_motivo_camb_est", Text)
    habilitado: Mapped[bool] = mapped_column("coi_hab", Boolean, default=True, nullable=False)

    tipo_comprobante = relationship("TipoComprobante", back_populates="comprobantes")
    cliente = relationship("Cliente")
    usuario = relationship("Usuario")
    moneda = relationship("Moneda")
    venta_boutique = relationship("VentaBoutique", back_populates="comprobante")
    pago_pedido = relationship("PagoPedido", back_populates="comprobante")
    salida_flete = relationship("SalidaFlete", back_populates="comprobante")
    detalles = relationship("DetalleComprobante", back_populates="comprobante", cascade="all, delete-orphan")

    @validates(
        "codigo",
        "nombre_cliente",
        "ci_nit_cliente",
        "celular_cliente",
        "motivo_cambio_estado",
    )
    def normalize_text(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()


class DetalleComprobante(Base):
    __tablename__ = "detalle_comprobante"
    __table_args__ = (
        CheckConstraint("dco_descuento <= (dco_cantidad * dco_precio_unidad)", name="ck_detalle_comprobante_descuento"),
        CheckConstraint("dco_subtotal = round(dco_cantidad * dco_precio_unidad - dco_descuento, 2)", name="ck_detalle_comprobante_subtotal"),
        CheckConstraint(
            "dco_cantidad > 0 and dco_precio_unidad >= 0 and dco_descuento >= 0 and dco_subtotal >= 0",
            name="ck_detalle_comprobante_montos",
        ),
        Index("ix_dco_coi_id", "coi_id"),
    )

    id: Mapped[int] = mapped_column("dco_id", BigInteger, Identity(always=True), primary_key=True)
    comprobante_id: Mapped[int] = mapped_column(
        "coi_id",
        ForeignKey("comprobante_interno.coi_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    concepto: Mapped[str] = mapped_column("dco_concepto", String(150), nullable=False)
    cantidad: Mapped[float] = mapped_column("dco_cantidad", Numeric(10, 2), nullable=False, default=1)
    precio_unidad: Mapped[float] = mapped_column("dco_precio_unidad", Numeric(10, 2), nullable=False)
    descuento: Mapped[float] = mapped_column("dco_descuento", Numeric(10, 2), nullable=False, default=0)
    subtotal: Mapped[float] = mapped_column("dco_subtotal", Numeric(10, 2), nullable=False)
    observaciones: Mapped[str | None] = mapped_column("dco_obs", String(150))

    comprobante = relationship("ComprobanteInterno", back_populates="detalles")

    @validates("concepto", "observaciones")
    def normalize_text(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()
