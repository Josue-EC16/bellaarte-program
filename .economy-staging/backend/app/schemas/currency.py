from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMBaseModel


class MonedaCreateRequest(BaseModel):
    codigo: str = Field(min_length=2, max_length=10)
    nombre: str = Field(min_length=2, max_length=80)
    simbolo: str | None = Field(default=None, max_length=10)
    es_base: bool = False
    habilitado: bool = True


class MonedaUpdateRequest(MonedaCreateRequest):
    pass


class MonedaStatusUpdateRequest(BaseModel):
    habilitado: bool


class MonedaResponse(ORMBaseModel):
    id: int
    codigo: str
    nombre: str
    simbolo: str | None
    es_base: bool
    habilitado: bool
    fecha_registro: datetime


class TipoCambioCreateRequest(BaseModel):
    moneda_id: int = Field(gt=0)
    valor_bob: float = Field(gt=0)
    observaciones: str | None = None
    activo: bool = True


class TipoCambioUpdateRequest(BaseModel):
    valor_bob: float = Field(gt=0)
    observaciones: str | None = None
    activo: bool = True


class TipoCambioStatusUpdateRequest(BaseModel):
    activo: bool


class TipoCambioListItem(ORMBaseModel):
    id: int
    moneda_id: int
    moneda_codigo: str
    moneda_nombre: str
    valor_bob: float
    activo: bool
    registrado_por: str
    fecha_registro: datetime


class TipoCambioDetailResponse(ORMBaseModel):
    id: int
    moneda: MonedaResponse
    valor_bob: float
    observaciones: str | None
    activo: bool
    registrado_por: str
    fecha_registro: datetime
