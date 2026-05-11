from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, Enum as SqlEnum, ForeignKey, Identity, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.base import Base
from app.models.boutique_enums import MotivoEntradaTallerEnum, UnidadMedidaEnum


unidad_medida_enum = SqlEnum(
    UnidadMedidaEnum,
    name="unidad_medida",
    values_callable=lambda enum_cls: [item.value for item in enum_cls],
)
motivo_entrada_taller_enum = SqlEnum(
    MotivoEntradaTallerEnum,
    name="motivo_entrada_taller",
    values_callable=lambda enum_cls: [item.value for item in enum_cls],
)


class TipoInventarioTaller(Base):
    __tablename__ = "tipo_inventario_taller"

    id: Mapped[int] = mapped_column("tit_id", BigInteger, Identity(always=True), primary_key=True)
    nombre: Mapped[str] = mapped_column("tit_nom", String(100), unique=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column("tit_des", String(200))
    habilitado: Mapped[bool] = mapped_column("tit_hab", Boolean, default=True, nullable=False)
    fecha_registro: Mapped[datetime] = mapped_column("tit_fec_reg", DateTime(timezone=True), server_default=func.now(), nullable=False)

    items = relationship("InventarioTaller", back_populates="tipo")

    @validates("nombre", "descripcion")
    def normalize_uppercase(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()


class InventarioTaller(Base):
    __tablename__ = "inventario_taller"
    __table_args__ = (
        CheckConstraint("int_costo_ref >= 0", name="ck_int_costo_ref"),
        CheckConstraint("int_stock >= 0", name="ck_int_stock"),
        CheckConstraint("int_stock_min >= 0", name="ck_int_stock_min"),
        CheckConstraint("int_largo IS NULL OR int_largo >= 0", name="ck_int_largo"),
        CheckConstraint("int_ancho IS NULL OR int_ancho >= 0", name="ck_int_ancho"),
    )

    id: Mapped[int] = mapped_column("int_id", BigInteger, Identity(always=True), primary_key=True)
    tipo_id: Mapped[int] = mapped_column("tit_id", ForeignKey("tipo_inventario_taller.tit_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    proveedor_id: Mapped[int | None] = mapped_column("pro_id", ForeignKey("proveedor.pro_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=True)
    codigo: Mapped[str] = mapped_column("int_cod", String(40), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column("int_nom", String(100), nullable=False)
    color: Mapped[str] = mapped_column("int_color", String(50), nullable=False)
    largo: Mapped[float | None] = mapped_column("int_largo", Numeric(6, 2))
    ancho: Mapped[float | None] = mapped_column("int_ancho", Numeric(6, 2))
    material: Mapped[str | None] = mapped_column("int_material", String(80))
    descripcion: Mapped[str | None] = mapped_column("int_des", Text)
    costo_referencia: Mapped[float] = mapped_column("int_costo_ref", Numeric(12, 2), default=0, nullable=False)
    stock: Mapped[float] = mapped_column("int_stock", Numeric(12, 2), default=0, nullable=False)
    unidad_medida: Mapped[UnidadMedidaEnum] = mapped_column("int_uni_med", unidad_medida_enum, nullable=False)
    stock_minimo: Mapped[float] = mapped_column("int_stock_min", Numeric(12, 2), default=0, nullable=False)
    estado: Mapped[bool] = mapped_column("int_estado", Boolean, default=True, nullable=False)
    observaciones: Mapped[str | None] = mapped_column("int_obs", Text)
    fecha_registro: Mapped[datetime] = mapped_column("int_fec_reg", DateTime(timezone=True), server_default=func.now(), nullable=False)

    tipo = relationship("TipoInventarioTaller", back_populates="items")
    proveedor = relationship("Proveedor")
    entradas = relationship("EntradaInventarioTaller", back_populates="item")
    salidas = relationship("SalidaMaterialTaller", back_populates="item")

    @validates("codigo")
    def normalize_code(self, _key: str, value: str) -> str:
        return value.strip().upper()

    @validates("nombre", "color", "material", "descripcion", "observaciones")
    def normalize_uppercase(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()


class EntradaInventarioTaller(Base):
    __tablename__ = "entrada_inventario_taller"
    __table_args__ = (
        CheckConstraint("emt_can > 0", name="ck_emt_can"),
        CheckConstraint("emt_costo_unitario >= 0", name="ck_emt_costo_unitario"),
    )

    id: Mapped[int] = mapped_column("emt_id", BigInteger, Identity(always=True), primary_key=True)
    item_id: Mapped[int] = mapped_column("int_id", ForeignKey("inventario_taller.int_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    usuario_id: Mapped[int] = mapped_column("usu_id", ForeignKey("usuarios.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    proveedor_id: Mapped[int | None] = mapped_column("pro_id", ForeignKey("proveedor.pro_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=True)
    fecha: Mapped[datetime] = mapped_column("emt_fec", DateTime(timezone=True), server_default=func.now(), nullable=False)
    cantidad: Mapped[float] = mapped_column("emt_can", Numeric(12, 2), nullable=False)
    unidad_medida: Mapped[UnidadMedidaEnum] = mapped_column("emt_uni_med", unidad_medida_enum, nullable=False)
    costo_unitario: Mapped[float] = mapped_column("emt_costo_unitario", Numeric(12, 2), default=0, nullable=False)
    motivo: Mapped[MotivoEntradaTallerEnum] = mapped_column("emt_motivo", motivo_entrada_taller_enum, default=MotivoEntradaTallerEnum.ENTRADA_STOCK, nullable=False)
    documento_referencia: Mapped[str | None] = mapped_column("emt_doc_ref", String(80))
    observaciones: Mapped[str | None] = mapped_column("emt_obs", Text)
    estado: Mapped[bool] = mapped_column("emt_estado", Boolean, default=True, nullable=False)

    item = relationship("InventarioTaller", back_populates="entradas")
    usuario = relationship("Usuario")
    proveedor = relationship("Proveedor")

    @validates("documento_referencia", "observaciones")
    def normalize_uppercase(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()


class SalidaMaterialTaller(Base):
    __tablename__ = "salida_material_taller"
    __table_args__ = (
        CheckConstraint("smt_can > 0", name="ck_smt_can"),
    )

    id: Mapped[int] = mapped_column("smt_id", BigInteger, Identity(always=True), primary_key=True)
    item_id: Mapped[int] = mapped_column("int_id", ForeignKey("inventario_taller.int_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    usuario_id: Mapped[int | None] = mapped_column("usu_id", ForeignKey("usuarios.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=True)
    fecha: Mapped[datetime] = mapped_column("smt_fec", DateTime(timezone=True), server_default=func.now(), nullable=False)
    cantidad: Mapped[float] = mapped_column("smt_can", Numeric(12, 2), nullable=False)
    unidad_medida: Mapped[UnidadMedidaEnum] = mapped_column("smt_uni_med", unidad_medida_enum, nullable=False)
    destino: Mapped[str] = mapped_column("smt_destino", String(50), nullable=False)
    observaciones_1: Mapped[str | None] = mapped_column("smt_obs1", Text)
    observaciones_2: Mapped[str | None] = mapped_column("smt_obs2", Text)
    estado: Mapped[bool] = mapped_column("smt_estado", Boolean, default=True, nullable=False)

    item = relationship("InventarioTaller", back_populates="salidas")
    usuario = relationship("Usuario")

    @validates("destino", "observaciones_1", "observaciones_2")
    def normalize_uppercase(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()
