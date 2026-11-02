from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

from app.models.boutique_enums import EstadoBackupBdEnum, TipoBackupBdEnum
from app.schemas.common import ORMBaseModel


def _normalize_upper(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    return normalized or None


class BackupUserSummary(ORMBaseModel):
    id: int
    full_name: str
    username: str | None = None


class BackupListItem(ORMBaseModel):
    id: int
    tipo: TipoBackupBdEnum
    estado: EstadoBackupBdEnum
    origen: str
    nombre_archivo: str
    tamano_bytes: int | None
    hash_sha256: str | None
    fecha_inicio: datetime
    fecha_fin: datetime | None
    pg_dump_version: str | None
    db_nombre: str | None
    usuario: BackupUserSummary | None
    file_exists: bool


class BackupDetailResponse(BackupListItem):
    ruta_archivo: str
    observacion: str | None
    error: str | None


class BackupRunResponse(BackupDetailResponse):
    message: str


class BackupCheckFileResponse(BaseModel):
    id: int
    exists: bool
    nombre_archivo: str
    ruta_archivo: str
    tamano_registrado_bytes: int | None
    tamano_actual_bytes: int | None


class BackupActiveStatusResponse(BaseModel):
    active: bool
    message: str | None = None
    backup_id: int | None = None
    tipo: str | None = None
    origen: str | None = None
    created_at: str | None = None


class BackupQueryFilters(BaseModel):
    tipo: TipoBackupBdEnum | None = None
    estado: EstadoBackupBdEnum | None = None
    origen: str | None = Field(default=None, max_length=30)
    usuario_id: int | None = Field(default=None, gt=0)
    date_from: date | None = None
    date_to: date | None = None
    search: str | None = Field(default=None, max_length=255)

    @field_validator("origen", "search", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        return _normalize_upper(value)
