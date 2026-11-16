from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, Enum as SqlEnum, ForeignKey, Identity, Index, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.base import Base
from app.models.boutique_enums import TipoAccionAuditoriaEnum


tipo_accion_auditoria_enum = SqlEnum(
    TipoAccionAuditoriaEnum,
    name="tipo_accion_auditoria",
    values_callable=lambda enum_cls: [item.value for item in enum_cls],
    create_type=False,
)


class AuditoriaSistema(Base):
    __tablename__ = "auditoria_sistema"
    __table_args__ = (
        Index("ix_auditoria_sistema_fec", "aud_fec"),
        Index("ix_auditoria_sistema_usu_fec", "usu_id", "aud_fec"),
        Index("ix_auditoria_sistema_modulo_fec", "aud_modulo", "aud_fec"),
        Index("ix_auditoria_sistema_tabla_fec", "aud_tabla", "aud_fec"),
        Index("ix_auditoria_sistema_accion_fec", "aud_accion", "aud_fec"),
        Index("ix_auditoria_sistema_evento", "aud_id_evento"),
        Index("ix_auditoria_sistema_ip", "aud_ip"),
        Index("ix_auditoria_sistema_registro", "aud_id_registro"),
    )

    id: Mapped[int] = mapped_column("aud_id", BigInteger, Identity(always=True), primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(
        "usu_id",
        ForeignKey("usuarios.id", onupdate="CASCADE", ondelete="RESTRICT"),
    )
    fecha: Mapped[datetime] = mapped_column(
        "aud_fec",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    modulo: Mapped[str] = mapped_column("aud_modulo", String(100), nullable=False)
    submodulo: Mapped[str | None] = mapped_column("aud_submodulo", String(100))
    tabla: Mapped[str] = mapped_column("aud_tabla", String(200), nullable=False)
    id_registro: Mapped[str] = mapped_column("aud_id_registro", String(200), nullable=False)
    accion: Mapped[TipoAccionAuditoriaEnum] = mapped_column("aud_accion", tipo_accion_auditoria_enum, nullable=False)
    accion_funcional: Mapped[str | None] = mapped_column("aud_accion_funcional", String(150))
    descripcion: Mapped[str | None] = mapped_column("aud_descripcion", Text)
    campo: Mapped[str | None] = mapped_column("aud_campo", String(200))
    valor_anterior: Mapped[str | None] = mapped_column("aud_valor_anterior", Text)
    valor_nuevo: Mapped[str | None] = mapped_column("aud_valor_nuevo", Text)
    metodo_http: Mapped[str | None] = mapped_column("aud_metodo_http", String(10))
    ip: Mapped[str | None] = mapped_column("aud_ip", String(100))
    user_agent: Mapped[str | None] = mapped_column("aud_user_agent", Text)
    dispositivo: Mapped[str | None] = mapped_column("aud_dispositivo", String(200))
    navegador: Mapped[str | None] = mapped_column("aud_navegador", String(100))
    sistema_operativo: Mapped[str | None] = mapped_column("aud_sistema_operativo", String(100))
    id_evento: Mapped[UUID | None] = mapped_column("aud_id_evento", Uuid)

    usuario = relationship("Usuario")

    @validates("modulo", "submodulo", "accion_funcional", "descripcion", "metodo_http", "dispositivo", "navegador", "sistema_operativo")
    def normalize_upper_text(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        return normalized or None

    @validates("tabla", "campo", "id_registro")
    def normalize_identifier_text(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None
