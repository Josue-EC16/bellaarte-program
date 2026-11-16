"""Exchange-rate-specific attempt history; deliberately outside general audit."""
from datetime import date, datetime

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, ForeignKey, ForeignKeyConstraint, Identity, Index, SmallInteger, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


STATES = ("INICIADO", "EXITOSO", "ERROR_CONEXION", "ERROR_API", "ERROR_DATOS", "ERROR_VIGENCIA", "ERROR_EJECUCION", "CARGA_HISTORICA")
STATE_SQL = "tcs_estado IN (" + ",".join("'" + value + "'" for value in STATES) + ")"


class TipoCambioRegistro(Base):
    __tablename__ = "tipo_cambio_registros"
    __table_args__ = (
        ForeignKeyConstraint(["mon_id", "tcm_id"], ["tipo_cambio_moneda.mon_id", "tipo_cambio_moneda.tcm_id"],
                             name="fk_tcs_cotizacion_moneda", ondelete="RESTRICT", onupdate="CASCADE"),
        CheckConstraint(STATE_SQL, name="ck_tcs_estado"),
        CheckConstraint("(tcs_estado='CARGA_HISTORICA' AND tcs_num_intento=0) OR (tcs_estado<>'CARGA_HISTORICA' AND tcs_num_intento BETWEEN 1 AND 10)", name="ck_tcs_intento"),
        CheckConstraint("(tcs_estado IN ('EXITOSO','CARGA_HISTORICA')) = (tcm_id IS NOT NULL)", name="ck_tcs_cotizacion_resultado"),
        CheckConstraint("tcs_codigo_http IS NULL OR tcs_codigo_http BETWEEN 100 AND 599", name="ck_tcs_http"),
        CheckConstraint("tcs_estado<>'EXITOSO' OR (tcs_codigo_http IS NOT NULL AND tcs_codigo_http BETWEEN 200 AND 299)", name="ck_tcs_http_exitoso"),
        CheckConstraint("tcs_estado NOT IN ('INICIADO','CARGA_HISTORICA','ERROR_CONEXION') OR tcs_codigo_http IS NULL", name="ck_tcs_http_estado"),
        CheckConstraint("tcs_proximo_intento IS NULL OR (tcs_estado LIKE 'ERROR_%' AND tcs_proximo_intento>tcs_fec_intento)", name="ck_tcs_proximo_intento"),
        CheckConstraint("length(btrim(tcs_proveedor))>0", name="ck_tcs_proveedor"),
        Index("ix_tcs_historial_moneda", "mon_id", text("tcs_fecha_objetivo DESC"), text("tcs_fec_intento DESC")),
        Index("ix_tcs_proximos", "tcs_proximo_intento", "mon_id", postgresql_where=text("tcs_proximo_intento IS NOT NULL")),
        Index("uq_tcs_ordinal_dia", "mon_id", "tcs_proveedor", text("((tcs_fec_intento AT TIME ZONE 'America/La_Paz')::date)"), "tcs_num_intento", unique=True, postgresql_where=text("tcs_num_intento>0")),
        Index("uq_tcs_exitoso_fecha", "mon_id", "tcs_proveedor", "tcs_fecha_objetivo", unique=True, postgresql_where=text("tcs_estado='EXITOSO'")),
        Index("uq_tcs_historico_fecha", "mon_id", "tcs_proveedor", "tcs_fecha_objetivo", unique=True, postgresql_where=text("tcs_estado='CARGA_HISTORICA'")),
    )

    id: Mapped[int] = mapped_column("tcs_id", BigInteger, Identity(always=True), primary_key=True)
    moneda_id: Mapped[int] = mapped_column("mon_id", BigInteger, ForeignKey("moneda.mon_id", name="fk_tcs_moneda", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False)
    tipo_cambio_id: Mapped[int | None] = mapped_column("tcm_id", BigInteger)
    fecha_objetivo: Mapped[date] = mapped_column("tcs_fecha_objetivo", Date, nullable=False)
    numero_intento: Mapped[int] = mapped_column("tcs_num_intento", SmallInteger, nullable=False)
    fecha_intento: Mapped[datetime] = mapped_column("tcs_fec_intento", DateTime(timezone=True), nullable=False)
    estado: Mapped[str] = mapped_column("tcs_estado", String(32), nullable=False)
    codigo_http: Mapped[int | None] = mapped_column("tcs_codigo_http", SmallInteger)
    proximo_intento: Mapped[datetime | None] = mapped_column("tcs_proximo_intento", DateTime(timezone=True))
    proveedor: Mapped[str] = mapped_column("tcs_proveedor", String(64), nullable=False)

    tipo_cambio = relationship("TipoCambioMoneda", foreign_keys=[moneda_id, tipo_cambio_id])
