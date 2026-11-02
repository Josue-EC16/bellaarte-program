from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.boutique_enums import EstadoCorteCajaEnum, EstadoEgresoEnum, TipoEgresoEnum, MetodoPagoEnum
from app.schemas.common import ORMBaseModel


IncomeSourceType = Literal["VENTA_BOUTIQUE", "PAGO_PEDIDO", "SALIDA_FLETE"]
RefundTargetState = Literal["CANCELADA", "ANULADA"]


def _normalize_upper(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    return normalized or None


class ExpenseCreateRequest(BaseModel):
    tipo: TipoEgresoEnum
    concepto: str = Field(min_length=3, max_length=150)
    cantidad: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    precio_unidad: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    metodo_pago: MetodoPagoEnum
    beneficiario: str | None = Field(default=None, max_length=120)
    observaciones_1: str | None = None
    observaciones_2: str | None = None

    @field_validator("concepto", "beneficiario", "observaciones_1", "observaciones_2", mode="before")
    @classmethod
    def normalize_upper_text(cls, value: str | None) -> str | None:
        return _normalize_upper(value)


class ExpenseAnnulRequest(BaseModel):
    money_did_not_leave: bool = False
    adjustment_method: MetodoPagoEnum | None = None
    motivo: str = Field(min_length=5, max_length=300)

    @field_validator("motivo", mode="before")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        return _normalize_upper(value) or ""


class CashCutCreateRequest(BaseModel):
    cajero_id: int = Field(gt=0)
    fondo_asignado: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    observaciones_apertura: str | None = None

    @field_validator("observaciones_apertura", mode="before")
    @classmethod
    def normalize_opening_notes(cls, value: str | None) -> str | None:
        return _normalize_upper(value)


class CashCutCloseRequest(BaseModel):
    efectivo_recibido: dict[str, Decimal] = Field(default_factory=dict)
    cierre_legado: bool = False
    estado: Literal[EstadoCorteCajaEnum.CERRADO, EstadoCorteCajaEnum.CERRADO_OBSERVADO]
    observaciones_cierre: str | None = None

    @field_validator("observaciones_cierre", mode="before")
    @classmethod
    def normalize_close_notes(cls, value: str | None) -> str | None:
        return _normalize_upper(value)

    @model_validator(mode="after")
    def validate_observed_close(self) -> "CashCutCloseRequest":
        for code, amount in self.efectivo_recibido.items():
            if not code.isalpha() or len(code) != 3 or code != code.upper():
                raise ValueError("Usa el código de moneda en mayúsculas (BOB, USD).")
            if not amount.is_finite() or amount < 0 or amount.as_tuple().exponent < -2:
                raise ValueError("El efectivo recibido debe ser no negativo y tener hasta dos decimales.")
        if self.estado == EstadoCorteCajaEnum.CERRADO_OBSERVADO and not self.observaciones_cierre:
            raise ValueError("Debes registrar la observación de cierre cuando el estado es CERRADO OBSERVADO.")
        return self


class RefundFlowRequest(BaseModel):
    origin_type: IncomeSourceType
    origin_id: int = Field(gt=0)
    target_state: None = None
    payment_method: MetodoPagoEnum
    refund_amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    reason: str = Field(min_length=5, max_length=300)
    concepto: str = Field(min_length=3, max_length=150)
    beneficiario: str | None = Field(default=None, max_length=120)
    observaciones: str | None = None

    @field_validator("origin_type", mode="before")
    @classmethod
    def normalize_catalogs(cls, value: str) -> str:
        return (_normalize_upper(value) or "")

    @field_validator("reason", "concepto", "beneficiario", "observaciones", mode="before")
    @classmethod
    def normalize_texts(cls, value: str | None) -> str | None:
        return _normalize_upper(value)


class RefundContextResponse(BaseModel):
    origin_type: IncomeSourceType
    origin_id: int
    source_code: str
    client_name: str | None
    registered_by: str
    currency_code: str | None
    currency_symbol: str | None
    amount_bob: float
    amount_origin: float | None
    exchange_rate_used: float | None
    payment_method: str | None
    current_state: str
    refunded_amount_bob: float
    refundable_balance_bob: float
    pending_refund_bob: float = 0
    net_collected_bob: float = 0
    can_refund: bool = True
    refund_block_reason: str | None = None
    available_target_states: list[RefundTargetState]
    suggested_concept: str
    suggested_beneficiary: str | None


class OperativeCancellationRequest(BaseModel):
    origin_type: IncomeSourceType
    origin_id: int = Field(gt=0)
    target_state: RefundTargetState
    reason: str = Field(min_length=5, max_length=300)

    @field_validator("reason", mode="before")
    @classmethod
    def normalize_reason(cls, value):
        return _normalize_upper(value)


class GuaranteeMovementRequest(BaseModel):
    action: Literal["RECEIVE", "RETURN", "RETAIN"]
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    payment_method: MetodoPagoEnum
    reason: str = Field(min_length=5, max_length=300)


class RefundFlowResponse(BaseModel):
    origin_type: IncomeSourceType
    origin_id: int
    target_state: RefundTargetState | None = None
    constancia_id: int | None = None
    refundable_balance_bob: float = 0
    refund_amount_bob: float
    expense_id: int
    expense_amount_bob: float
    origin_state: str


class UserMiniSummary(ORMBaseModel):
    id: int
    full_name: str
    username: str | None = None


class CashCutMiniSummary(ORMBaseModel):
    id: int
    estado: EstadoCorteCajaEnum
    fecha_apertura: datetime
    fecha_cierre: datetime | None
    fondo_asignado: float


class ExpenseListItem(ORMBaseModel):
    metodo_pago: str | None = None
    adjusted_amount_bob: float = 0
    net_amount_bob: float = 0
    id: int
    fecha: datetime
    tipo: TipoEgresoEnum
    concepto: str
    cantidad: float
    precio_unidad: float
    monto: float
    beneficiario: str | None
    estado: EstadoEgresoEnum
    usuario: UserMiniSummary | None
    corte: CashCutMiniSummary | None
    tabla_referencia: str | None
    id_referencia: int | None


class ExpenseDetailResponse(ExpenseListItem):
    constancia_id: int | None = None
    observaciones_1: str | None
    observaciones_2: str | None
    fecha_cambio_estado: datetime | None
    motivo_cambio_estado: str | None


class CashCutListItem(ORMBaseModel):
    control_version: int = 0
    certified: bool = False
    efectivo_esperado: dict[str, float] = Field(default_factory=dict)
    efectivo_recibido: dict[str, float] = Field(default_factory=dict)
    diferencias_efectivo: dict[str, float] = Field(default_factory=dict)
    efectivo_libre_bob: float | None = None
    garantias_reservadas_bob: float | None = None
    id: int
    cajero: UserMiniSummary
    admin: UserMiniSummary
    fecha_apertura: datetime
    fecha_cierre: datetime | None
    fondo_asignado: float
    estado: EstadoCorteCajaEnum
    ingresos_total_bob: float
    egresos_total_bob: float
    resultado_bob: float | None


class CashCutDetailResponse(CashCutListItem):
    observaciones_apertura: str | None
    observaciones_cierre: str | None
    ingresos_por_fuente: list["NamedAmountBucket"]
    ingresos_por_metodo_pago: list["NamedAmountBucket"]
    ingresos_por_moneda: list["NamedAmountBucket"]
    egresos_por_tipo: list["NamedAmountBucket"]
    egresos: list[ExpenseListItem]


class CashCutOwnActiveResponse(ORMBaseModel):
    has_active_cut: bool
    cut: CashCutListItem | None


class CashCutOwnHistoryItem(ORMBaseModel):
    control_version: int = 0
    certified: bool = False
    id: int
    fecha_apertura: datetime
    fecha_cierre: datetime | None
    fondo_asignado: float
    estado: EstadoCorteCajaEnum
    ingresos_display: str
    ventas_display: str
    pagos_display: str
    fletes_display: str
    metodos_display: str
    resultado_display: str
    egresos_total_bob: float
    has_observation: bool


class IncomeListItem(ORMBaseModel):
    source_type: IncomeSourceType
    source_id: int
    source_code: str
    fecha: datetime
    cliente: str | None
    usuario: str
    metodo_pago: str | None
    moneda: str | None
    simbolo_moneda: str | None
    monto_moneda_origen: float | None
    tipo_cambio_usado: float | None
    monto_bob: float
    estado_origen: str
    corte_id: int | None = None
    monto_neto_bob: float = 0
    pendiente_devolucion_bob: float = 0
    monto_devuelto_bob: float


class NamedAmountBucket(BaseModel):
    label: str
    total_bob: float
    amount_origin: float | None = None
    currency_code: str | None = None
    symbol: str | None = None


class TimeSeriesBucket(BaseModel):
    period: str
    ingresos_total_bob: float
    egresos_total_bob: float
    resultado_bob: float | None
    efectivo: float = 0
    qr: float = 0
    transaccion: float = 0
    tarjeta: float = 0
    ticket_o_vale: float = 0


class IncomeStatementReportResponse(BaseModel):
    comparable: bool = True
    comparison_note: str | None = None
    ingresos_total_bob: float
    egresos_total_bob: float
    resultado_bob: float | None
    ingresos_por_fuente: list[NamedAmountBucket]
    egresos_por_tipo: list[NamedAmountBucket]
    serie_mensual: list[TimeSeriesBucket]


class CashFlowReportResponse(BaseModel):
    comparable: bool = True
    comparison_note: str | None = None
    entradas_total_bob: float
    egresos_total_bob: float
    flujo_neto_bob: float | None
    entradas_por_metodo: list[NamedAmountBucket]
    entradas_por_fuente: list[NamedAmountBucket]
    entradas_por_moneda: list[NamedAmountBucket]
    serie_periodica: list[TimeSeriesBucket]


class CashierReportResponse(BaseModel):
    cajero: UserMiniSummary
    cortes: list[CashCutListItem]
    comparativo_periodos: list[TimeSeriesBucket]


class MyPeriodReportResponse(BaseModel):
    has_active_cut: bool
    message: str | None = None
    cut: CashCutListItem | None = None
    ingresos_total_bob: float = 0
    egresos_total_bob: float = 0
    resultado_bob: float = 0
    ingresos_por_fuente: list[NamedAmountBucket] = []
    ingresos_por_metodo_pago: list[NamedAmountBucket] = []
    ingresos_por_moneda: list[NamedAmountBucket] = []
    egresos_por_tipo: list[NamedAmountBucket] = []
    egresos: list[ExpenseListItem] = []


class MyIncomeStatementResponse(BaseModel):
    has_active_cut: bool
    message: str | None = None
    ingresos_total_bob: float = 0
    egresos_total_bob: float = 0
    resultado_bob: float = 0


class MyHistoryReportResponse(BaseModel):
    cuts: list[CashCutOwnHistoryItem]


class IncomePageResponse(BaseModel):
    items: list[IncomeListItem]
    total: int
    page: int
    page_size: int
    total_bob: float
    refunded_total_bob: float


class ExpensePageResponse(BaseModel):
    items: list[ExpenseListItem]
    total: int
    page: int
    page_size: int
    total_bob: float


class EconomyFilters(BaseModel):
    search: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    source_type: IncomeSourceType | None = None
    expense_type: TipoEgresoEnum | None = None
    currency_id: int | None = None
    payment_method: str | None = None
    cashier_id: int | None = None
    cut_id: int | None = None

    @field_validator("search", "payment_method", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        return _normalize_upper(value)

    @model_validator(mode="after")
    def ordered_dates(self):
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("La fecha inicial no puede ser posterior a la final.")
        return self


CashCutDetailResponse.model_rebuild()


class CashCutPageResponse(BaseModel):
    items: list[CashCutListItem]
    total: int
    page: int
    page_size: int
    open_count: int
    closed_count: int
    observed_count: int


class CashCutOwnHistoryPageResponse(BaseModel):
    items: list[CashCutOwnHistoryItem]
    total: int
    page: int
    page_size: int
