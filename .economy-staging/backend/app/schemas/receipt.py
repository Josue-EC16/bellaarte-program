from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.boutique_enums import EstadoComprobanteEnum, MetodoPagoEnum
from app.schemas.common import ORMBaseModel


class ReceiptCustomerSnapshotPayload(BaseModel):
    full_name: str | None = Field(default=None, max_length=150)
    ci_nit: str | None = Field(default=None, max_length=30)
    cellphone: str | None = Field(default=None, max_length=30)

    @field_validator("full_name", "ci_nit", "cellphone", mode="before")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        return normalized or None


class ReceiptTypeCreateRequest(BaseModel):
    nombre: str = Field(min_length=3, max_length=50)
    descripcion: str | None = Field(default=None, max_length=100)
    es_fiscal: bool = False

    @field_validator("nombre", "descripcion", mode="before")
    @classmethod
    def normalize_catalog_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        return normalized or None


class ReceiptTypeUpdateRequest(BaseModel):
    descripcion: str | None = Field(default=None, max_length=100)
    es_fiscal: bool

    @field_validator("descripcion", mode="before")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        return normalized or None


class ReceiptTypeStatusUpdateRequest(BaseModel):
    habilitado: bool


class ReceiptTypeResponse(ORMBaseModel):
    id: int
    nombre: str
    descripcion: str | None
    es_fiscal: bool
    habilitado: bool
    fecha_registro: datetime


class ReceiptSummary(ORMBaseModel):
    id: int
    codigo: str
    estado: EstadoComprobanteEnum
    total: float
    total_moneda_original: float


class ReceiptClientSnapshot(ORMBaseModel):
    id: int | None
    full_name: str
    ci_nit: str
    cellphone: str


class ReceiptUserSummary(ORMBaseModel):
    id: int
    full_name: str
    username: str | None


class ReceiptCurrencySummary(ORMBaseModel):
    id: int | None
    codigo: str | None
    nombre: str | None
    simbolo: str | None
    es_base: bool | None


class ReceiptDetailLine(ORMBaseModel):
    id: int
    concepto: str
    cantidad: float
    precio_unidad: float
    descuento: float
    subtotal: float
    observaciones: str | None


class ReceiptListItem(ORMBaseModel):
    id: int
    codigo: str
    fecha: datetime
    estado: EstadoComprobanteEnum
    origin_type: str
    origin_id: int
    tipo_comprobante: str
    client_name: str
    client_ci_nit: str
    client_cellphone: str
    currency_code: str | None
    payment_method: MetodoPagoEnum | None
    subtotal: float
    descuento: float
    total: float
    total_moneda_original: float
    saldo_posterior: float
    garantia: float
    registered_by: str


class ReceiptDetailResponse(ORMBaseModel):
    id: int
    codigo: str
    fecha: datetime
    estado: EstadoComprobanteEnum
    origin_type: str
    origin_id: int
    tipo_comprobante: str
    client: ReceiptClientSnapshot
    registered_by: ReceiptUserSummary
    currency: ReceiptCurrencySummary | None
    subtotal: float
    descuento: float
    total: float
    total_moneda_original: float
    saldo_posterior: float
    garantia: float
    tipo_cambio_usado: float
    payment_method: MetodoPagoEnum | None
    changed_at: datetime | None
    state_change_reason: str | None
    details: list[ReceiptDetailLine]
