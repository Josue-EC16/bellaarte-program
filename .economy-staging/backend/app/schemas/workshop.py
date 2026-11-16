from datetime import datetime

from pydantic import BaseModel, Field

from app.models.boutique_enums import MotivoEntradaTallerEnum, UnidadMedidaEnum
from app.schemas.boutique import ProveedorNested
from app.schemas.common import ORMBaseModel


class TallerTypeCreateRequest(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    descripcion: str | None = Field(default=None, max_length=200)


class TallerTypeUpdateRequest(TallerTypeCreateRequest):
    pass


class TallerTypeStatusUpdateRequest(BaseModel):
    habilitado: bool


class TallerTypeResponse(ORMBaseModel):
    id: int
    nombre: str
    descripcion: str | None
    habilitado: bool
    fecha_registro: datetime


class TallerInventoryCreateRequest(BaseModel):
    type_id: int = Field(gt=0)
    provider_id: int | None = Field(default=None, gt=0)
    code: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=2, max_length=100)
    color: str = Field(min_length=2, max_length=50)
    length: float | None = Field(default=None, ge=0)
    width: float | None = Field(default=None, ge=0)
    material: str | None = Field(default=None, max_length=80)
    description: str | None = None
    reference_cost: float = Field(ge=0)
    stock: float = Field(ge=0)
    unit_measure: UnidadMedidaEnum
    stock_min: float = Field(ge=0)
    observations: str | None = None


class TallerInventoryUpdateRequest(TallerInventoryCreateRequest):
    pass


class TallerInventoryStatusUpdateRequest(BaseModel):
    is_active: bool


class TallerTypeNested(ORMBaseModel):
    id: int
    nombre: str


class TallerInventoryListItem(ORMBaseModel):
    id: int
    type_id: int
    type_name: str
    code: str
    name: str
    color: str
    material: str | None
    provider_name: str | None
    stock: float
    unit_measure: UnidadMedidaEnum
    stock_min: float
    is_low_stock: bool
    is_active: bool
    created_at: datetime


class TallerInventoryDetailResponse(ORMBaseModel):
    id: int
    type: TallerTypeNested
    provider: ProveedorNested | None
    code: str
    name: str
    color: str
    length: float | None
    width: float | None
    material: str | None
    description: str | None
    reference_cost: float
    stock: float
    unit_measure: UnidadMedidaEnum
    stock_min: float
    is_low_stock: bool
    is_active: bool
    observations: str | None
    created_at: datetime


class TallerEntryCreateRequest(BaseModel):
    item_id: int = Field(gt=0)
    provider_id: int | None = Field(default=None, gt=0)
    quantity: float = Field(gt=0)
    unit_measure: UnidadMedidaEnum
    unit_cost: float = Field(ge=0)
    reason: MotivoEntradaTallerEnum = MotivoEntradaTallerEnum.ENTRADA_STOCK
    document_reference: str | None = Field(default=None, max_length=80)
    observations: str | None = None


class TallerEntryStatusUpdateRequest(BaseModel):
    is_active: bool


class TallerItemSummary(ORMBaseModel):
    id: int
    code: str
    name: str
    unit_measure: UnidadMedidaEnum
    type_name: str | None = None


class TallerUserSummary(ORMBaseModel):
    id: int
    full_name: str
    username: str


class TallerEntryListItem(ORMBaseModel):
    id: int
    fecha: datetime
    item: TallerItemSummary
    provider_name: str | None
    quantity: float
    unit_measure: UnidadMedidaEnum
    unit_cost: float
    reason: MotivoEntradaTallerEnum
    document_reference: str | None
    is_active: bool
    registered_by: str


class TallerEntryDetailResponse(ORMBaseModel):
    id: int
    fecha: datetime
    item: TallerItemSummary
    provider: ProveedorNested | None
    quantity: float
    unit_measure: UnidadMedidaEnum
    unit_cost: float
    reason: MotivoEntradaTallerEnum
    document_reference: str | None
    observations: str | None
    is_active: bool
    registered_by: TallerUserSummary


class TallerOutputCreateRequest(BaseModel):
    item_id: int = Field(gt=0)
    quantity: float = Field(gt=0)
    unit_measure: UnidadMedidaEnum
    destination: str = Field(min_length=2, max_length=50)
    observations_1: str | None = None
    observations_2: str | None = None


class TallerOutputStatusUpdateRequest(BaseModel):
    is_active: bool


class TallerOutputListItem(ORMBaseModel):
    id: int
    fecha: datetime
    item: TallerItemSummary
    quantity: float
    unit_measure: UnidadMedidaEnum
    destination: str
    is_active: bool
    registered_by: str | None


class TallerOutputDetailResponse(ORMBaseModel):
    id: int
    fecha: datetime
    item: TallerItemSummary
    quantity: float
    unit_measure: UnidadMedidaEnum
    destination: str
    observations_1: str | None
    observations_2: str | None
    is_active: bool
    registered_by: TallerUserSummary | None
