from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.account import Cuenta
from app.models.boutique_enums import EstadoCorteCajaEnum, EstadoEgresoEnum, EstadoPagoPedidoEnum, EstadoSalidaFleteEnum, EstadoVentaBoutiqueEnum, TipoEgresoEnum
from app.models.boutique_item import ItemBoutique
from app.models.boutique_sale import VentaBoutique
from app.models.client import Cliente
from app.models.currency import Moneda
from app.models.economy import CorteCaja, Egreso
from app.models.flete import FleteVestido, SalidaFlete
from app.models.order import PagoPedido, Pedido
from app.models.user import Usuario
from app.schemas.economy import IncomeListItem, IncomeSourceType, RefundContextResponse, RefundTargetState


def _to_float(value: Decimal | float | int | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _is_admin(account: Cuenta) -> bool:
    return account.rol.codigo == "ADMIN"


def _get_active_cut_for_cajero(db: Session, *, cajero_id: int) -> CorteCaja | None:
    return db.execute(
        select(CorteCaja)
        .where(CorteCaja.cajero_id == cajero_id, CorteCaja.estado == EstadoCorteCajaEnum.ABIERTO)
        .options(joinedload(CorteCaja.cajero), joinedload(CorteCaja.admin))
    ).scalar_one_or_none()


def _build_refund_totals(db: Session) -> dict[tuple[str, int], float]:
    rows = db.execute(
        select(Egreso.tabla_referencia, Egreso.id_referencia, func.coalesce(func.sum(Egreso.monto), 0))
        .where(Egreso.tipo == TipoEgresoEnum.DEVOLUCION, Egreso.estado == EstadoEgresoEnum.REGISTRADO)
        .group_by(Egreso.tabla_referencia, Egreso.id_referencia)
    ).all()
    return {(row[0], int(row[1])): float(row[2] or 0) for row in rows if row[0] and row[1] is not None}


def _matches_search(term: str, *values: str | None) -> bool:
    if not term:
        return True
    normalized = term.strip().upper()
    return any(normalized in (value or "").upper() for value in values)


def _get_period_bounds_for_account(
    db: Session,
    *,
    account: Cuenta,
) -> tuple[datetime | None, datetime | None]:
    if _is_admin(account):
        return None, None
    active_cut = _get_active_cut_for_cajero(db, cajero_id=account.usuario_id)
    if active_cut is None:
        return None, None
    return active_cut.fecha_apertura, active_cut.fecha_cierre


def collect_income_rows_for_period(
    db: Session,
    *,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    user_id: int | None = None,
    search: str | None = None,
    source_type: IncomeSourceType | None = None,
    currency_id: int | None = None,
    payment_method: str | None = None,
    date_from=None,
    date_to=None,
) -> list[IncomeListItem]:
    refund_totals = _build_refund_totals(db)
    items: list[IncomeListItem] = []

    if source_type in (None, "VENTA_BOUTIQUE"):
        stmt = (
            select(VentaBoutique)
            .options(
                joinedload(VentaBoutique.item),
                joinedload(VentaBoutique.cliente),
                joinedload(VentaBoutique.usuario),
                joinedload(VentaBoutique.moneda),
            )
            .order_by(VentaBoutique.fecha.desc(), VentaBoutique.id.desc())
        )
        if user_id is not None:
            stmt = stmt.where(VentaBoutique.usuario_id == user_id)
        if start_at is not None:
            stmt = stmt.where(VentaBoutique.fecha >= start_at)
        if end_at is not None:
            stmt = stmt.where(VentaBoutique.fecha <= end_at)
        if currency_id is not None:
            stmt = stmt.where(VentaBoutique.moneda_id == currency_id)
        if payment_method:
            stmt = stmt.where(func.upper(VentaBoutique.metodo_pago) == payment_method.upper())
        if date_from is not None:
            stmt = stmt.where(func.date(VentaBoutique.fecha) >= date_from)
        if date_to is not None:
            stmt = stmt.where(func.date(VentaBoutique.fecha) <= date_to)
        for sale in db.execute(stmt).unique().scalars().all():
            if not _matches_search(
                search or "",
                sale.item.codigo,
                sale.item.nombre,
                sale.cliente.nombre_completo if sale.cliente else None,
                sale.usuario.nombre_completo,
                f"VENTA {sale.id}",
            ):
                continue
            items.append(
                IncomeListItem(
                    source_type="VENTA_BOUTIQUE",
                    source_id=sale.id,
                    source_code=f"VENTA #{sale.id} - {sale.item.codigo}",
                    fecha=sale.fecha,
                    cliente=sale.cliente.nombre_completo if sale.cliente else None,
                    usuario=sale.usuario.nombre_completo,
                    metodo_pago=sale.metodo_pago.value,
                    moneda=sale.moneda.codigo,
                    simbolo_moneda=sale.moneda.simbolo,
                    monto_moneda_origen=float(sale.total_moneda_original),
                    tipo_cambio_usado=float(sale.tipo_cambio_usado),
                    monto_bob=float(sale.total),
                    estado_origen=sale.estado.value.upper(),
                    monto_devuelto_bob=refund_totals.get(("venta_boutique", sale.id), 0),
                )
            )

    if source_type in (None, "PAGO_PEDIDO"):
        stmt = (
            select(PagoPedido)
            .options(
                joinedload(PagoPedido.pedido).joinedload(Pedido.cliente),
                joinedload(PagoPedido.usuario),
                joinedload(PagoPedido.moneda),
            )
            .order_by(PagoPedido.fecha.desc(), PagoPedido.id.desc())
        )
        if user_id is not None:
            stmt = stmt.where(PagoPedido.usuario_id == user_id)
        if start_at is not None:
            stmt = stmt.where(PagoPedido.fecha >= start_at)
        if end_at is not None:
            stmt = stmt.where(PagoPedido.fecha <= end_at)
        if currency_id is not None:
            stmt = stmt.where(PagoPedido.moneda_id == currency_id)
        if payment_method:
            stmt = stmt.where(func.upper(PagoPedido.metodo_pago) == payment_method.upper())
        if date_from is not None:
            stmt = stmt.where(func.date(PagoPedido.fecha) >= date_from)
        if date_to is not None:
            stmt = stmt.where(func.date(PagoPedido.fecha) <= date_to)
        for payment in db.execute(stmt).unique().scalars().all():
            if not _matches_search(
                search or "",
                payment.pedido.codigo,
                payment.pedido.cliente.nombre_completo,
                payment.usuario.nombre_completo,
                f"PAGO {payment.id}",
            ):
                continue
            items.append(
                IncomeListItem(
                    source_type="PAGO_PEDIDO",
                    source_id=payment.id,
                    source_code=f"PAGO #{payment.id} - {payment.pedido.codigo}",
                    fecha=payment.fecha,
                    cliente=payment.pedido.cliente.nombre_completo,
                    usuario=payment.usuario.nombre_completo,
                    metodo_pago=payment.metodo_pago.value,
                    moneda=payment.moneda.codigo,
                    simbolo_moneda=payment.moneda.simbolo,
                    monto_moneda_origen=float(payment.monto),
                    tipo_cambio_usado=float(payment.tipo_cambio_usado),
                    monto_bob=float(payment.monto_bob),
                    estado_origen=payment.estado.value.upper(),
                    monto_devuelto_bob=refund_totals.get(("pago_pedido", payment.id), 0),
                )
            )

    if source_type in (None, "SALIDA_FLETE"):
        stmt = (
            select(SalidaFlete)
            .options(
                joinedload(SalidaFlete.flete).joinedload(FleteVestido.item),
                joinedload(SalidaFlete.cliente),
                joinedload(SalidaFlete.usuario),
                joinedload(SalidaFlete.moneda),
            )
            .order_by(SalidaFlete.fecha_registro.desc(), SalidaFlete.id.desc())
        )
        if user_id is not None:
            stmt = stmt.where(SalidaFlete.usuario_id == user_id)
        if start_at is not None:
            stmt = stmt.where(SalidaFlete.fecha_registro >= start_at)
        if end_at is not None:
            stmt = stmt.where(SalidaFlete.fecha_registro <= end_at)
        if currency_id is not None:
            stmt = stmt.where(SalidaFlete.moneda_id == currency_id)
        if payment_method:
            stmt = stmt.where(func.upper(SalidaFlete.metodo_pago) == payment_method.upper())
        if date_from is not None:
            stmt = stmt.where(func.date(SalidaFlete.fecha_registro) >= date_from)
        if date_to is not None:
            stmt = stmt.where(func.date(SalidaFlete.fecha_registro) <= date_to)
        for output in db.execute(stmt).unique().scalars().all():
            if not _matches_search(
                search or "",
                output.flete.item.codigo,
                output.flete.item.nombre,
                output.cliente.nombre_completo,
                output.usuario.nombre_completo,
                f"FLETE {output.id}",
            ):
                continue
            items.append(
                IncomeListItem(
                    source_type="SALIDA_FLETE",
                    source_id=output.id,
                    source_code=f"FLETE #{output.id} - {output.flete.item.codigo}",
                    fecha=output.fecha_registro,
                    cliente=output.cliente.nombre_completo,
                    usuario=output.usuario.nombre_completo,
                    metodo_pago=output.metodo_pago.value,
                    moneda=output.moneda.codigo,
                    simbolo_moneda=output.moneda.simbolo,
                    monto_moneda_origen=float(output.total_flete_moneda_original),
                    tipo_cambio_usado=float(output.tipo_cambio_usado),
                    monto_bob=float(output.total_flete),
                    estado_origen=output.estado_salida.value.upper(),
                    monto_devuelto_bob=refund_totals.get(("salida_flete", output.id), 0),
                )
            )

    items.sort(key=lambda item: (item.fecha, item.source_id), reverse=True)
    return items


def list_income_rows(
    db: Session,
    *,
    account: Cuenta,
    search: str | None = None,
    source_type: IncomeSourceType | None = None,
    user_id: int | None = None,
    currency_id: int | None = None,
    payment_method: str | None = None,
    date_from=None,
    date_to=None,
) -> list[IncomeListItem]:
    start_at, end_at = _get_period_bounds_for_account(db, account=account)
    if not _is_admin(account) and start_at is None:
        return []
    return collect_income_rows_for_period(
        db,
        start_at=start_at,
        end_at=end_at,
        user_id=user_id if _is_admin(account) else account.usuario_id,
        search=search,
        source_type=source_type,
        currency_id=currency_id,
        payment_method=payment_method,
        date_from=date_from,
        date_to=date_to,
    )


def _build_sale_refund_context(db: Session, *, origin_id: int, refund_totals: dict[tuple[str, int], float]) -> RefundContextResponse:
    sale = db.execute(
        select(VentaBoutique)
        .options(joinedload(VentaBoutique.item), joinedload(VentaBoutique.cliente), joinedload(VentaBoutique.usuario), joinedload(VentaBoutique.moneda))
        .where(VentaBoutique.id == origin_id)
    ).scalar_one_or_none()
    if sale is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La venta boutique no existe.")
    if sale.estado != EstadoVentaBoutiqueEnum.ACTIVA:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La venta boutique ya no se encuentra activa para este flujo.")
    refunded = refund_totals.get(("venta_boutique", sale.id), 0)
    return RefundContextResponse(
        origin_type="VENTA_BOUTIQUE",
        origin_id=sale.id,
        source_code=f"VENTA #{sale.id} - {sale.item.codigo}",
        client_name=sale.cliente.nombre_completo if sale.cliente else None,
        registered_by=sale.usuario.nombre_completo,
        currency_code=sale.moneda.codigo,
        currency_symbol=sale.moneda.simbolo,
        amount_bob=float(sale.total),
        amount_origin=float(sale.total_moneda_original),
        exchange_rate_used=float(sale.tipo_cambio_usado),
        payment_method=sale.metodo_pago.value,
        current_state=sale.estado.value.upper(),
        refunded_amount_bob=refunded,
        refundable_balance_bob=max(float(sale.total) - refunded, 0),
        available_target_states=["CANCELADA", "ANULADA"],
        suggested_concept=f"DEVOLUCIÓN DE VENTA BOUTIQUE {sale.item.codigo}",
        suggested_beneficiary=sale.cliente.nombre_completo if sale.cliente else None,
    )


def _build_payment_refund_context(db: Session, *, origin_id: int, refund_totals: dict[tuple[str, int], float]) -> RefundContextResponse:
    payment = db.execute(
        select(PagoPedido)
        .options(joinedload(PagoPedido.pedido).joinedload(Pedido.cliente), joinedload(PagoPedido.usuario), joinedload(PagoPedido.moneda))
        .where(PagoPedido.id == origin_id)
    ).scalar_one_or_none()
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El pago de pedido no existe.")
    if payment.estado != EstadoPagoPedidoEnum.REGISTRADO:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El pago de pedido ya no se encuentra registrado para este flujo.")
    refunded = refund_totals.get(("pago_pedido", payment.id), 0)
    return RefundContextResponse(
        origin_type="PAGO_PEDIDO",
        origin_id=payment.id,
        source_code=f"PAGO #{payment.id} - {payment.pedido.codigo}",
        client_name=payment.pedido.cliente.nombre_completo,
        registered_by=payment.usuario.nombre_completo,
        currency_code=payment.moneda.codigo,
        currency_symbol=payment.moneda.simbolo,
        amount_bob=float(payment.monto_bob),
        amount_origin=float(payment.monto),
        exchange_rate_used=float(payment.tipo_cambio_usado),
        payment_method=payment.metodo_pago.value,
        current_state=payment.estado.value.upper(),
        refunded_amount_bob=refunded,
        refundable_balance_bob=max(float(payment.monto_bob) - refunded, 0),
        available_target_states=["ANULADA"],
        suggested_concept=f"DEVOLUCIÓN DE PAGO DE PEDIDO {payment.pedido.codigo}",
        suggested_beneficiary=payment.pedido.cliente.nombre_completo,
    )


def _build_flete_refund_context(db: Session, *, origin_id: int, refund_totals: dict[tuple[str, int], float]) -> RefundContextResponse:
    output = db.execute(
        select(SalidaFlete)
        .options(joinedload(SalidaFlete.flete).joinedload(FleteVestido.item), joinedload(SalidaFlete.cliente), joinedload(SalidaFlete.usuario), joinedload(SalidaFlete.moneda))
        .where(SalidaFlete.id == origin_id)
    ).scalar_one_or_none()
    if output is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La salida de flete no existe.")
    if output.estado_salida == EstadoSalidaFleteEnum.ANULADO:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La salida de flete ya se encuentra anulada.")
    refunded = refund_totals.get(("salida_flete", output.id), 0)
    return RefundContextResponse(
        origin_type="SALIDA_FLETE",
        origin_id=output.id,
        source_code=f"FLETE #{output.id} - {output.flete.item.codigo}",
        client_name=output.cliente.nombre_completo,
        registered_by=output.usuario.nombre_completo,
        currency_code=output.moneda.codigo,
        currency_symbol=output.moneda.simbolo,
        amount_bob=float(output.total_flete),
        amount_origin=float(output.total_flete_moneda_original),
        exchange_rate_used=float(output.tipo_cambio_usado),
        payment_method=output.metodo_pago.value,
        current_state=output.estado_salida.value.upper(),
        refunded_amount_bob=refunded,
        refundable_balance_bob=max(float(output.total_flete) - refunded, 0),
        available_target_states=["ANULADA"],
        suggested_concept=f"DEVOLUCIÓN DE FLETE {output.flete.item.codigo}",
        suggested_beneficiary=output.cliente.nombre_completo,
    )


def get_income_refund_context(
    db: Session,
    *,
    origin_type: IncomeSourceType,
    origin_id: int,
) -> RefundContextResponse:
    refund_totals = _build_refund_totals(db)
    if origin_type == "VENTA_BOUTIQUE":
        return _build_sale_refund_context(db, origin_id=origin_id, refund_totals=refund_totals)
    if origin_type == "PAGO_PEDIDO":
        return _build_payment_refund_context(db, origin_id=origin_id, refund_totals=refund_totals)
    return _build_flete_refund_context(db, origin_id=origin_id, refund_totals=refund_totals)


def validate_refund_target_state(
    *,
    origin_type: IncomeSourceType,
    target_state: RefundTargetState,
) -> None:
    if origin_type == "VENTA_BOUTIQUE" and target_state in {"CANCELADA", "ANULADA"}:
        return
    if origin_type in {"PAGO_PEDIDO", "SALIDA_FLETE"} and target_state == "ANULADA":
        return
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El estado destino no es válido para el ingreso seleccionado.")
