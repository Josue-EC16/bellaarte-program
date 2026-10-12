from datetime import date, datetime, time
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.boutique_enums import (
    EstadoPagoPedidoEnum,
    EstadoPedidoGeneralEnum,
    MetodoPagoEnum,
    MotivoDescuentoPedidoEnum,
    PruebaEstadoPedidoEnum,
    TipoPedidoEnum,
    TipoVestidoEnum,
)
from app.schemas.common import ORMBaseModel
from app.schemas.receipt import ReceiptCustomerSnapshotPayload, ReceiptSummary


class OrderClientSummary(ORMBaseModel):
    id: int
    codigo: str
    full_name: str
    celular: str | None = None


class OrderUserSummary(ORMBaseModel):
    id: int
    full_name: str
    username: str | None = None


class OrderCurrencySummary(ORMBaseModel):
    id: int
    codigo: str
    nombre: str
    simbolo: str | None
    es_base: bool


class PedidoVestidoPayload(BaseModel):
    tipo_vestido: TipoVestidoEnum
    color_principal: str = Field(min_length=1, max_length=50)
    color_secundario: str | None = Field(default=None, max_length=50)
    descripcion_material: str = Field(min_length=1)
    descripcion_diseno: str = Field(min_length=1)
    descripcion_adicional: str | None = None
    ancho_espalda: float | None = Field(default=None, ge=0)
    talle_espalda: float | None = Field(default=None, ge=0)
    talle_delantero: float | None = Field(default=None, ge=0)
    contorno_cintura: float | None = Field(default=None, ge=0)
    contorno_cadera: float | None = Field(default=None, ge=0)
    largo_falda: float | None = Field(default=None, ge=0)
    sisa: float | None = Field(default=None, ge=0)
    ancho_busto: float | None = Field(default=None, ge=0)
    separacion_busto: float | None = Field(default=None, ge=0)
    talle_busto: float | None = Field(default=None, ge=0)
    talle_costado: float | None = Field(default=None, ge=0)
    observaciones: str | None = None

    @field_validator("color_principal", "color_secundario", "descripcion_material", "descripcion_diseno", "descripcion_adicional", "observaciones", mode="before")
    @classmethod
    def normalize_upper_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()


class PedidoVeloPayload(BaseModel):
    tipo: str | None = Field(default=None, max_length=100)
    color_principal: str = Field(min_length=1, max_length=50)
    color_secundario: str | None = Field(default=None, max_length=50)
    largo: float = Field(gt=0)
    ancho: float | None = Field(default=None, ge=0)
    capas: int | None = Field(default=None, gt=0)
    borde: str | None = Field(default=None, max_length=100)
    decoracion: str | None = None
    material: str | None = Field(default=None, max_length=100)
    observaciones: str | None = None

    @field_validator("tipo", "color_principal", "color_secundario", "borde", "decoracion", "material", "observaciones", mode="before")
    @classmethod
    def normalize_upper_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()


class PedidoColaPayload(BaseModel):
    tipo: str | None = Field(default=None, max_length=100)
    color_principal: str = Field(min_length=1, max_length=50)
    color_secundario: str | None = Field(default=None, max_length=50)
    largo: float = Field(gt=0)
    ancho: float | None = Field(default=None, ge=0)
    material: str | None = Field(default=None, max_length=100)
    decoracion: str | None = None
    observaciones: str | None = None

    @field_validator("tipo", "color_principal", "color_secundario", "material", "decoracion", "observaciones", mode="before")
    @classmethod
    def normalize_upper_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()


class PedidoMangaPayload(BaseModel):
    tipo: str | None = Field(default=None, max_length=100)
    color_principal: str = Field(min_length=1, max_length=50)
    color_secundario: str | None = Field(default=None, max_length=50)
    largo_manga: float = Field(gt=0)
    brazo: float = Field(ge=0)
    puno: float = Field(ge=0)
    material: str | None = Field(default=None, max_length=100)
    decoracion: str | None = None
    observaciones: str | None = None

    @field_validator("tipo", "color_principal", "color_secundario", "material", "decoracion", "observaciones", mode="before")
    @classmethod
    def normalize_upper_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()


class PedidoBouquetPayload(BaseModel):
    tipo: str = Field(min_length=1, max_length=100)
    color_principal: str = Field(min_length=1, max_length=50)
    color_secundario: str | None = Field(default=None, max_length=50)
    largo: float = Field(ge=0)
    ancho: float | None = Field(default=None, ge=0)
    tipo_flor: str | None = Field(default=None, max_length=100)
    decoracion: str | None = None
    observaciones: str | None = None

    @field_validator("tipo", "color_principal", "color_secundario", "tipo_flor", "decoracion", "observaciones", mode="before")
    @classmethod
    def normalize_upper_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()


class PedidoOtroPayload(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    color_principal: str = Field(min_length=1, max_length=50)
    color_secundario: str | None = Field(default=None, max_length=50)
    largo: float | None = Field(default=None, ge=0)
    ancho: float | None = Field(default=None, ge=0)
    descripcion: str | None = None
    observaciones: str | None = None

    @field_validator("nombre", "color_principal", "color_secundario", "descripcion", "observaciones", mode="before")
    @classmethod
    def normalize_upper_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()


class OrderBasePayload(BaseModel):
    codigo: str | None = Field(default=None, max_length=40)
    client_id: int = Field(gt=0)
    tipo: TipoPedidoEnum
    fecha_entrega: date
    viaje: bool = False
    pais_destino: str | None = Field(default=None, max_length=50)
    ciudad_destino: str | None = Field(default=None, max_length=50)
    precio: float = Field(default=0, ge=0)
    descuento: float | None = Field(default=None, ge=0)
    motivo_descuento: MotivoDescuentoPedidoEnum | None = None
    observaciones: str | None = None

    @field_validator("codigo", "pais_destino", "ciudad_destino", "observaciones", mode="before")
    @classmethod
    def normalize_upper_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()

    @model_validator(mode="after")
    def validate_commercial_rules(self) -> "OrderBasePayload":
        if self.fecha_entrega < date.today():
            raise ValueError("La fecha de entrega no puede ser anterior al día de hoy.")
        if self.descuento is None and self.motivo_descuento is not None:
            raise ValueError("No debes enviar motivo si no existe descuento.")
        if self.descuento is not None and self.motivo_descuento is None:
            raise ValueError("Debes especificar el motivo del descuento.")
        if self.descuento is not None and self.descuento > self.precio:
            raise ValueError("El descuento no puede ser mayor al precio base.")
        if self.viaje and not (self.pais_destino or self.ciudad_destino):
            raise ValueError("Los pedidos de viaje requieren país o ciudad destino.")
        return self


class OrderCreateRequest(BaseModel):
    order: OrderBasePayload
    detail: dict[str, Any]


class OrderUpdateRequest(BaseModel):
    order: OrderBasePayload
    detail: dict[str, Any] | None = None


class OrderStatusUpdateRequest(BaseModel):
    target_state: EstadoPedidoGeneralEnum
    reason: str = Field(min_length=5, max_length=300)

    @field_validator("reason", mode="before")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        return value.strip().upper()


class OrderDeliverRequest(BaseModel):
    fecha_entrega_final: date
    observaciones: str | None = None

    @field_validator("observaciones", mode="before")
    @classmethod
    def normalize_observaciones(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()


class OrderListItem(ORMBaseModel):
    id: int
    codigo: str
    tipo: TipoPedidoEnum
    client_id: int
    client_name: str
    fecha_entrega: date
    precio_total: float
    total_pagado: float
    saldo: float
    estado_general: EstadoPedidoGeneralEnum
    habilitado: bool
    viaje: bool


class OrderPaymentSummary(ORMBaseModel):
    id: int
    fecha: datetime
    monto: float
    monto_bob: float
    metodo_pago: MetodoPagoEnum
    estado: EstadoPagoPedidoEnum


class OrderTestSummary(ORMBaseModel):
    id: int
    numero: int
    fecha: date
    hora: time | None
    estado: PruebaEstadoPedidoEnum


class OrderDetailResponse(ORMBaseModel):
    id: int
    codigo: str
    tipo: TipoPedidoEnum
    client: OrderClientSummary
    usuario_encargado: OrderUserSummary
    fecha_contrato: datetime
    fecha_entrega: date
    fecha_entrega_final: date | None
    viaje: bool
    pais_destino: str | None
    ciudad_destino: str | None
    precio: float
    descuento: float | None
    motivo_descuento: MotivoDescuentoPedidoEnum | None
    precio_total: float
    total_pagado: float
    saldo: float
    observaciones: str | None
    estado_general: EstadoPedidoGeneralEnum
    fecha_cambio_estado: datetime | None
    motivo_cambio_estado: str | None
    habilitado: bool
    detail: dict[str, Any] | None
    pagos: list[OrderPaymentSummary]
    pruebas: list[OrderTestSummary]


class OrderPaymentCreateRequest(BaseModel):
    currency_id: int = Field(gt=0)
    monto: float = Field(gt=0)
    metodo_pago: MetodoPagoEnum
    observaciones: str | None = None
    receipt_customer_snapshot: ReceiptCustomerSnapshotPayload | None = None

    @field_validator("observaciones", mode="before")
    @classmethod
    def normalize_observaciones(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()


class OrderPaymentAnnulRequest(BaseModel):
    reason: str = Field(min_length=5, max_length=300)

    @field_validator("reason", mode="before")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        return value.strip().upper()


class OrderPaymentListItem(ORMBaseModel):
    id: int
    pedido_id: int
    pedido_codigo: str
    client_name: str
    currency: OrderCurrencySummary
    fecha: datetime
    monto: float
    tipo_cambio_usado: float
    monto_bob: float
    metodo_pago: MetodoPagoEnum
    estado: EstadoPagoPedidoEnum
    registered_by: str


class OrderPaymentDetailResponse(OrderPaymentListItem):
    observaciones: str | None
    fecha_cambio_estado: datetime | None
    motivo_cambio_estado: str | None
    receipt: ReceiptSummary | None = None


class OrderTestCreateRequest(BaseModel):
    numero: int = Field(gt=0)
    fecha: date
    hora: time | None = None
    estado: PruebaEstadoPedidoEnum
    observaciones: str | None = None

    @field_validator("observaciones", mode="before")
    @classmethod
    def normalize_observaciones(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()


class OrderTestUpdateRequest(BaseModel):
    fecha: date
    hora: time | None = None
    estado: PruebaEstadoPedidoEnum
    observaciones: str | None = None

    @field_validator("observaciones", mode="before")
    @classmethod
    def normalize_observaciones(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()


class OrderTestListItem(ORMBaseModel):
    id: int
    pedido_id: int
    pedido_codigo: str
    tipo: TipoPedidoEnum
    client_name: str
    numero: int
    fecha: date
    hora: time | None
    estado: PruebaEstadoPedidoEnum
    observaciones: str | None
    fecha_entrega: date


class ClientOrderSummaryReport(ORMBaseModel):
    client: OrderClientSummary
    total_contratado: float
    total_pagado: float
    saldo_pendiente: float
    pedidos_activos: int
    pedidos_inactivos: int
    pedidos_entregados: int
    pedidos_cancelados: int
    orders: list[OrderListItem]
    payments: list[OrderPaymentListItem]


class OrderBalanceReportItem(ORMBaseModel):
    client_id: int
    client_name: str
    total_contratado: float
    total_pagado: float
    saldo_pendiente: float
    active_orders: int
