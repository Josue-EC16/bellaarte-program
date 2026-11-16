from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

from app.models.boutique_enums import PrioridadNotificacionEnum
from app.schemas.common import ORMBaseModel


class NotificationResolveRequest(BaseModel):
    motivo: str = Field(min_length=5, max_length=500)

    @field_validator("motivo", mode="before")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) < 5:
            raise ValueError("El motivo debe contener al menos 5 caracteres.")
        return normalized


class NotificationReadRequest(BaseModel):
    revision: int = Field(ge=1)


class NotificationPreferencesRequest(BaseModel):
    desktop_enabled: bool


class NotificationEmailRetryRequest(BaseModel):
    confirm_uncertain: bool = False


class NotificationPreferencesResponse(BaseModel):
    desktop_enabled: bool
    desktop_enabled_since: datetime | None


class NotificationRecipientSummary(ORMBaseModel):
    user_id: int
    full_name: str
    role_code: str | None
    role_name: str | None
    username: str | None


class NotificationListItem(ORMBaseModel):
    id: int
    tipo: str
    prioridad: PrioridadNotificacionEnum
    titulo: str
    mensaje: str
    modulo: str | None
    leida: bool
    resuelta: bool
    fecha: datetime
    fecha_leida: datetime | None
    fecha_resuelta: datetime | None
    tabla_referencia: str | None
    id_referencia: int | None
    recipient: NotificationRecipientSummary
    revision: int
    revision_fecha: datetime
    can_resolve: bool
    motivo_cierre: str | None = None
    duplicada_de_id: int | None = None


class NotificationDetailResponse(NotificationListItem):
    action_path: str | None


class NotificationPageResponse(BaseModel):
    items: list[NotificationListItem]
    total: int
    page: int
    page_size: int


class NotificationDesktopClaimResponse(BaseModel):
    items: list[NotificationDetailResponse]


class NotificationSummaryResponse(BaseModel):
    unread_count: int
    unresolved_count: int
    urgent_count: int
    priority_counts: dict[str, int]
    latest: list[NotificationListItem]


class NotificationReportBucket(BaseModel):
    label: str
    count: int


class NotificationReportSummary(BaseModel):
    total: int
    unread: int
    unresolved: int
    urgent_unresolved: int
    by_module: list[NotificationReportBucket]
    by_priority: list[NotificationReportBucket]
    by_role: list[NotificationReportBucket]
    by_type: list[NotificationReportBucket]


class NotificationQueryFilters(BaseModel):
    user_id: int | None = Field(default=None, gt=0)
    role_code: str | None = None
    module: str | None = None
    type: str | None = None
    priority: PrioridadNotificacionEnum | None = None
    is_read: bool | None = None
    is_resolved: bool | None = None
    date_from: date | None = None
    date_to: date | None = None
    table_ref: str | None = None
    record_id_ref: int | None = Field(default=None, gt=0)

    @field_validator("role_code", "module", "type", "table_ref", mode="before")
    @classmethod
    def normalize_catalog_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        return normalized or None
