from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Identity, Index, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.types import Enum as SqlEnum

from app.models.base import Base
from app.models.boutique_enums import PrioridadNotificacionEnum


prioridad_notificacion_enum = SqlEnum(
    PrioridadNotificacionEnum,
    name="prioridad_notificacion",
    values_callable=lambda enum: [member.value for member in enum],
)


class Notificacion(Base):
    __tablename__ = "notificacion"
    __table_args__ = (
        CheckConstraint(
            "((not_resuelta = false and not_fec_resuelta is null) or (not_resuelta = true and not_fec_resuelta is not null))",
            name="ck_not_resuelta_fecha",
        ),
        CheckConstraint("not_revision >= 1", name="ck_not_revision_positiva"),
        CheckConstraint(
            "not_escritorio_revision_reclamada >= 0 and not_escritorio_revision_reclamada <= not_revision",
            name="ck_not_escritorio_revision",
        ),
        CheckConstraint(
            "not_tipo = upper(btrim(not_tipo)) and length(not_tipo) > 0 and "
            "(not_tabla_ref is null or (not_tabla_ref = upper(btrim(not_tabla_ref)) and length(not_tabla_ref) > 0))",
            name="ck_not_clave_normalizada",
        ),
        CheckConstraint(
            "not_duplicada_de_id is null or (not_duplicada_de_id <> not_id and not_resuelta = true and not_motivo_cierre is not null and not_motivo_cierre = 'DUPLICADA')",
            name="ck_not_duplicada_cerrada",
        ),
        Index(
            "ux_notificacion_abierta", "usu_id", "not_tipo", "not_tabla_ref", "not_id_ref",
            unique=True, postgresql_where=text("not_resuelta = false"), postgresql_nulls_not_distinct=True,
        ),
        Index(
            "idx_notificacion_escritorio", "usu_id", "not_revision_fecha", "not_id",
            postgresql_where=text("not_resuelta = false and not_leida = false"),
        ),
    )

    id: Mapped[int] = mapped_column("not_id", BigInteger, Identity(always=True), primary_key=True)
    usuario_id: Mapped[int] = mapped_column("usu_id", ForeignKey("usuarios.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False)
    tipo: Mapped[str] = mapped_column("not_tipo", String(200), nullable=False)
    prioridad: Mapped[PrioridadNotificacionEnum] = mapped_column(
        "not_prioridad",
        prioridad_notificacion_enum,
        nullable=False,
        default=PrioridadNotificacionEnum.MEDIA,
        server_default=PrioridadNotificacionEnum.MEDIA.value,
    )
    titulo: Mapped[str] = mapped_column("not_titulo", String(120), nullable=False)
    mensaje: Mapped[str] = mapped_column("not_mensaje", Text, nullable=False)
    modulo: Mapped[str | None] = mapped_column("not_modulo", String(50))
    leida: Mapped[bool] = mapped_column("not_leida", Boolean, nullable=False, default=False, server_default="false")
    fecha: Mapped[datetime] = mapped_column("not_fec", DateTime(timezone=True), nullable=False)
    fecha_leida: Mapped[datetime | None] = mapped_column("not_fec_leida", DateTime(timezone=True))
    tabla_referencia: Mapped[str | None] = mapped_column("not_tabla_ref", String(100))
    id_referencia: Mapped[int | None] = mapped_column("not_id_ref", BigInteger)
    resuelta: Mapped[bool] = mapped_column("not_resuelta", Boolean, nullable=False, default=False, server_default="false")
    fecha_resuelta: Mapped[datetime | None] = mapped_column("not_fec_resuelta", DateTime(timezone=True))
    revision: Mapped[int] = mapped_column("not_revision", Integer, nullable=False, default=1, server_default="1")
    revision_fecha: Mapped[datetime] = mapped_column("not_revision_fecha", DateTime(timezone=True), nullable=False, server_default=func.now())
    stock_cero_detectado: Mapped[bool] = mapped_column("not_stock_cero_detectado", Boolean, nullable=False, default=False, server_default="false")
    escritorio_revision_reclamada: Mapped[int] = mapped_column("not_escritorio_revision_reclamada", Integer, nullable=False, default=0, server_default="0")
    motivo_cierre: Mapped[str | None] = mapped_column("not_motivo_cierre", String(50))
    duplicada_de_id: Mapped[int | None] = mapped_column("not_duplicada_de_id", BigInteger, ForeignKey("notificacion.not_id", ondelete="RESTRICT"))

    usuario = relationship("Usuario")

    @validates("tipo", "titulo", "mensaje", "modulo", "tabla_referencia")
    def normalize_upper_text(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        return normalized or None


class PreferenciaNotificacion(Base):
    __tablename__ = "preferencia_notificacion"

    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"), primary_key=True)
    escritorio_habilitado_desde: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EnvioNotificacionCorreo(Base):
    """Delivery coordination only: never stores a password or message body."""

    __tablename__ = "envio_notificacion_correo"
    __table_args__ = (
        UniqueConstraint("cuenta_id", "destino", name="uq_envio_notificacion_cuenta_destino"),
        CheckConstraint("intentos >= 0", name="ck_envio_notificacion_intentos"),
        CheckConstraint(
            "estado in ('EN_CURSO', 'ENVIADO', 'FALLIDO', 'INCIERTO', 'BLOQUEADO')",
            name="ck_envio_notificacion_estado",
        ),
        CheckConstraint("destino = lower(btrim(destino)) and length(destino) > 0", name="ck_envio_notificacion_destino"),
        Index("idx_envio_notificacion_reintento", "proximo_intento", postgresql_where=text("estado = 'FALLIDO'")),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuentas.id", ondelete="RESTRICT"), nullable=False)
    destino: Mapped[str] = mapped_column(String(320), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="BLOQUEADO", server_default="BLOQUEADO")
    intentos: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    intento_id: Mapped[str | None] = mapped_column(String(36))
    ultimo_intento: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    proximo_intento: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fecha_resultado: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    categoria_error: Mapped[str | None] = mapped_column(String(50))
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    @validates("destino")
    def normalize_destination(self, _key: str, value: str) -> str:
        return value.strip().lower()
