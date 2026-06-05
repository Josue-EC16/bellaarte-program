from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, Computed, DateTime, Enum as SqlEnum, ForeignKey, Identity, Index, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.base import Base
from app.models.boutique_enums import EstadoCorteCajaEnum, EstadoEgresoEnum, TipoEgresoEnum


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
        CheckConstraint(
            "((cco_estado = 'abierto' and cco_fec_cierre is null) or "
            "(cco_estado in ('cerrado', 'cerrado_observado') and cco_fec_cierre is not null))",
            name="ck_cco_cierre",
        ),
        Index("ix_cco_cajero_estado", "usu_id_cajero", "cco_estado"),
        Index("ix_cco_apertura_cierre", "cco_fec_apertura", "cco_fec_cierre"),
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
