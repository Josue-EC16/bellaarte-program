"""Shared economic facts and source locks; helpers never commit transactions."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from functools import wraps

from fastapi import HTTPException
from sqlalchemy import func, select

from app.models.boutique_enums import (
    EstadoEgresoEnum, EstadoPagoPedidoEnum, EstadoPedidoGeneralEnum,
    EstadoSalidaFleteEnum, EstadoVentaBoutiqueEnum, TipoEgresoEnum,
)
from app.models.boutique_item import ItemBoutique
from app.models.boutique_sale import VentaBoutique
from app.models.economy import Egreso, MovimientoEconomico
from app.models.flete import FleteVestido, SalidaFlete
from app.models.order import PagoPedido, Pedido
from app.services.economic_ledger_service import money as _validated_money
from app.services.economy_query_service import refund_totals_query


def rollback_on_error(operation):
    """A coordinator failure must never leave mutations available to a caller."""
    @wraps(operation)
    def guarded(db, *args, **kwargs):
        try:
            return operation(db, *args, **kwargs)
        except Exception:
            db.rollback()
            raise
    return guarded


def money(value) -> Decimal:
    return _validated_money(value if value is not None else 0)


def rate(value) -> Decimal:
    result = Decimal(str(value)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    if not result.is_finite() or result <= 0 or result >= Decimal("100000000"):
        raise HTTPException(status_code=422, detail="Tipo de cambio inválido.")
    return result


def refund_totals(db, origin_type: str, origin_id: int) -> Decimal:
    original = money(db.execute(select(func.coalesce(func.sum(Egreso.monto), 0)).where(
        Egreso.tipo == TipoEgresoEnum.DEVOLUCION,
        Egreso.tabla_referencia == origin_type.lower(), Egreso.id_referencia == origin_id,
        Egreso.estado == EstadoEgresoEnum.REGISTRADO,
    )).scalar_one())
    adjustments = money(db.execute(select(func.coalesce(func.sum(MovimientoEconomico.monto_bob), 0))
                                   .join(Egreso, Egreso.id == MovimientoEconomico.egreso_id).where(
        MovimientoEconomico.evento == "ajuste_egreso", Egreso.tipo == TipoEgresoEnum.DEVOLUCION,
        Egreso.tabla_referencia == origin_type.lower(), Egreso.id_referencia == origin_id,
        Egreso.estado == EstadoEgresoEnum.REGISTRADO,
    )).scalar_one())
    return original - adjustments


def effective_order_paid(db, order_id: int) -> Decimal:
    # Annulment is operational. Historical collections remain real until returned.
    refunds = refund_totals_query()
    return money(db.execute(select(func.coalesce(func.sum(
        PagoPedido.monto_bob - func.coalesce(refunds.c.refunded, 0)), 0))
        .outerjoin(refunds, (refunds.c.origin == "pago_pedido") & (refunds.c.source_id == PagoPedido.id))
        .where(PagoPedido.pedido_id == order_id)).scalar_one())


def order_financial_summary(db, order: Pedido) -> dict:
    gross = money(db.execute(select(func.coalesce(func.sum(PagoPedido.monto_bob), 0))
                            .where(PagoPedido.pedido_id == order.id)).scalar_one())
    effective = effective_order_paid(db, order.id)
    cancelled = order.estado_general == EstadoPedidoGeneralEnum.CANCELADO
    return {"total_cobrado_bruto_bob": gross, "total_devuelto_bob": gross - effective,
            "total_pagado": effective,
            "saldo_exigible_bob": Decimal("0.00") if cancelled else max(Decimal("0.00"), money(order.precio_total) - effective),
            "devolucion_pendiente_bob": effective if cancelled else Decimal("0.00")}


def recalculate_order_amounts(db, order: Pedido) -> None:
    db.flush()
    db.refresh(order, attribute_names=["precio_total"])
    order.total_pagado = effective_order_paid(db, order.id)
    order.saldo = (Decimal("0.00") if order.estado_general == EstadoPedidoGeneralEnum.CANCELADO
                   else max(Decimal("0.00"), money(order.precio_total) - order.total_pagado))
    db.flush()


def _lock(db, model, identifier):
    with db.no_autoflush:
        entity = db.execute(select(model).where(model.id == identifier)
                            .with_for_update().execution_options(populate_existing=True)).scalar_one_or_none()
    if entity is None:
        raise HTTPException(status_code=404, detail="Origen económico no encontrado.")
    return entity


def ensure_source_access(account, source, cut) -> None:
    if account.rol.codigo == "ADMIN":
        return
    if account.rol.codigo != "CAJA" or cut is None or source.usuario_id != account.usuario_id or source.corte_id != cut.id:
        raise HTTPException(status_code=403, detail="Solo puedes operar sobre ingresos propios de tu corte activo.")


def lock_financial_source(db, *, origin_type: str, origin_id: int, account, cut=None):
    # Cut must be locked by caller before any source. Discover parent identifiers
    # without locking, then acquire a consistent parent-to-child order.
    with db.no_autoflush:
        if origin_type == "VENTA_BOUTIQUE":
            parent = db.execute(select(VentaBoutique.item_id).where(VentaBoutique.id == origin_id)).scalar_one_or_none()
            if parent is not None:
                _lock(db, ItemBoutique, parent)
            source = _lock(db, VentaBoutique, origin_id)
        elif origin_type == "PAGO_PEDIDO":
            parent = db.execute(select(PagoPedido.pedido_id).where(PagoPedido.id == origin_id)).scalar_one_or_none()
            if parent is not None:
                _lock(db, Pedido, parent)
            source = _lock(db, PagoPedido, origin_id)
        elif origin_type == "SALIDA_FLETE":
            parent = db.execute(select(SalidaFlete.flete_id).where(SalidaFlete.id == origin_id)).scalar_one_or_none()
            if parent is not None:
                lock_flete(db, parent)
            source = _lock(db, SalidaFlete, origin_id)
        else:
            raise HTTPException(status_code=422, detail="Tipo de origen económico inválido.")
    ensure_source_access(account, source, cut)
    return source


def lock_flete(db, flete_id):
    with db.no_autoflush:
        item_id = db.execute(select(FleteVestido.item_id).where(FleteVestido.id == flete_id)).scalar_one_or_none()
        if item_id is not None:
            _lock(db, ItemBoutique, item_id)
        return _lock(db, FleteVestido, flete_id)


def source_financial_amount(source, origin_type: str) -> Decimal:
    field = {"VENTA_BOUTIQUE": "total", "PAGO_PEDIDO": "monto_bob", "SALIDA_FLETE": "total_flete"}.get(origin_type)
    if field is None:
        raise HTTPException(status_code=422, detail="Tipo de origen económico inválido.")
    return money(getattr(source, field))


def source_is_cancelled(source, origin_type: str) -> bool:
    if origin_type == "VENTA_BOUTIQUE":
        return source.estado != EstadoVentaBoutiqueEnum.ACTIVA
    if origin_type == "PAGO_PEDIDO":
        return (source.estado == EstadoPagoPedidoEnum.ANULADO
                or source.pedido.estado_general == EstadoPedidoGeneralEnum.CANCELADO)
    return source.estado_salida == EstadoSalidaFleteEnum.ANULADO


def source_refund_summary(db, origin_type: str, source) -> dict:
    gross = source_financial_amount(source, origin_type)
    refunded = refund_totals(db, origin_type, source.id)
    refundable = max(Decimal("0.00"), gross - refunded)
    return {"gross": gross, "refunded": refunded, "refundable": refundable,
            "pending": refundable if source_is_cancelled(source, origin_type) else Decimal("0.00")}
