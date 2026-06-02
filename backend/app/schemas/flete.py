from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.models.boutique_enums import (
    EstadoFleteDevolucionEnum,
    EstadoFleteEntregaEnum,
    EstadoFleteEnum,
    EstadoSalidaFleteEnum,
    MetodoPagoEnum,
    MotivoDescFleteEnum,
)
from app.schemas.common import ORMBaseModel
from app.schemas.receipt import ReceiptCustomerSnapshotPayload


ReviewResolution = Literal["disponible", "agotado"]


class FleteCreateRequest(BaseModel):
    item_id: int = Field(gt=0)
    precio_flete_ref: float = Field(gt=0)
    max_salidas: int = Field(default=3, ge=1, le=4)
    observaciones: str | None = Field(default=None, max_length=150)


class FleteUpdateRequest(BaseModel):
    precio_flete_ref: float = Field(gt=0)
    max_salidas: int = Field(ge=1, le=4)
    observaciones: str | None = Field(default=None, max_length=150)


class FleteDisableRequest(BaseModel):
    motivo: str = Field(min_length=5, max_length=200)


class FleteResolveReviewRequest(BaseModel):
    resolution: ReviewResolution
    motivo: str = Field(min_length=5, max_length=200)


class FletePassToSaleRequest(BaseModel):
    new_sale_price: float = Field(gt=0)
    observaciones: str | None = Field(default=None, max_length=200)


class FleteRetireRequest(BaseModel):
    motivo: str = Field(min_length=5, max_length=200)


class FleteEligibleItemSummary(ORMBaseModel):
    id: int
    code: str
    name: str
    color_primary: str
    sale_price: float
    stock: int
    detail_kind: str


class FleteItemSummary(ORMBaseModel):
    id: int
    code: str
    name: str
    color_primary: str
    color_secondary: str | None
    material: str
    sale_price: float
    stock: int


class FleteUserSummary(ORMBaseModel):
    id: int
    full_name: str
    username: str


class FleteListItem(ORMBaseModel):
    id: int
    item: FleteItemSummary
    precio_flete_ref: float
    max_salidas: int
    salidas_actuales: int
    estado: EstadoFleteEnum
    habilitado: bool
    fecha_habilitacion: datetime
    tiene_salida_activa: bool


class FleteSalidaHistoryItem(ORMBaseModel):
    id: int
    numero_salida: int
    fecha_salida: date
    fecha_devolucion_prevista: date
    client_name: str
    estado_salida: EstadoSalidaFleteEnum
    total_flete: float


class FleteDetailResponse(ORMBaseModel):
    id: int
    item: FleteItemSummary
    registered_by: FleteUserSummary
    precio_flete_ref: float
    max_salidas: int
    salidas_actuales: int
    estado: EstadoFleteEnum
    fecha_habilitacion: datetime
    observaciones: str | None
    habilitado: bool
    tiene_salida_activa: bool
    active_output_id: int | None
    salidas: list[FleteSalidaHistoryItem]


class FletePassToSaleResponse(ORMBaseModel):
    flete: FleteDetailResponse
    new_item_id: int
    new_item_code: str


class SalidaFleteCreateRequest(BaseModel):
    flete_id: int = Field(gt=0)
    client_id: int = Field(gt=0)
    currency_id: int = Field(gt=0)
    fecha_salida: date
    fecha_devolucion_prevista: date
    precio: float = Field(gt=0)
    descuento: float | None = Field(default=None, ge=0)
    motivo_desc: MotivoDescFleteEnum | None = None
    metodo_pago: MetodoPagoEnum
    garantia: float = Field(default=0, ge=0)
    estado_entrega: EstadoFleteEntregaEnum
    observaciones_entrega: str | None = None
    receipt_customer_snapshot: ReceiptCustomerSnapshotPayload | None = None

    @model_validator(mode="after")
    def validate_discount(self) -> "SalidaFleteCreateRequest":
        if self.fecha_devolucion_prevista < self.fecha_salida:
            raise ValueError("La fecha prevista de devolución no puede ser anterior a la fecha de salida.")
        if self.descuento is None and self.motivo_desc is not None:
            raise ValueError("No debes enviar motivo de descuento si no existe descuento.")
        if self.descuento is not None and self.motivo_desc is None:
            raise ValueError("Debes especificar el motivo del descuento.")
        if self.descuento is not None and self.descuento > self.precio:
            raise ValueError("El descuento no puede ser mayor al precio del flete.")
        return self


class SalidaFleteDeliverRequest(BaseModel):
    observaciones_entrega: str | None = None


class SalidaFleteReturnRequest(BaseModel):
    estado_salida: Literal["devuelto", "devuelto_con_observacion", "devuelto_con_arreglo"]
    estado_devolucion: EstadoFleteDevolucionEnum
    fecha_devolucion_real: date
    requiere_arreglo: bool = False
    monto_arreglo: float = Field(default=0, ge=0)
    descripcion_arreglo: str | None = Field(default=None, max_length=150)
    garantia_devuelta: float = Field(default=0, ge=0)
    observaciones_devolucion: str | None = None

    @model_validator(mode="after")
    def validate_arreglo(self) -> "SalidaFleteReturnRequest":
        if self.estado_salida == "devuelto_con_arreglo" and not self.requiere_arreglo:
            raise ValueError("La devolución con arreglo debe marcar que requiere arreglo.")
        if self.requiere_arreglo and not self.descripcion_arreglo:
            raise ValueError("Debes describir el arreglo requerido.")
        if not self.requiere_arreglo and self.descripcion_arreglo is not None:
            raise ValueError("No debes enviar descripción de arreglo si no requiere arreglo.")
        if not self.requiere_arreglo and self.monto_arreglo != 0:
            raise ValueError("El monto de arreglo debe ser cero cuando no se requiere arreglo.")
        return self


class SalidaFleteAnnulRequest(BaseModel):
    motivo: str = Field(min_length=5, max_length=200)


class FleteClientSummary(ORMBaseModel):
    id: int
    codigo: str
    full_name: str


class FleteCurrencySummary(ORMBaseModel):
    id: int
    codigo: str
    nombre: str
    simbolo: str | None
    es_base: bool


class ComprobanteSummary(ORMBaseModel):
    id: int
    codigo: str
    total: float
    total_moneda_original: float
    garantia: float
    estado: str


class SalidaFleteListItem(ORMBaseModel):
    id: int
    flete_id: int
    item_code: str
    item_name: str
    client_id: int
    client_name: str
    currency_code: str
    numero_salida: int
    fecha_salida: date
    fecha_devolucion_prevista: date
    estado_salida: EstadoSalidaFleteEnum
    total_flete: float
    garantia: float
    registered_by: str


class SalidaFleteDetailResponse(ORMBaseModel):
    id: int
    flete_id: int
    item: FleteItemSummary
    client: FleteClientSummary
    currency: FleteCurrencySummary
    registered_by: FleteUserSummary
    numero_salida: int
    fecha_registro: datetime
    fecha_salida: date
    fecha_devolucion_prevista: date
    fecha_devolucion_real: date | None
    precio: float
    descuento: float | None
    motivo_desc: MotivoDescFleteEnum | None
    metodo_pago: MetodoPagoEnum
    tipo_cambio_usado: float
    total_flete: float
    total_flete_moneda_origen: float
    garantia: float
    garantia_devuelta: float
    estado_salida: EstadoSalidaFleteEnum
    estado_entrega: EstadoFleteEntregaEnum
    estado_devolucion: EstadoFleteDevolucionEnum | None
    requiere_arreglo: bool
    monto_arreglo: float
    descripcion_arreglo: str | None
    observaciones_entrega: str | None
    observaciones_devolucion: str | None
    habilitado: bool
    comprobante: ComprobanteSummary | None
