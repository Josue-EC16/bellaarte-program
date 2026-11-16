from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Identity, Index, Numeric, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.base import Base


class TipoCambioMoneda(Base):
    __tablename__ = "tipo_cambio_moneda"
    __table_args__ = (
        CheckConstraint("tcm_valor_bob > 0", name="ck_tcm_valor_bob"),
        CheckConstraint("tcm_valor_bob <> 'NaN'::numeric", name="ck_tcm_valor_finito"),
        CheckConstraint("tcm_origen IN ('MANUAL','AUTOMATICO')", name="ck_tcm_origen"),
        CheckConstraint("(tcm_origen='MANUAL' AND usu_id IS NOT NULL) OR (tcm_origen='AUTOMATICO' AND usu_id IS NULL)", name="ck_tcm_autoria"),
        CheckConstraint("tcm_origen<>'AUTOMATICO' OR (tcm_fuente IS NOT NULL AND length(btrim(tcm_fuente))>0)", name="ck_tcm_fuente_automatica"),
        UniqueConstraint("mon_id", "tcm_id", name="uq_tcm_moneda_id"),
        Index("ix_tcm_historial_moneda", "mon_id", text("tcm_fec_reg DESC")),
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
    usuario_id: Mapped[int | None] = mapped_column(
        "usu_id",
        ForeignKey("usuarios.id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=True,
    )
    valor_bob: Mapped[Decimal] = mapped_column("tcm_valor_bob", Numeric(12, 4), nullable=False)
    origen: Mapped[str] = mapped_column("tcm_origen", String(12), default="MANUAL", server_default="MANUAL", nullable=False)
    fuente: Mapped[str | None] = mapped_column("tcm_fuente", String(64))
    fecha_consulta: Mapped[datetime | None] = mapped_column("tcm_fec_consulta", DateTime(timezone=True))
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
