from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Identity, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.types import Enum as SqlEnum

from app.models.base import Base
from app.models.boutique_enums import EstadoBackupBdEnum, TipoBackupBdEnum


tipo_backup_bd_enum = SqlEnum(
    TipoBackupBdEnum,
    name="tipo_backup_bd",
    values_callable=lambda enum_cls: [item.value for item in enum_cls],
    create_type=False,
)
estado_backup_bd_enum = SqlEnum(
    EstadoBackupBdEnum,
    name="estado_backup_bd",
    values_callable=lambda enum_cls: [item.value for item in enum_cls],
    create_type=False,
)


class BackupBd(Base):
    __tablename__ = "backup_bd"
    __table_args__ = (
        CheckConstraint("bkp_origen in ('AUTOMATICO', 'MANUAL')", name="ck_backup_origen"),
        CheckConstraint("bkp_tamano_bytes is null or bkp_tamano_bytes >= 0", name="ck_backup_tamano"),
        CheckConstraint(
            "("
            "(bkp_estado = 'EN_PROCESO' and bkp_fec_fin is null)"
            " or "
            "(bkp_estado in ('EXITOSO', 'FALLIDO') and bkp_fec_fin is not null)"
            ")",
            name="ck_backup_estado_fechas",
        ),
        Index("ix_backup_bd_fec_inicio", "bkp_fec_inicio"),
        Index("ix_backup_bd_estado_fec_inicio", "bkp_estado", "bkp_fec_inicio"),
        Index("ix_backup_bd_tipo_fec_inicio", "bkp_tipo", "bkp_fec_inicio"),
        Index("ix_backup_bd_origen_fec_inicio", "bkp_origen", "bkp_fec_inicio"),
        Index("ix_backup_bd_usu_fec_inicio", "usu_id", "bkp_fec_inicio"),
        Index("ix_backup_bd_nombre_archivo", "bkp_nombre_archivo"),
    )

    id: Mapped[int] = mapped_column("bkp_id", BigInteger, Identity(always=True), primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(
        "usu_id",
        ForeignKey("usuarios.id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=True,
    )
    tipo: Mapped[TipoBackupBdEnum] = mapped_column("bkp_tipo", tipo_backup_bd_enum, nullable=False)
    estado: Mapped[EstadoBackupBdEnum] = mapped_column(
        "bkp_estado",
        estado_backup_bd_enum,
        nullable=False,
        default=EstadoBackupBdEnum.EN_PROCESO,
        server_default=EstadoBackupBdEnum.EN_PROCESO.value,
    )
    origen: Mapped[str] = mapped_column("bkp_origen", String(30), nullable=False)
    nombre_archivo: Mapped[str] = mapped_column("bkp_nombre_archivo", String(255), nullable=False)
    ruta_archivo: Mapped[str] = mapped_column("bkp_ruta_archivo", Text, nullable=False)
    tamano_bytes: Mapped[int | None] = mapped_column("bkp_tamano_bytes", BigInteger)
    hash_sha256: Mapped[str | None] = mapped_column("bkp_hash_sha256", String(128))
    fecha_inicio: Mapped[datetime] = mapped_column("bkp_fec_inicio", DateTime(timezone=True), nullable=False, server_default=func.now())
    fecha_fin: Mapped[datetime | None] = mapped_column("bkp_fec_fin", DateTime(timezone=True))
    pg_dump_version: Mapped[str | None] = mapped_column("bkp_pg_dump_version", String(100))
    db_nombre: Mapped[str | None] = mapped_column("bkp_db_nombre", String(150))
    observacion: Mapped[str | None] = mapped_column("bkp_observacion", Text)
    error: Mapped[str | None] = mapped_column("bkp_error", Text)

    usuario = relationship("Usuario")

    @validates("origen", "observacion", "error")
    def normalize_upper_text(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        return normalized or None
