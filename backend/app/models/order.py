from datetime import date, datetime, time

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Computed, Date, DateTime, Enum as SqlEnum, ForeignKey, Identity, Index, Integer, Numeric, SmallInteger, String, Text, Time, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.base import Base
from app.models.boutique_enums import (
    EstadoPagoPedidoEnum,
    EstadoPedidoGeneralEnum,
    MetodoPagoEnum,
    MotivoDescuentoPedidoEnum,
    PruebaEstadoPedidoEnum,
    TipoPedidoEnum,
    TipoVestidoEnum,
)


tipo_pedido_enum = SqlEnum(TipoPedidoEnum, name="tipo_pedido", values_callable=lambda enum_cls: [item.value for item in enum_cls], create_type=False)
motivo_descuento_pedido_enum = SqlEnum(
    MotivoDescuentoPedidoEnum,
    name="motivo_descuento_pedido",
    values_callable=lambda enum_cls: [item.value for item in enum_cls],
    create_type=False,
)
estado_pedido_general_enum = SqlEnum(
    EstadoPedidoGeneralEnum,
    name="estado_pedido_general",
    values_callable=lambda enum_cls: [item.value for item in enum_cls],
    create_type=False,
)
estado_pago_pedido_enum = SqlEnum(
    EstadoPagoPedidoEnum,
    name="estado_pago_pedido",
    values_callable=lambda enum_cls: [item.value for item in enum_cls],
    create_type=False,
)
prueba_estado_pedido_enum = SqlEnum(
    PruebaEstadoPedidoEnum,
    name="prueba_estado_pedido",
    values_callable=lambda enum_cls: [item.value for item in enum_cls],
    create_type=False,
)
tipo_vestido_enum = SqlEnum(TipoVestidoEnum, name="tipo_vestido", values_callable=lambda enum_cls: [item.value for item in enum_cls], create_type=False)
metodo_pago_enum = SqlEnum(MetodoPagoEnum, name="metodo_pago", values_callable=lambda enum_cls: [item.value for item in enum_cls], create_type=False)


class Pedido(Base):
    __tablename__ = "pedido"
    __table_args__ = (
        CheckConstraint(
            "(ped_estado_general = 'activo' and ped_fec_camb_est is null and ped_motivo_camb_est is null) or "
            "(ped_estado_general = 'entregado') or "
            "(ped_estado_general in ('cancelado', 'inactivo') and ped_fec_camb_est is not null and ped_motivo_camb_est is not null)",
            name="ck_ped_cambio_estado",
        ),
        CheckConstraint("ped_precio >= 0", name="ck_ped_precio"),
        CheckConstraint("ped_total_pagado >= 0", name="ck_ped_total_pagado"),
        CheckConstraint("ped_saldo >= 0", name="ck_ped_saldo"),
        CheckConstraint("ped_descuento is null or (ped_descuento >= 0 and ped_descuento <= ped_precio)", name="ck_ped_descuento"),
        CheckConstraint(
            "(ped_descuento is null and ped_motivo_descuento is null) or (ped_descuento is not null and ped_motivo_descuento is not null)",
            name="ck_ped_motivo_descuento",
        ),
        CheckConstraint("(ped_viaje = false) or (ped_pais_destino is not null or ped_ciudad_destino is not null)", name="ck_ped_destino_viaje"),
        Index("ix_pedido_cliente_estado", "cli_id", "ped_estado_general", "ped_hab"),
        Index("ix_pedido_entrega", "ped_fec_de_entrega"),
        Index("idx_ped_fec_reg", "ped_fec_reg_contrato"),
        Index("idx_ped_estado_fec_reg", "ped_estado_general", "ped_fec_reg_contrato"),
        Index("idx_ped_estado_entrega", "ped_estado_general", "ped_fec_de_entrega"),
        Index("idx_ped_estado_cambio_fec", "ped_estado_general", "ped_fec_camb_est"),
        Index("idx_ped_tipo_fec_reg", "ped_tipo", "ped_fec_reg_contrato"),
        Index("idx_ped_usu_estado", "ped_usu_encargado", "ped_estado_general"),
        Index("idx_ped_viaje_estado", "ped_viaje", "ped_estado_general"),
    )

    id: Mapped[int] = mapped_column("ped_id", BigInteger, Identity(always=True), primary_key=True)
    cliente_id: Mapped[int] = mapped_column("cli_id", ForeignKey("cliente.cli_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    codigo: Mapped[str] = mapped_column("ped_cod", String(40), unique=True, nullable=False)
    tipo: Mapped[TipoPedidoEnum] = mapped_column("ped_tipo", tipo_pedido_enum, nullable=False)
    fecha_contrato: Mapped[datetime] = mapped_column("ped_fec_reg_contrato", DateTime(timezone=True), server_default=func.now(), nullable=False)
    usuario_encargado_id: Mapped[int] = mapped_column("ped_usu_encargado", ForeignKey("usuarios.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    fecha_entrega: Mapped[date] = mapped_column("ped_fec_de_entrega", Date, nullable=False)
    fecha_entrega_final: Mapped[date | None] = mapped_column("ped_fec_entrega_final", Date)
    viaje: Mapped[bool] = mapped_column("ped_viaje", Boolean, default=False, nullable=False)
    pais_destino: Mapped[str | None] = mapped_column("ped_pais_destino", String(50))
    ciudad_destino: Mapped[str | None] = mapped_column("ped_ciudad_destino", String(50))
    precio: Mapped[float] = mapped_column("ped_precio", Numeric(12, 2), nullable=False, default=0)
    descuento: Mapped[float | None] = mapped_column("ped_descuento", Numeric(12, 2))
    motivo_descuento: Mapped[MotivoDescuentoPedidoEnum | None] = mapped_column("ped_motivo_descuento", motivo_descuento_pedido_enum)
    precio_total: Mapped[float] = mapped_column("ped_pre_tot", Numeric(12, 2), Computed("round(ped_precio - coalesce(ped_descuento, 0), 2)", persisted=True), nullable=False)
    total_pagado: Mapped[float] = mapped_column("ped_total_pagado", Numeric(12, 2), default=0, nullable=False)
    saldo: Mapped[float] = mapped_column("ped_saldo", Numeric(12, 2), default=0, nullable=False)
    observaciones: Mapped[str | None] = mapped_column("ped_obs", Text)
    estado_general: Mapped[EstadoPedidoGeneralEnum] = mapped_column(
        "ped_estado_general",
        estado_pedido_general_enum,
        default=EstadoPedidoGeneralEnum.ACTIVO,
        server_default=EstadoPedidoGeneralEnum.ACTIVO.value,
        nullable=False,
    )
    fecha_cambio_estado: Mapped[datetime | None] = mapped_column("ped_fec_camb_est", DateTime(timezone=True))
    motivo_cambio_estado: Mapped[str | None] = mapped_column("ped_motivo_camb_est", Text)
    habilitado: Mapped[bool] = mapped_column("ped_hab", Boolean, default=True, nullable=False)

    cliente = relationship("Cliente")
    usuario_encargado = relationship("Usuario")
    vestido = relationship("PedidoVestido", back_populates="pedido", uselist=False, cascade="all, delete-orphan")
    velo = relationship("PedidoVelo", back_populates="pedido", uselist=False, cascade="all, delete-orphan")
    cola = relationship("PedidoCola", back_populates="pedido", uselist=False, cascade="all, delete-orphan")
    manga = relationship("PedidoManga", back_populates="pedido", uselist=False, cascade="all, delete-orphan")
    bouquet = relationship("PedidoBouquet", back_populates="pedido", uselist=False, cascade="all, delete-orphan")
    otro = relationship("PedidoOtro", back_populates="pedido", uselist=False, cascade="all, delete-orphan")
    pruebas = relationship("PruebaPedido", back_populates="pedido")
    pagos = relationship("PagoPedido", back_populates="pedido")

    @validates("codigo", "pais_destino", "ciudad_destino", "observaciones", "motivo_cambio_estado")
    def normalize_text(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()


class PedidoVestido(Base):
    __tablename__ = "pedido_vestido"
    __table_args__ = tuple(
        CheckConstraint(f"{column} is null or {column} >= 0", name=f"ck_{column}")
        for column in ("pdv_ane_esp", "pdv_tal_esp", "pdv_tal_del", "pdv_con_cin", "pdv_con_cad", "pdv_lar_fal", "pdv_sisa", "pdv_anb_bus", "pdv_sep_bus", "pdv_tal_bus", "pdv_tal_cos")
    )

    id: Mapped[int] = mapped_column("pdv_id", BigInteger, Identity(always=True), primary_key=True)
    pedido_id: Mapped[int] = mapped_column("ped_id", ForeignKey("pedido.ped_id", onupdate="CASCADE", ondelete="RESTRICT"), unique=True, nullable=False)
    tipo_vestido: Mapped[TipoVestidoEnum] = mapped_column("pdv_tipo_vestido", tipo_vestido_enum, nullable=False)
    color_principal: Mapped[str] = mapped_column("pdv_color_prin", String(50), nullable=False)
    color_secundario: Mapped[str | None] = mapped_column("pdv_color_secu", String(50))
    descripcion_material: Mapped[str] = mapped_column("pdv_descr_material", Text, nullable=False)
    descripcion_diseno: Mapped[str] = mapped_column("pdv_descr_diseno", Text, nullable=False)
    descripcion_adicional: Mapped[str | None] = mapped_column("pdv_descripcion_2", Text)
    ancho_espalda: Mapped[float | None] = mapped_column("pdv_ane_esp", Numeric(6, 2))
    talle_espalda: Mapped[float | None] = mapped_column("pdv_tal_esp", Numeric(6, 2))
    talle_delantero: Mapped[float | None] = mapped_column("pdv_tal_del", Numeric(6, 2))
    contorno_cintura: Mapped[float | None] = mapped_column("pdv_con_cin", Numeric(6, 2))
    contorno_cadera: Mapped[float | None] = mapped_column("pdv_con_cad", Numeric(6, 2))
    largo_falda: Mapped[float | None] = mapped_column("pdv_lar_fal", Numeric(6, 2))
    sisa: Mapped[float | None] = mapped_column("pdv_sisa", Numeric(6, 2))
    ancho_busto: Mapped[float | None] = mapped_column("pdv_anb_bus", Numeric(6, 2))
    separacion_busto: Mapped[float | None] = mapped_column("pdv_sep_bus", Numeric(6, 2))
    talle_busto: Mapped[float | None] = mapped_column("pdv_tal_bus", Numeric(6, 2))
    talle_costado: Mapped[float | None] = mapped_column("pdv_tal_cos", Numeric(6, 2))
    observaciones: Mapped[str | None] = mapped_column("pdv_obs", Text)

    pedido = relationship("Pedido", back_populates="vestido")

    @validates("color_principal", "color_secundario", "descripcion_material", "descripcion_diseno", "descripcion_adicional", "observaciones")
    def normalize_text(self, _key: str, value: str | None) -> str | None:
        return value.strip().upper() if value is not None else None


class _SimplePedidoDetailMixin:
    @validates("color_principal", "color_secundario", "observaciones")
    def normalize_text(self, _key: str, value: str | None) -> str | None:
        return value.strip().upper() if value is not None else None


class PedidoVelo(_SimplePedidoDetailMixin, Base):
    __tablename__ = "pedido_velo"
    __table_args__ = (
        CheckConstraint("pdve_largo > 0", name="ck_pdve_largo"),
        CheckConstraint("pdve_ancho is null or pdve_ancho >= 0", name="ck_pdve_ancho"),
        CheckConstraint("pdve_capas is null or pdve_capas > 0", name="ck_pdve_capas"),
    )
    id: Mapped[int] = mapped_column("pdve_id", BigInteger, Identity(always=True), primary_key=True)
    pedido_id: Mapped[int] = mapped_column("ped_id", ForeignKey("pedido.ped_id", onupdate="CASCADE", ondelete="RESTRICT"), unique=True, nullable=False)
    tipo: Mapped[str | None] = mapped_column("pdve_tipo_velo", String(100))
    color_principal: Mapped[str] = mapped_column("pdve_color_prin", String(50), nullable=False)
    color_secundario: Mapped[str | None] = mapped_column("pdve_color_secu", String(50))
    largo: Mapped[float] = mapped_column("pdve_largo", Numeric(6, 2), nullable=False)
    ancho: Mapped[float | None] = mapped_column("pdve_ancho", Numeric(6, 2))
    capas: Mapped[int | None] = mapped_column("pdve_capas", SmallInteger)
    borde: Mapped[str | None] = mapped_column("pdve_borde", String(100))
    decoracion: Mapped[str | None] = mapped_column("pdve_decoracion", Text)
    material: Mapped[str | None] = mapped_column("pdve_material", String(100))
    observaciones: Mapped[str | None] = mapped_column("pdve_obs", Text)
    pedido = relationship("Pedido", back_populates="velo")

    @validates("tipo", "borde", "decoracion", "material")
    def normalize_velo_text(self, _key: str, value: str | None) -> str | None:
        return value.strip().upper() if value is not None else None


class PedidoCola(_SimplePedidoDetailMixin, Base):
    __tablename__ = "pedido_cola"
    __table_args__ = (CheckConstraint("pdco_largo > 0", name="ck_pdco_largo"), CheckConstraint("pdco_ancho is null or pdco_ancho >= 0", name="ck_pdco_ancho"))
    id: Mapped[int] = mapped_column("pdco_id", BigInteger, Identity(always=True), primary_key=True)
    pedido_id: Mapped[int] = mapped_column("ped_id", ForeignKey("pedido.ped_id", onupdate="CASCADE", ondelete="RESTRICT"), unique=True, nullable=False)
    tipo: Mapped[str | None] = mapped_column("pdco_tipo_cola", String(100))
    color_principal: Mapped[str] = mapped_column("pdco_color_prin", String(50), nullable=False)
    color_secundario: Mapped[str | None] = mapped_column("pdco_color_secun", String(50))
    largo: Mapped[float] = mapped_column("pdco_largo", Numeric(6, 2), nullable=False)
    ancho: Mapped[float | None] = mapped_column("pdco_ancho", Numeric(6, 2))
    material: Mapped[str | None] = mapped_column("pdco_material", String(100))
    decoracion: Mapped[str | None] = mapped_column("pdco_decoracion", Text)
    observaciones: Mapped[str | None] = mapped_column("pdco_obs", Text)
    pedido = relationship("Pedido", back_populates="cola")

    @validates("tipo", "material", "decoracion")
    def normalize_cola_text(self, _key: str, value: str | None) -> str | None:
        return value.strip().upper() if value is not None else None


class PedidoManga(_SimplePedidoDetailMixin, Base):
    __tablename__ = "pedido_manga"
    __table_args__ = (
        CheckConstraint("pdma_lar_man > 0", name="ck_pdma_lar_man"),
        CheckConstraint("pdma_bra >= 0", name="ck_pdma_bra"),
        CheckConstraint("pdma_pun >= 0", name="ck_pdma_pun"),
    )
    id: Mapped[int] = mapped_column("pdma_id", BigInteger, Identity(always=True), primary_key=True)
    pedido_id: Mapped[int] = mapped_column("ped_id", ForeignKey("pedido.ped_id", onupdate="CASCADE", ondelete="RESTRICT"), unique=True, nullable=False)
    tipo: Mapped[str | None] = mapped_column("pdma_tipo_manga", String(100))
    color_principal: Mapped[str] = mapped_column("pdma_color_prin", String(50), nullable=False)
    color_secundario: Mapped[str | None] = mapped_column("pdma_color_secun", String(50))
    largo_manga: Mapped[float] = mapped_column("pdma_lar_man", Numeric(6, 2), nullable=False)
    brazo: Mapped[float] = mapped_column("pdma_bra", Numeric(6, 2), nullable=False)
    puno: Mapped[float] = mapped_column("pdma_pun", Numeric(6, 2), nullable=False)
    material: Mapped[str | None] = mapped_column("pdma_material", String(100))
    decoracion: Mapped[str | None] = mapped_column("pdma_decoracion", Text)
    observaciones: Mapped[str | None] = mapped_column("pdma_obs", Text)
    pedido = relationship("Pedido", back_populates="manga")

    @validates("tipo", "material", "decoracion")
    def normalize_manga_text(self, _key: str, value: str | None) -> str | None:
        return value.strip().upper() if value is not None else None


class PedidoBouquet(_SimplePedidoDetailMixin, Base):
    __tablename__ = "pedido_bouquet"
    __table_args__ = (CheckConstraint("pdb_largo >= 0", name="ck_pdb_largo"), CheckConstraint("pdb_ancho is null or pdb_ancho >= 0", name="ck_pdb_ancho"))
    id: Mapped[int] = mapped_column("pdb_id", BigInteger, Identity(always=True), primary_key=True)
    pedido_id: Mapped[int] = mapped_column("ped_id", ForeignKey("pedido.ped_id", onupdate="CASCADE", ondelete="RESTRICT"), unique=True, nullable=False)
    tipo: Mapped[str] = mapped_column("pdb_tipo_bouquet", String(100), nullable=False)
    color_principal: Mapped[str] = mapped_column("pdb_color_prin", String(50), nullable=False)
    color_secundario: Mapped[str | None] = mapped_column("pdb_color_secun", String(50))
    largo: Mapped[float] = mapped_column("pdb_largo", Numeric(6, 2), nullable=False)
    ancho: Mapped[float | None] = mapped_column("pdb_ancho", Numeric(6, 2))
    tipo_flor: Mapped[str | None] = mapped_column("pdb_tipo_flor", String(100))
    decoracion: Mapped[str | None] = mapped_column("pdb_decoracion", Text)
    observaciones: Mapped[str | None] = mapped_column("pdb_obs", Text)
    pedido = relationship("Pedido", back_populates="bouquet")

    @validates("tipo", "tipo_flor", "decoracion")
    def normalize_bouquet_text(self, _key: str, value: str | None) -> str | None:
        return value.strip().upper() if value is not None else None


class PedidoOtro(_SimplePedidoDetailMixin, Base):
    __tablename__ = "pedido_otro"
    __table_args__ = (CheckConstraint("pdot_largo is null or pdot_largo >= 0", name="ck_pdot_largo"), CheckConstraint("pdot_ancho is null or pdot_ancho >= 0", name="ck_pdot_ancho"))
    id: Mapped[int] = mapped_column("pdot_id", BigInteger, Identity(always=True), primary_key=True)
    pedido_id: Mapped[int] = mapped_column("ped_id", ForeignKey("pedido.ped_id", onupdate="CASCADE", ondelete="RESTRICT"), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column("pdot_nom", String(80), nullable=False)
    color_principal: Mapped[str] = mapped_column("pdot_color_prin", String(50), nullable=False)
    color_secundario: Mapped[str | None] = mapped_column("pdot_color_secun", String(50))
    largo: Mapped[float | None] = mapped_column("pdot_largo", Numeric(6, 2))
    ancho: Mapped[float | None] = mapped_column("pdot_ancho", Numeric(6, 2))
    descripcion: Mapped[str | None] = mapped_column("pdot_descripcion", Text)
    observaciones: Mapped[str | None] = mapped_column("pdot_obs", Text)
    pedido = relationship("Pedido", back_populates="otro")

    @validates("nombre", "descripcion")
    def normalize_otro_text(self, _key: str, value: str | None) -> str | None:
        return value.strip().upper() if value is not None else None


class PruebaPedido(Base):
    __tablename__ = "prueba_pedido"
    __table_args__ = (
        CheckConstraint("prp_num > 0", name="ck_prp_num"),
        UniqueConstraint("ped_id", "prp_num", name="uq_prueba_pedido_num"),
        Index("ix_prp_fec_estado", "prp_fec", "prp_estado"),
        Index("idx_prp_estado_fec", "prp_estado", "prp_fec"),
        Index("idx_prp_ped_fec", "ped_id", "prp_fec"),
    )
    id: Mapped[int] = mapped_column("prp_id", BigInteger, Identity(always=True), primary_key=True)
    pedido_id: Mapped[int] = mapped_column("ped_id", ForeignKey("pedido.ped_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    numero: Mapped[int] = mapped_column("prp_num", SmallInteger, nullable=False)
    fecha: Mapped[date] = mapped_column("prp_fec", Date, nullable=False)
    hora: Mapped[time | None] = mapped_column("prp_hor", Time)
    estado: Mapped[PruebaEstadoPedidoEnum] = mapped_column("prp_estado", prueba_estado_pedido_enum, nullable=False)
    observaciones: Mapped[str | None] = mapped_column("prp_obs", Text)
    pedido = relationship("Pedido", back_populates="pruebas")

    @validates("observaciones")
    def normalize_text(self, _key: str, value: str | None) -> str | None:
        return value.strip().upper() if value is not None else None


class PagoPedido(Base):
    __tablename__ = "pago_pedido"
    __table_args__ = (
        CheckConstraint(
            "(ppd_estado = 'registrado' and ppd_fec_camb_est is null and ppd_motivo_camb_est is null) or "
            "(ppd_estado = 'anulado' and ppd_fec_camb_est is not null and ppd_motivo_camb_est is not null)",
            name="ck_ppd_cambio_estado",
        ),
        CheckConstraint("ppd_monto > 0", name="ck_ppd_monto"),
        CheckConstraint("ppd_tipo_cambio_usado > 0", name="ck_ppd_tipo_cambio"),
        Index("ix_ppd_pedido_estado_fec", "ped_id", "ppd_estado", "ppd_fec"),
        Index("idx_ppd_fec", "ppd_fec"),
        Index("idx_ppd_estado_fec", "ppd_estado", "ppd_fec"),
        Index("idx_ppd_estado_cambio_fec", "ppd_estado", "ppd_fec_camb_est"),
        Index("idx_ppd_ped_fec", "ped_id", "ppd_fec"),
        Index("idx_ppd_usu_fec", "usu_id", "ppd_fec"),
        Index("idx_ppd_mon_fec", "mon_id", "ppd_fec"),
        Index("idx_ppd_metodo_fec", "ppd_metodo", "ppd_fec"),
    )
    id: Mapped[int] = mapped_column("ppd_id", BigInteger, Identity(always=True), primary_key=True)
    pedido_id: Mapped[int] = mapped_column("ped_id", ForeignKey("pedido.ped_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    usuario_id: Mapped[int] = mapped_column("usu_id", ForeignKey("usuarios.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    moneda_id: Mapped[int] = mapped_column("mon_id", ForeignKey("moneda.mon_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    fecha: Mapped[datetime] = mapped_column("ppd_fec", DateTime(timezone=True), server_default=func.now(), nullable=False)
    monto: Mapped[float] = mapped_column("ppd_monto", Numeric(12, 2), nullable=False)
    tipo_cambio_usado: Mapped[float] = mapped_column("ppd_tipo_cambio_usado", Numeric(12, 4), nullable=False, default=1)
    monto_bob: Mapped[float] = mapped_column("ppd_monto_bob", Numeric(12, 2), Computed("round(ppd_monto * ppd_tipo_cambio_usado, 2)", persisted=True), nullable=False)
    metodo_pago: Mapped[MetodoPagoEnum] = mapped_column("ppd_metodo", metodo_pago_enum, nullable=False)
    observaciones: Mapped[str | None] = mapped_column("ppd_obs1", Text)
    estado: Mapped[EstadoPagoPedidoEnum] = mapped_column("ppd_estado", estado_pago_pedido_enum, default=EstadoPagoPedidoEnum.REGISTRADO, server_default=EstadoPagoPedidoEnum.REGISTRADO.value, nullable=False)
    fecha_cambio_estado: Mapped[datetime | None] = mapped_column("ppd_fec_camb_est", DateTime(timezone=True))
    motivo_cambio_estado: Mapped[str | None] = mapped_column("ppd_motivo_camb_est", Text)
    pedido = relationship("Pedido", back_populates="pagos")
    usuario = relationship("Usuario")
    moneda = relationship("Moneda")
    comprobante = relationship("ComprobanteInterno", back_populates="pago_pedido", uselist=False)

    @validates("observaciones", "motivo_cambio_estado")
    def normalize_text(self, _key: str, value: str | None) -> str | None:
        return value.strip().upper() if value is not None else None
