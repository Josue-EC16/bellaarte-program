from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.models.boutique_enums import EstadoCorteCajaEnum
from app.models.boutique_sale import VentaBoutique
from app.models.economy import CorteCaja
from app.models.flete import SalidaFlete
from app.models.order import PagoPedido, Pedido
from app.schemas.economy import IncomeListItem, IncomePageResponse, RefundContextResponse, IncomeSourceType, RefundTargetState
from app.services.economy_query_service import income_scope, date_bounds


def _is_admin(account):
    return account.rol.codigo == "ADMIN"


def _get_active_cut_for_cajero(db, *, cajero_id):
    return db.execute(select(CorteCaja).where(CorteCaja.cajero_id == cajero_id,
        CorteCaja.estado == EstadoCorteCajaEnum.ABIERTO)).scalar_one_or_none()


def _row_item(row):
    data = dict(row)
    data["monto_neto_bob"] = data["monto_bob"] - data["monto_devuelto_bob"]
    data["pendiente_devolucion_bob"] = data["monto_neto_bob"] if data.pop("pending_refund",False) else 0
    return IncomeListItem(**data)


def collect_income_rows_for_period(db, **filters):
    scope = income_scope(**filters)
    return [_row_item(row) for row in db.execute(select(scope).order_by(
        scope.c.fecha.desc(), scope.c.source_type, scope.c.source_id.desc())).mappings()]


def list_income_rows(db, *, account, page=1, page_size=25, **filters):
    date_bounds(filters.get("date_from"),filters.get("date_to"))
    if page<1 or not 1<=page_size<=100:
        raise HTTPException(422,"La paginación exige página positiva y tamaño entre 1 y 100.")
    if not _is_admin(account):
        requested = filters.get("user_id")
        if requested is not None and requested != account.usuario_id:
            raise HTTPException(403, "Solo puedes consultar tus propios ingresos.")
        cut = _get_active_cut_for_cajero(db, cajero_id=account.usuario_id)
        if cut is None:
            return IncomePageResponse(items=[], total=0,page=page,page_size=page_size,total_bob=0,refunded_total_bob=0)
        filters["user_id"] = account.usuario_id
        if cut.control_version:
            filters["cut_id"] = cut.id
        else:
            filters.update(start_at=cut.fecha_apertura,end_at=cut.fecha_cierre)
    scope = income_scope(**filters)
    count, gross, refunded = db.execute(select(func.count(),func.coalesce(func.sum(scope.c.monto_bob),0),
        func.coalesce(func.sum(scope.c.monto_devuelto_bob),0)).select_from(scope)).one()
    rows = db.execute(select(scope).order_by(scope.c.fecha.desc(),scope.c.source_type,scope.c.source_id.desc())
        .offset((page-1)*page_size).limit(page_size)).mappings()
    return IncomePageResponse(items=[_row_item(row) for row in rows],total=count,page=page,page_size=page_size,
        total_bob=gross,refunded_total_bob=refunded)


def get_income_refund_context(db, *, origin_type, origin_id, account):
    from app.services.financial_source_service import ensure_source_access, source_refund_summary
    from app.models.boutique_enums import EstadoPedidoGeneralEnum
    models = {"VENTA_BOUTIQUE": VentaBoutique,"PAGO_PEDIDO":PagoPedido,"SALIDA_FLETE":SalidaFlete}
    if origin_type not in models:
        raise HTTPException(422,"El tipo de ingreso no es válido.")
    source = db.get(models[origin_type], origin_id)
    if source is None:
        raise HTTPException(404,"No se encontró la operación de origen.")
    cut = None if _is_admin(account) else _get_active_cut_for_cajero(db,cajero_id=account.usuario_id)
    ensure_source_access(account,source,cut)
    summary = source_refund_summary(db,origin_type,source)
    if origin_type == "VENTA_BOUTIQUE":
        client=source.cliente
        code=f"VENTA #{source.id} - {source.item.codigo}"
        original=source.total_moneda_original
        state=source.estado.value.upper()
        gross=source.total
    elif origin_type == "PAGO_PEDIDO":
        client=source.pedido.cliente
        code=f"PAGO #{source.id} - {source.pedido.codigo}"
        original=source.monto
        state=source.estado.value.upper()
        gross=source.monto_bob
    else:
        client=source.cliente
        code=f"FLETE #{source.id} - {source.flete.item.codigo}"
        original=source.total_flete_moneda_original
        state=source.estado_salida.value.upper()
        gross=source.total_flete
    blocked = origin_type == "PAGO_PEDIDO" and source.pedido.estado_general == EstadoPedidoGeneralEnum.ENTREGADO
    refunded = summary["refunded"]
    return RefundContextResponse(origin_type=origin_type,origin_id=origin_id,source_code=code,
        client_name=client.nombre_completo if client else None,registered_by=source.usuario.nombre_completo,
        currency_code=source.moneda.codigo,currency_symbol=source.moneda.simbolo,amount_bob=gross,
        amount_origin=original,exchange_rate_used=source.tipo_cambio_usado,payment_method=source.metodo_pago.value,
        current_state=state,refunded_amount_bob=refunded,refundable_balance_bob=summary["refundable"],
        pending_refund_bob=summary["pending"],net_collected_bob=summary["refundable"],can_refund=not blocked,
        refund_block_reason="Los pedidos entregados requieren un procedimiento de devolución específico." if blocked else None,
        available_target_states=[] if state in {"CANCELADA","ANULADA","ANULADO"} else (["CANCELADA","ANULADA"] if origin_type == "VENTA_BOUTIQUE" else ["ANULADA"]),
        suggested_concept="DEVOLUCIÓN " + code,suggested_beneficiary=client.nombre_completo if client else None)


def validate_refund_target_state(
    *,
    origin_type: IncomeSourceType,
    target_state: RefundTargetState,
) -> None:
    if origin_type == "VENTA_BOUTIQUE" and target_state in {"CANCELADA", "ANULADA"}:
        return
    if origin_type in {"PAGO_PEDIDO", "SALIDA_FLETE"} and target_state == "ANULADA":
        return
    raise HTTPException(status_code=409, detail="El estado destino no es válido para el ingreso seleccionado.")
