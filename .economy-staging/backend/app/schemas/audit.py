from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.boutique_enums import TipoAccionAuditoriaEnum
from app.schemas.common import ORMBaseModel


class AuditUserSummary(ORMBaseModel):
    user_id: int
    full_name: str
    username: str | None
    email: str | None


class AuditListItem(ORMBaseModel):
    id: int
    fecha: datetime
    modulo: str
    submodulo: str | None
    tabla: str
    id_registro: str
    accion: TipoAccionAuditoriaEnum
    accion_funcional: str | None
    descripcion: str | None
    campo: str | None
    valor_anterior: str | None
    valor_nuevo: str | None
    metodo_http: str | None
    ip: str | None
    user_agent: str | None
    dispositivo: str | None
    navegador: str | None
    sistema_operativo: str | None
    id_evento: UUID | None
    usuario: AuditUserSummary | None


class AuditDetailResponse(AuditListItem):
    event_records_count: int


class AuditEventResponse(BaseModel):
    event_id: UUID
    total_records: int
    records: list[AuditListItem]


class AuditQueryFilters(BaseModel):
    user_id: int | None = None
    module: str | None = None
    submodule: str | None = None
    table: str | None = None
    record_id: str | None = None
    action: TipoAccionAuditoriaEnum | None = None
    functional_action: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    ip: str | None = None
    device: str | None = None
    browser: str | None = None
    operating_system: str | None = None
    http_method: str | None = None
    event_id: UUID | None = None
    search_description: str | None = Field(default=None, min_length=1)
    search_old_value: str | None = Field(default=None, min_length=1)
    search_new_value: str | None = Field(default=None, min_length=1)
    search_field: str | None = Field(default=None, min_length=1)

    @field_validator(
        "module",
        "submodule",
        "table",
        "functional_action",
        "device",
        "browser",
        "operating_system",
        "http_method",
        "search_description",
        "search_old_value",
        "search_new_value",
        "search_field",
        mode="before",
    )
    @classmethod
    def normalize_upper_catalogs(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        return normalized or None

    @field_validator("record_id", "ip", mode="before")
    @classmethod
    def normalize_free_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None
