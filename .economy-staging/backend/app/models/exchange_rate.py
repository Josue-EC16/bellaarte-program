from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Identity, Index, Numeric, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.base import Base


class TipoCambioMoneda(Base):
    __tablename__ = "tipo_cambio_moneda"
    __table_args__ = (
        CheckConstraint("tcm_valor_bob > 0", name="ck_tcm_valor_bob"),
        Index(
            "uq_tipo_cambio_activo_moneda",
            "mon_id",
            unique=True,
            postgresql_where=text("tcm_activo = true"),
        ),
    )

    id: Mapped[int] = mapped_column("tcm_id", BigInteger, Identity(always=True), primary_key=True)
    moneda_id: Mapped[int] = mapped_column(
        "mon_id",
        ForeignKey("moneda.mon_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    usuario_id: Mapped[int] = mapped_column(
        "usu_id",
        ForeignKey("usuarios.id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    valor_bob: Mapped[float] = mapped_column("tcm_valor_bob", Numeric(12, 4), nullable=False)
    fecha_registro: Mapped[datetime] = mapped_column(
        "tcm_fec_reg",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    observaciones: Mapped[str | None] = mapped_column("tcm_obs", Text)
    activo: Mapped[bool] = mapped_column("tcm_activo", Boolean, default=True, nullable=False)

    moneda = relationship("Moneda", back_populates="tipos_cambio")
    usuario = relationship("Usuario")

    @validates("observaciones")
    def normalize_uppercase(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()
