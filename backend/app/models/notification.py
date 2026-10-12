from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, String, Text
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
    )

    id: Mapped[int] = mapped_column("not_id", primary_key=True, index=True)
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

    usuario = relationship("Usuario")

    @validates("tipo", "titulo", "mensaje", "modulo", "tabla_referencia")
    def normalize_upper_text(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        return normalized or None
