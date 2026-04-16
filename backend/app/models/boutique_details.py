from sqlalchemy import BigInteger, Boolean, CheckConstraint, Enum as SqlEnum, ForeignKey, Identity, Numeric, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.base import Base
from app.models.boutique_enums import (
    CopaTallaVestidoBoutiqueEnum,
    TallaVestidoBoutiqueEnum,
    TamanoEnum,
    TipoVestidoEnum,
)


tamano_enum = SqlEnum(TamanoEnum, name="TAMANO", values_callable=lambda enum_cls: [item.value for item in enum_cls])
tipo_vestido_enum = SqlEnum(
    TipoVestidoEnum,
    name="TIPO_VESTIDO",
    values_callable=lambda enum_cls: [item.value for item in enum_cls],
)
copa_talla_enum = SqlEnum(
    CopaTallaVestidoBoutiqueEnum,
    name="COPA_TALLA_VESTIDO_BOUTIQUE",
    values_callable=lambda enum_cls: [item.value for item in enum_cls],
)
talla_vestido_enum = SqlEnum(
    TallaVestidoBoutiqueEnum,
    name="TALLA_VESTIDO_BOUTIQUE",
    values_callable=lambda enum_cls: [item.value for item in enum_cls],
)


class DetalleVestidoBoutique(Base):
    __tablename__ = "DETALLE_VESTIDO_BOUTIQUE"
    __table_args__ = (
        CheckConstraint('"DVB_LARGO_FALDA" IS NULL OR "DVB_LARGO_FALDA" >= 0', name="CK_DVB_LARGO_FALDA"),
    )

    id: Mapped[int] = mapped_column("DVB_ID", BigInteger, Identity(always=True), primary_key=True)
    item_id: Mapped[int] = mapped_column(
        "ITB_ID",
        ForeignKey("ITEM_BOUTIQUE.ITB_ID", onupdate="CASCADE", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    tipo_vestido: Mapped[TipoVestidoEnum] = mapped_column("DVB_TIPO_VESTIDO", tipo_vestido_enum, nullable=False)
    corte_falda: Mapped[str | None] = mapped_column("DVB_CORTE_FALDA", String(100))
    tipo_escote: Mapped[str | None] = mapped_column("DVB_TIPO_ESCOTE", String(100))
    tiene_cola: Mapped[bool] = mapped_column("DVB_TIENE_COLA", Boolean, default=False, nullable=False)
    tiene_manga: Mapped[bool] = mapped_column("DVB_TIENE_MANGA", Boolean, default=False, nullable=False)
    tiene_pedreria: Mapped[bool] = mapped_column("DVB_TIENE_PEDRERIA", Boolean, default=False, nullable=False)
    copa_talla: Mapped[CopaTallaVestidoBoutiqueEnum | None] = mapped_column("DVB_COPA_TALLA", copa_talla_enum)
    talla: Mapped[TallaVestidoBoutiqueEnum] = mapped_column("DVB_TALLA", talla_vestido_enum, nullable=False)
    largo_falda: Mapped[float | None] = mapped_column("DVB_LARGO_FALDA", Numeric(6, 2))
    observaciones: Mapped[str | None] = mapped_column("DVB_OBS", Text)

    item = relationship("ItemBoutique", back_populates="detalle_vestido")

    @validates("corte_falda", "tipo_escote", "observaciones")
    def normalize_uppercase(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()


class DetalleVeloBoutique(Base):
    __tablename__ = "DETALLE_VELO_BOUTIQUE"
    __table_args__ = (
        CheckConstraint('"DVE_LARGO" IS NULL OR "DVE_LARGO" >= 0', name="CK_DVE_LARGO"),
        CheckConstraint('"DVE_CAPAS" IS NULL OR "DVE_CAPAS" > 0', name="CK_DVE_CAPAS"),
    )

    id: Mapped[int] = mapped_column("DVE_ID", BigInteger, Identity(always=True), primary_key=True)
    item_id: Mapped[int] = mapped_column(
        "ITB_ID",
        ForeignKey("ITEM_BOUTIQUE.ITB_ID", onupdate="CASCADE", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    tipo_velo: Mapped[str] = mapped_column("DVE_TIPO_VELO", String(50), nullable=False)
    largo: Mapped[float | None] = mapped_column("DVE_LARGO", Numeric(6, 2))
    tamano: Mapped[TamanoEnum] = mapped_column("DVE_TAMANO", tamano_enum, nullable=False)
    capas: Mapped[int | None] = mapped_column("DVE_CAPAS", SmallInteger)
    borde: Mapped[str | None] = mapped_column("DVE_BORDE", String(100))
    decoracion: Mapped[str] = mapped_column("DVE_DECORACION", String(100), nullable=False)
    observaciones: Mapped[str | None] = mapped_column("DVE_OBS", Text)

    item = relationship("ItemBoutique", back_populates="detalle_velo")

    @validates("tipo_velo", "borde", "decoracion", "observaciones")
    def normalize_uppercase(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()


class DetalleBouquetBoutique(Base):
    __tablename__ = "DETALLE_BOUQUET_BOUTIQUE"

    id: Mapped[int] = mapped_column("DBO_ID", BigInteger, Identity(always=True), primary_key=True)
    item_id: Mapped[int] = mapped_column(
        "ITB_ID",
        ForeignKey("ITEM_BOUTIQUE.ITB_ID", onupdate="CASCADE", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    tipo_bouquet: Mapped[str | None] = mapped_column("DBO_TIPO_BOUQUET", String(100))
    tamano: Mapped[TamanoEnum] = mapped_column("DBO_TAMANO", tamano_enum, nullable=False)
    tipo_flor: Mapped[str | None] = mapped_column("DBO_TIPO_FLOR", String(100))
    decoracion: Mapped[str | None] = mapped_column("DBO_DECORACION", String(100))
    observaciones: Mapped[str | None] = mapped_column("DBO_OBS", Text)

    item = relationship("ItemBoutique", back_populates="detalle_bouquet")

    @validates("tipo_bouquet", "tipo_flor", "decoracion", "observaciones")
    def normalize_uppercase(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()
