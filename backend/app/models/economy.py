from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, Computed, DateTime, Enum as SqlEnum, ForeignKey, Identity, Index, Integer, Numeric, SmallInteger, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.base import Base
from app.models.boutique_enums import EstadoCorteCajaEnum, EstadoEgresoEnum, TipoEgresoEnum
from app.models.boutique_sale import metodo_pago_enum


tipo_egreso_enum = SqlEnum(
    TipoEgresoEnum,
    name="tipo_egreso",
    values_callable=lambda enum_cls: [item.value for item in enum_cls],
    create_type=False,
)
estado_egreso_enum = SqlEnum(
    EstadoEgresoEnum,
    name="estado_egreso",
    values_callable=lambda enum_cls: [item.value for item in enum_cls],
    create_type=False,
)
estado_corte_caja_enum = SqlEnum(
    EstadoCorteCajaEnum,
    name="estado_corte_caja",
    values_callable=lambda enum_cls: [item.value for item in enum_cls],
    create_type=False,
)


class CorteCaja(Base):
    __tablename__ = "corte_caja"
    __table_args__ = (
        CheckConstraint("cco_fondo_asignado >= 0", name="ck_cco_fondo"),
        CheckConstraint("control_version in (0, 1)", name="ck_cco_control_version"),
        CheckConstraint("control_version = 0 or cco_estado = 'abierto' or cierre_snapshot is not null", name="ck_cco_snapshot"),
        CheckConstraint(
            "((cco_estado = 'abierto' and cco_fec_cierre is null) or "
            "(cco_estado in ('cerrado', 'cerrado_observado') and cco_fec_cierre is not null))",
            name="ck_cco_cierre",
        ),
        Index("ix_cco_cajero_estado", "usu_id_cajero", "cco_estado"),
        Index("ix_cco_apertura_cierre", "cco_fec_apertura", "cco_fec_cierre"),
        Index("idx_cco_estado_apertura", "cco_estado", "cco_fec_apertura"),
        Index("idx_cco_cajero_apertura", "usu_id_cajero", "cco_fec_apertura"),
        Index("idx_cco_admin_apertura", "usu_id_admin", "cco_fec_apertura"),
        Index("uq_corte_abierto_cajero", "usu_id_cajero", unique=True, postgresql_where=text("cco_estado = 'abierto'")),
    )

    id: Mapped[int] = mapped_column("cco_id", BigInteger, Identity(always=True), primary_key=True)
    cajero_id: Mapped[int] = mapped_column(
        "usu_id_cajero",
        ForeignKey("usuarios.id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    admin_id: Mapped[int] = mapped_column(
        "usu_id_admin",
        ForeignKey("usuarios.id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    fecha_apertura: Mapped[datetime] = mapped_column("cco_fec_apertura", DateTime(timezone=True), nullable=False, server_default=func.now())
    fecha_cierre: Mapped[datetime | None] = mapped_column("cco_fec_cierre", DateTime(timezone=True))
    control_version: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1, server_default="0")
    cierre_snapshot: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True))
    fondo_asignado: Mapped[float] = mapped_column("cco_fondo_asignado", Numeric(12, 2), nullable=False, default=0, server_default="0")
    observaciones_apertura: Mapped[str | None] = mapped_column("cco_obs_apertura", Text)
    observaciones_cierre: Mapped[str | None] = mapped_column("cco_obs_cierre", Text)
    estado: Mapped[EstadoCorteCajaEnum] = mapped_column(
        "cco_estado",
        estado_corte_caja_enum,
        nullable=False,
        default=EstadoCorteCajaEnum.ABIERTO,
        server_default=EstadoCorteCajaEnum.ABIERTO.value,
    )

    cajero = relationship("Usuario", foreign_keys=[cajero_id])
    admin = relationship("Usuario", foreign_keys=[admin_id])
    egresos = relationship("Egreso", back_populates="corte")

    @validates("observaciones_apertura", "observaciones_cierre")
    def normalize_text(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()


class Egreso(Base):
    __tablename__ = "egreso"
    __table_args__ = (
        CheckConstraint(
            "((egr_estado = 'registrado' and egr_fec_camb_est is null and egr_motivo_camb_est is null) or "
            "(egr_estado = 'anulado' and egr_fec_camb_est is not null and egr_motivo_camb_est is not null))",
            name="ck_egr_cambio_estado",
        ),
        CheckConstraint("egr_cantidad > 0", name="ck_egr_cantidad"),
        CheckConstraint("egr_precio_unidad > 0", name="ck_egr_precio_unidad"),
        CheckConstraint(
            "("
            "(egr_tipo <> 'devolucion' and egr_tabla_ref is null and egr_id_ref is null)"
            " or "
            "(egr_tipo = 'devolucion' and egr_tabla_ref in ('venta_boutique', 'pago_pedido', 'salida_flete') and egr_id_ref is not null)"
            ")",
            name="ck_egr_ref_devolucion",
        ),
        Index("ix_egr_fec_estado", "egr_fec", "egr_estado"),
        Index("ix_egr_cco_id", "cco_id"),
        Index("ix_egr_usu_fec", "usu_id", "egr_fec"),
        Index("ix_egr_tipo_fec", "egr_tipo", "egr_fec"),
        Index("ix_egr_ref", "egr_tabla_ref", "egr_id_ref"),
        Index("idx_egr_estado_fec", "egr_estado", "egr_fec"),
        Index("idx_egr_cco_fec", "cco_id", "egr_fec"),
    )

    id: Mapped[int] = mapped_column("egr_id", BigInteger, Identity(always=True), primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        "usu_id",
        ForeignKey("usuarios.id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=True,
    )
    corte_id: Mapped[int | None] = mapped_column(
        "cco_id",
        ForeignKey("corte_caja.cco_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=True,
    )
    fecha: Mapped[datetime] = mapped_column("egr_fec", DateTime(timezone=True), nullable=False, server_default=func.now())
    tipo: Mapped[TipoEgresoEnum] = mapped_column("egr_tipo", tipo_egreso_enum, nullable=False)
    concepto: Mapped[str] = mapped_column("egr_concepto", String(150), nullable=False)
    cantidad: Mapped[float] = mapped_column("egr_cantidad", Numeric(12, 2), nullable=False)
    precio_unidad: Mapped[float] = mapped_column("egr_precio_unidad", Numeric(12, 2), nullable=False)
    beneficiario: Mapped[str | None] = mapped_column("egr_beneficiario", String(120))
    monto: Mapped[float] = mapped_column(
        "egr_monto",
        Numeric(12, 2),
        Computed("round(egr_cantidad * egr_precio_unidad, 2)", persisted=True),
        nullable=False,
    )
    observaciones_1: Mapped[str | None] = mapped_column("egr_obs1", Text)
    observaciones_2: Mapped[str | None] = mapped_column("egr_obs2", Text)
    estado: Mapped[EstadoEgresoEnum] = mapped_column(
        "egr_estado",
        estado_egreso_enum,
        nullable=False,
        default=EstadoEgresoEnum.REGISTRADO,
        server_default=EstadoEgresoEnum.REGISTRADO.value,
    )
    fecha_cambio_estado: Mapped[datetime | None] = mapped_column("egr_fec_camb_est", DateTime(timezone=True))
    motivo_cambio_estado: Mapped[str | None] = mapped_column("egr_motivo_camb_est", Text)
    tabla_referencia: Mapped[str | None] = mapped_column("egr_tabla_ref", String(50))
    id_referencia: Mapped[int | None] = mapped_column("egr_id_ref", BigInteger)
    metodo_pago = mapped_column(metodo_pago_enum, nullable=True)

    usuario = relationship("Usuario")
    corte = relationship("CorteCaja", back_populates="egresos")

    @validates("concepto", "beneficiario", "observaciones_1", "observaciones_2", "motivo_cambio_estado")
    def normalize_upper_text(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()

    @validates("tabla_referencia")
    def normalize_table_ref(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().lower()


class MovimientoEconomico(Base):
    """Append-only cash attribution; commercial income remains in its source."""

    __tablename__ = "movimiento_economico"
    __table_args__ = (
        CheckConstraint("monto_bob > 0 and monto_original > 0", name="ck_mov_montos"),
        CheckConstraint("direccion in (-1, 0, 1)", name="ck_mov_direccion"),
        CheckConstraint("evento in ('fondo','ingreso','egreso','ajuste_egreso','garantia_recibida','garantia_devuelta','garantia_retenida')", name="ck_mov_evento"),
        CheckConstraint("((evento in ('fondo','ingreso','ajuste_egreso','garantia_recibida') and direccion = 1) or (evento in ('egreso','garantia_devuelta') and direccion = -1) or (evento = 'garantia_retenida' and direccion = 0))", name="ck_mov_evento_direccion"),
        CheckConstraint("(origen_tipo is null) = (origen_id is null)", name="ck_mov_origen"),
        CheckConstraint("origen_tipo is null or origen_tipo in ('venta_boutique','pago_pedido','salida_flete','egreso','corte_caja')", name="ck_mov_origen_tipo"),
        CheckConstraint("evento in ('ingreso') or moneda_codigo = 'BOB'", name="ck_mov_moneda"),
        CheckConstraint("moneda_codigo <> 'BOB' or monto_original = monto_bob", name="ck_mov_bob_equivalencia"),
        CheckConstraint("secuencia > 0", name="ck_mov_secuencia"),
        UniqueConstraint("evento", "origen_tipo", "origen_id", "secuencia", name="uq_mov_evento_origen"),
        Index("ix_mov_corte_fecha", "corte_id", "fecha"),
        Index("ix_mov_origen", "origen_tipo", "origen_id"),
        Index("ix_mov_fecha_evento", "fecha", "evento"),
        Index("uq_mov_evento_unico", "evento", "origen_tipo", "origen_id", unique=True, postgresql_where=text("evento in ('fondo','ingreso','egreso','ajuste_egreso','garantia_recibida')")),
    )
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    corte_id: Mapped[int | None] = mapped_column(ForeignKey("corte_caja.cco_id", ondelete="RESTRICT"))
    actor_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    evento: Mapped[str] = mapped_column(String(30), nullable=False)
    direccion: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    monto_bob: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    monto_original: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    moneda_codigo: Mapped[str] = mapped_column(String(10), nullable=False)
    metodo_pago = mapped_column(metodo_pago_enum, nullable=False)
    origen_tipo: Mapped[str | None] = mapped_column(String(30))
    origen_id: Mapped[int | None] = mapped_column(BigInteger)
    secuencia: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    egreso_id: Mapped[int | None] = mapped_column(ForeignKey("egreso.egr_id", ondelete="RESTRICT"))
    salida_flete_id: Mapped[int | None] = mapped_column(ForeignKey("salida_flete.sfl_id", ondelete="RESTRICT"))
    motivo: Mapped[str | None] = mapped_column(Text)


class ConstanciaDevolucion(Base):
    __tablename__ = "constancia_devolucion"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    egreso_id: Mapped[int] = mapped_column(ForeignKey("egreso.egr_id", ondelete="RESTRICT"), nullable=False, unique=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)


class SolicitudEconomica(Base):
    __tablename__ = "solicitud_economica"
    __table_args__ = (
        UniqueConstraint("actor_id", "operacion", "clave", name="uq_solicitud_actor_operacion_clave"),
        CheckConstraint("length(payload_hash) = 64", name="ck_solicitud_hash"),
    )
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    operacion: Mapped[str] = mapped_column(String(80), nullable=False)
    clave: Mapped[str] = mapped_column(String(120), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    resultado: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True))
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
