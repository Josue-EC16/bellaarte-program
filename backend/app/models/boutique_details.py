from sqlalchemy import BigInteger, Boolean, CheckConstraint, Enum as SqlEnum, ForeignKey, Identity, Numeric, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.base import Base
from app.models.boutique_enums import CopaTallaVestidoBoutiqueEnum, TallaVestidoBoutiqueEnum, TipoVestidoEnum


tipo_vestido_enum = SqlEnum(
    TipoVestidoEnum,
    name="tipo_vestido",
    values_callable=lambda enum_cls: [item.value for item in enum_cls],
)
copa_talla_enum = SqlEnum(
    CopaTallaVestidoBoutiqueEnum,
    name="copa_talla_vestido_boutique",
    values_callable=lambda enum_cls: [item.value for item in enum_cls],
)
talla_vestido_enum = SqlEnum(
    TallaVestidoBoutiqueEnum,
    name="talla_vestido_boutique",
    values_callable=lambda enum_cls: [item.value for item in enum_cls],
)


class DetalleVestidoBoutique(Base):
    __tablename__ = "detalle_vestido_boutique"
    __table_args__ = (
        CheckConstraint("dvb_largo_falda IS NULL OR dvb_largo_falda >= 0", name="ck_dvb_largo_falda"),
    )

    id: Mapped[int] = mapped_column("dvb_id", BigInteger, Identity(always=True), primary_key=True)
    item_id: Mapped[int] = mapped_column(
        "itb_id",
        ForeignKey("item_boutique.itb_id", onupdate="CASCADE", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    tipo_vestido: Mapped[TipoVestidoEnum] = mapped_column("dvb_tipo_vestido", tipo_vestido_enum, nullable=False)
    corte_falda: Mapped[str | None] = mapped_column("dvb_corte_falda", String(100))
    tipo_escote: Mapped[str | None] = mapped_column("dvb_tipo_escote", String(100))
    tiene_cola: Mapped[bool] = mapped_column("dvb_tiene_cola", Boolean, default=False, nullable=False)
    tiene_manga: Mapped[bool] = mapped_column("dvb_tiene_manga", Boolean, default=False, nullable=False)
    tiene_pedreria: Mapped[bool] = mapped_column("dvb_tiene_pedreria", Boolean, default=False, nullable=False)
    copa_talla: Mapped[CopaTallaVestidoBoutiqueEnum | None] = mapped_column("dvb_copa_talla", copa_talla_enum)
    talla: Mapped[TallaVestidoBoutiqueEnum] = mapped_column("dvb_talla", talla_vestido_enum, nullable=False)
    largo_falda: Mapped[float | None] = mapped_column("dvb_largo_falda", Numeric(6, 2))
    observaciones: Mapped[str | None] = mapped_column("dvb_obs", Text)

    item = relationship("ItemBoutique", back_populates="detalle_vestido")

    @validates("corte_falda", "tipo_escote", "observaciones")
    def normalize_uppercase(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()


class DetalleVeloBoutique(Base):
    __tablename__ = "detalle_velo_boutique"
    __table_args__ = (
        CheckConstraint("dve_capas IS NULL OR dve_capas > 0", name="ck_dve_capas"),
    )

    id: Mapped[int] = mapped_column("dve_id", BigInteger, Identity(always=True), primary_key=True)
    item_id: Mapped[int] = mapped_column(
        "itb_id",
        ForeignKey("item_boutique.itb_id", onupdate="CASCADE", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    tipo_velo: Mapped[str] = mapped_column("dve_tipo_velo", String(50), nullable=False)
    capas: Mapped[int | None] = mapped_column("dve_capas", SmallInteger)
    borde: Mapped[str | None] = mapped_column("dve_borde", String(100))
    decoracion: Mapped[str | None] = mapped_column("dve_decoracion", Text)
    observaciones: Mapped[str | None] = mapped_column("dve_obs", Text)

    item = relationship("ItemBoutique", back_populates="detalle_velo")

    @validates("tipo_velo", "borde", "decoracion", "observaciones")
    def normalize_uppercase(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()


class DetalleBouquetBoutique(Base):
    __tablename__ = "detalle_bouquet_boutique"

    id: Mapped[int] = mapped_column("dbo_id", BigInteger, Identity(always=True), primary_key=True)
    item_id: Mapped[int] = mapped_column(
        "itb_id",
        ForeignKey("item_boutique.itb_id", onupdate="CASCADE", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    tipo_bouquet: Mapped[str | None] = mapped_column("dbo_tipo_bouquet", String(100))
    forma: Mapped[str | None] = mapped_column("dbo_forma", String(50))
    tipo_flor: Mapped[str | None] = mapped_column("dbo_tipo_flor", String(50))
    decoracion: Mapped[str | None] = mapped_column("dbo_decoracion", Text)
    observaciones: Mapped[str | None] = mapped_column("dbo_obs", Text)

    item = relationship("ItemBoutique", back_populates="detalle_bouquet")

    @validates("tipo_bouquet", "forma", "tipo_flor", "decoracion", "observaciones")
    def normalize_uppercase(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()


class DetalleBrassierBoutique(Base):
    __tablename__ = "detalle_brassier_boutique"

    id: Mapped[int] = mapped_column("dbb_id", BigInteger, Identity(always=True), primary_key=True)
    item_id: Mapped[int] = mapped_column(
        "itb_id",
        ForeignKey("item_boutique.itb_id", onupdate="CASCADE", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    copa_talla: Mapped[CopaTallaVestidoBoutiqueEnum] = mapped_column("dbb_copa_tall", copa_talla_enum, nullable=False)
    tiene_encaje: Mapped[bool] = mapped_column("dbb_tiene_encaje", Boolean, default=True, nullable=False)
    marca: Mapped[str | None] = mapped_column("dbb_marca", String(50))
    observaciones: Mapped[str | None] = mapped_column("dbb_obs", Text)

    item = relationship("ItemBoutique", back_populates="detalle_brassier")

    @validates("marca", "observaciones")
    def normalize_uppercase(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()
