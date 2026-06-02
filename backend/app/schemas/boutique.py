from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.boutique_enums import (
    EstadoVentaBoutiqueEnum,
    CopaTallaVestidoBoutiqueEnum,
    MetodoPagoEnum,
    MotivoEntradaItemEnum,
    MotivoDescVentaBoutiqueEnum,
    TallaVestidoBoutiqueEnum,
    TipoVestidoEnum,
)
from app.schemas.common import ORMBaseModel
from app.schemas.receipt import ReceiptCustomerSnapshotPayload, ReceiptSummary


DetailKind = Literal["VESTIDO", "VELO", "BOUQUET", "BRASIER", "OTRO"]


class TipoItemBoutiqueCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    descripcion: str | None = Field(default=None, max_length=200)


class TipoItemBoutiqueUpdate(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    descripcion: str | None = Field(default=None, max_length=200)


class TipoItemBoutiqueStatusUpdate(BaseModel):
    habilitado: bool


class TipoItemBoutiqueResponse(ORMBaseModel):
    id: int
    nombre: str
    descripcion: str | None
    habilitado: bool
    fecha_registro: datetime


class ProveedorCreateRequest(BaseModel):
    nombres: str = Field(min_length=2, max_length=100)
    apellido_paterno: str | None = Field(default=None, max_length=50)
    apellido_materno: str | None = Field(default=None, max_length=50)
    nombre_comercial: str | None = Field(default=None, max_length=120)
    celular: str | None = Field(default=None, max_length=30)
    celular_secundario: str | None = Field(default=None, max_length=30)
    correo: str | None = Field(default=None, max_length=120)
    pais: str | None = Field(default=None, max_length=50)
    ciudad: str | None = Field(default=None, max_length=70)
    direccion: str | None = Field(default=None, max_length=150)
    observaciones: str | None = None


class ProveedorUpdateRequest(ProveedorCreateRequest):
    pass


class ProveedorStatusUpdateRequest(BaseModel):
    habilitado: bool


class ProveedorListItem(ORMBaseModel):
    id: int
    full_name: str
    nombre_comercial: str | None
    celular: str | None
    correo: str | None
    ciudad: str | None
    is_active: bool
    created_at: datetime


class ProveedorDetailResponse(ORMBaseModel):
    id: int
    nombres: str
    apellido_paterno: str | None
    apellido_materno: str | None
    full_name: str
    nombre_comercial: str | None
    celular: str | None
    celular_secundario: str | None
    correo: str | None
    pais: str | None
    ciudad: str | None
    direccion: str | None
    observaciones: str | None
    is_active: bool
    created_at: datetime


class BoutiqueItemBasePayload(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=2, max_length=150)
    color_primary: str = Field(min_length=2, max_length=60)
    color_secondary: str | None = Field(default=None, max_length=60)
    material: str = Field(min_length=2, max_length=100)
    length: float | None = Field(default=None, ge=0)
    width: float | None = Field(default=None, ge=0)
    provider_id: int | None = Field(default=None, gt=0)
    purchase_price: float = Field(ge=0)
    sale_price: float = Field(ge=0)
    stock: int = Field(ge=0)
    stock_min: int = Field(ge=0)
    detail: str | None = None

    @model_validator(mode="after")
    def validate_prices(self) -> "BoutiqueItemBasePayload":
        if self.sale_price < self.purchase_price:
            raise ValueError("El precio de venta no puede ser menor al precio de compra.")
        return self


class DetalleVestidoBoutiquePayload(BaseModel):
    dress_type: TipoVestidoEnum
    skirt_cut: str | None = Field(default=None, max_length=100)
    neckline_type: str | None = Field(default=None, max_length=100)
    has_train: bool = False
    has_sleeves: bool = False
    has_stoning: bool = False
    cup_size: CopaTallaVestidoBoutiqueEnum | None = None
    dress_size: TallaVestidoBoutiqueEnum
    skirt_length: float | None = Field(default=None, ge=0)
    notes: str | None = None


class DetalleVeloBoutiquePayload(BaseModel):
    veil_type: str = Field(min_length=2, max_length=50)
    layers: int | None = Field(default=None, gt=0)
    edge: str | None = Field(default=None, max_length=100)
    decoration: str | None = None
    notes: str | None = None


class DetalleBouquetBoutiquePayload(BaseModel):
    bouquet_type: str | None = Field(default=None, max_length=100)
    shape: str | None = Field(default=None, max_length=50)
    flower_type: str | None = Field(default=None, max_length=50)
    decoration: str | None = None
    notes: str | None = None


class DetalleBrassierBoutiquePayload(BaseModel):
    cup_size: CopaTallaVestidoBoutiqueEnum
    has_lace: bool = True
    brand: str | None = Field(default=None, max_length=50)
    notes: str | None = None


class BoutiqueItemCreateRequest(BaseModel):
    type_id: int = Field(gt=0)
    item: BoutiqueItemBasePayload
    detail_kind: DetailKind = "OTRO"
    detail: dict[str, Any] | None = None

    @field_validator("detail_kind")
    @classmethod
    def normalize_detail_kind(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def validate_detail_payload(self) -> "BoutiqueItemCreateRequest":
        if self.detail_kind == "OTRO" and self.detail is not None:
            raise ValueError("No debes enviar detalle especializado para items tipo OTRO.")
        if self.detail_kind != "OTRO" and self.detail is None:
            raise ValueError("Debes enviar el detalle especializado para el tipo seleccionado.")
        if self.detail_kind == "BRASIER" and self.detail is not None and not self.detail.get("cup_size"):
            raise ValueError("El detalle del brassier requiere la copa/talla.")
        return self


class BoutiqueItemUpdateRequest(BaseModel):
    item: BoutiqueItemBasePayload
    detail: dict[str, Any] | None = None


class BoutiqueItemStatusUpdateRequest(BaseModel):
    is_active: bool


class ProveedorNested(ORMBaseModel):
    id: int
    full_name: str
    nombre_comercial: str | None


class TipoItemBoutiqueNested(ORMBaseModel):
    id: int
    nombre: str


class BoutiqueItemListItem(ORMBaseModel):
    id: int
    type_id: int
    type_name: str
    code: str
    name: str
    color_primary: str
    color_secondary: str | None
    material: str
    provider_name: str | None
    sale_price: float
    stock: int
    stock_min: int
    is_low_stock: bool
    is_active: bool
    detail_kind: DetailKind
    created_at: datetime


class BoutiqueItemDetailResponse(ORMBaseModel):
    id: int
    type: TipoItemBoutiqueNested
    provider: ProveedorNested | None
    code: str
    name: str
    color_primary: str
    color_secondary: str | None
    material: str
    length: float | None
    width: float | None
    detail_text: str | None
    purchase_price: float
    sale_price: float
    stock: int
    stock_min: int
    is_low_stock: bool
    is_active: bool
    created_at: datetime
    detail_kind: DetailKind
    detail: dict[str, Any] | None


class BoutiqueSaleCreateRequest(BaseModel):
    item_id: int = Field(gt=0)
    client_id: int | None = Field(default=None, gt=0)
    currency_id: int = Field(gt=0)
    quantity: int = Field(gt=0)
    discount: float | None = Field(default=None, ge=0)
    discount_reason: MotivoDescVentaBoutiqueEnum | None = None
    payment_method: MetodoPagoEnum
    observations: str | None = None
    receipt_customer_snapshot: ReceiptCustomerSnapshotPayload | None = None

    @model_validator(mode="after")
    def validate_discount(self) -> "BoutiqueSaleCreateRequest":
        if self.discount is None and self.discount_reason is not None:
            raise ValueError("No debes enviar motivo de descuento si no existe descuento.")
        if self.discount is not None and self.discount_reason is None:
            raise ValueError("Debes especificar el motivo del descuento.")
        return self


class BoutiqueSaleStateChangeRequest(BaseModel):
    reason: str = Field(min_length=5, max_length=200)


class BoutiqueEntryCreateRequest(BaseModel):
    item_id: int = Field(gt=0)
    provider_id: int | None = Field(default=None, gt=0)
    quantity: int = Field(gt=0)
    unit_cost: float = Field(ge=0)
    reason: MotivoEntradaItemEnum = MotivoEntradaItemEnum.ENTRADA_STOCK
    document_reference: str | None = Field(default=None, max_length=80)
    observations: str | None = None


class BoutiqueEntryStatusUpdateRequest(BaseModel):
    is_active: bool


class BoutiqueEntryItemSummary(ORMBaseModel):
    id: int
    code: str
    name: str
    type_name: str


class BoutiqueEntryUserSummary(ORMBaseModel):
    id: int
    full_name: str
    username: str


class BoutiqueEntryListItem(ORMBaseModel):
    id: int
    fecha: datetime
    item: BoutiqueEntryItemSummary
    provider_name: str | None
    quantity: int
    unit_cost: float
    reason: MotivoEntradaItemEnum
    document_reference: str | None
    is_active: bool
    registered_by: str


class BoutiqueEntryDetailResponse(ORMBaseModel):
    id: int
    fecha: datetime
    item: BoutiqueEntryItemSummary
    provider: ProveedorNested | None
    quantity: int
    unit_cost: float
    reason: MotivoEntradaItemEnum
    document_reference: str | None
    observations: str | None
    is_active: bool
    registered_by: BoutiqueEntryUserSummary


class BoutiqueSaleItemSummary(ORMBaseModel):
    id: int
    code: str
    name: str
    type_name: str


class BoutiqueSaleClientSummary(ORMBaseModel):
    id: int
    codigo: str
    full_name: str


class BoutiqueSaleUserSummary(ORMBaseModel):
    id: int
    full_name: str
    username: str


class BoutiqueSaleCurrencySummary(ORMBaseModel):
    id: int
    codigo: str
    nombre: str
    simbolo: str | None
    es_base: bool


class BoutiqueSaleListItem(ORMBaseModel):
    id: int
    fecha: datetime
    estado: EstadoVentaBoutiqueEnum
    payment_method: MetodoPagoEnum
    item_id: int
    item_code: str
    item_name: str
    client_id: int | None
    client_code: str | None
    client_name: str | None
    currency_code: str
    registered_by: str
    quantity: int
    unit_price: float
    discount: float | None
    total: float
    total_currency_origin: float


class BoutiqueSaleDetailResponse(ORMBaseModel):
    id: int
    fecha: datetime
    estado: EstadoVentaBoutiqueEnum
    payment_method: MetodoPagoEnum
    item: BoutiqueSaleItemSummary
    client: BoutiqueSaleClientSummary | None
    currency: BoutiqueSaleCurrencySummary
    registered_by: BoutiqueSaleUserSummary
    quantity: int
    unit_price: float
    discount: float | None
    discount_reason: MotivoDescVentaBoutiqueEnum | None
    total: float
    exchange_rate_used: float
    total_currency_origin: float
    observations: str | None
    changed_at: datetime | None
    state_change_reason: str | None
    receipt: ReceiptSummary | None = None
