from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


class OperationalRateResponse(BaseModel):
    id: int
    valor_bob: str
    origen: str
    fuente: str | None
    fecha_registro: datetime
    fecha_oficial: date | None


class ExchangeRateSyncStateResponse(BaseModel):
    enabled: bool
    start_date: date | None
    local_date: date
    status: Literal["DISABLED", "PAUSED", "NOT_STARTED", "NO_ACTIVE_RATE", "UPDATED", "MANUAL_AFTER_OFFICIAL", "MANUAL_FALLBACK", "CONNECTION_ERROR", "ERROR", "EXHAUSTED", "WAITING"]
    message: str
    operational_rate: OperationalRateResponse | None
    last_official_date: date | None
    official_today: bool
    attempts_used: int
    attempts_remaining: int
    next_attempt_at: datetime | None
    consecutive_missing_days: int
    backlog_count: int


class ExchangeRateSyncRecordResponse(BaseModel):
    id: int
    moneda_codigo: str
    fecha_objetivo: date
    numero_intento: int
    fecha_intento: datetime
    estado: str
    codigo_http: int | None
    proximo_intento: datetime | None
    proveedor: str
    tipo_cambio_id: int | None
    valor_bob: str | None
    message: str


class ExchangeRateSyncPageResponse(BaseModel):
    items: list[ExchangeRateSyncRecordResponse]
    total: int
    page: int
    page_size: int
