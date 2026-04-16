from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.boutique_enums import (
    CopaTallaVestidoBoutiqueEnum,
    TallaVestidoBoutiqueEnum,
    TamanoEnum,
    TipoVestidoEnum,
)
from app.schemas.common import ORMBaseModel


DetailKind = Literal["VESTIDO", "VELO", "BOUQUET", "OTRO"]


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


class BoutiqueItemBasePayload(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=2, max_length=150)
    color: str = Field(min_length=2, max_length=60)
    shape: str | None = Field(default=None, max_length=60)
    material: str = Field(min_length=2, max_length=100)
    measurements: str | None = None
    supplier: str | None = Field(default=None, max_length=100)
    description: str | None = None
    purchase_price: float = Field(ge=0)
    sale_price: float = Field(ge=0)
    stock: float = Field(ge=0)
    stock_min: float = Field(ge=0)
    notes: str | None = None


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
    length: float | None = Field(default=None, ge=0)
    size: TamanoEnum
    layers: int | None = Field(default=None, gt=0)
    edge: str | None = Field(default=None, max_length=100)
    decoration: str = Field(min_length=2, max_length=100)
    notes: str | None = None


class DetalleBouquetBoutiquePayload(BaseModel):
    bouquet_type: str | None = Field(default=None, max_length=100)
    size: TamanoEnum
    flower_type: str | None = Field(default=None, max_length=100)
    decoration: str | None = Field(default=None, max_length=100)
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
        return self


class BoutiqueItemUpdateRequest(BaseModel):
    item: BoutiqueItemBasePayload
    detail: dict[str, Any] | None = None


class BoutiqueItemStatusUpdateRequest(BaseModel):
    is_active: bool


class TipoItemBoutiqueNested(ORMBaseModel):
    id: int
    nombre: str


class DetalleVestidoBoutiqueResponse(ORMBaseModel):
    dress_type: TipoVestidoEnum
    skirt_cut: str | None
    neckline_type: str | None
    has_train: bool
    has_sleeves: bool
    has_stoning: bool
    cup_size: CopaTallaVestidoBoutiqueEnum | None
    dress_size: TallaVestidoBoutiqueEnum
    skirt_length: float | None
    notes: str | None


class DetalleVeloBoutiqueResponse(ORMBaseModel):
    veil_type: str
    length: float | None
    size: TamanoEnum
    layers: int | None
    edge: str | None
    decoration: str
    notes: str | None


class DetalleBouquetBoutiqueResponse(ORMBaseModel):
    bouquet_type: str | None
    size: TamanoEnum
    flower_type: str | None
    decoration: str | None
    notes: str | None


class BoutiqueItemListItem(ORMBaseModel):
    id: int
    type_id: int
    type_name: str
    code: str
    name: str
    color: str
    material: str
    sale_price: float
    stock: float
    stock_min: float
    is_low_stock: bool
    is_active: bool
    detail_kind: DetailKind
    created_at: datetime


class BoutiqueItemDetailResponse(ORMBaseModel):
    id: int
    type: TipoItemBoutiqueNested
    code: str
    name: str
    color: str
    shape: str | None
    material: str
    measurements: str | None
    supplier: str | None
    description: str | None
    notes: str | None
    purchase_price: float
    sale_price: float
    stock: float
    stock_min: float
    is_low_stock: bool
    is_active: bool
    created_at: datetime
    detail_kind: DetailKind
    detail: dict[str, Any] | None
