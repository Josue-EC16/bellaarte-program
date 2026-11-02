"""Shared, indexable economic scopes. Commercial receipts are counted once.

Ledger movements describe custody/cash attribution; they are never a second
source of commercial income. All calendar filters use America/La_Paz.
"""
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import String, cast, func, literal, or_, select, union_all

from app.models.boutique_item import ItemBoutique
from app.models.boutique_sale import VentaBoutique
from app.models.client import Cliente
from app.models.currency import Moneda
from app.models.economy import Egreso, MovimientoEconomico
from app.models.flete import FleteVestido, SalidaFlete
from app.models.order import PagoPedido, Pedido
from app.models.user import Usuario

LOCAL_ZONE = ZoneInfo("America/La_Paz")
SOURCES = {"VENTA_BOUTIQUE", "PAGO_PEDIDO", "SALIDA_FLETE"}
METHODS = {"efectivo", "qr", "transaccion", "tarjeta", "ticket_o_vale"}


def date_bounds(date_from=None, date_to=None):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(422, "La fecha inicial no puede ser posterior a la final.")
    start = datetime.combine(date_from, time.min, LOCAL_ZONE).astimezone(timezone.utc) if date_from else None
    end = datetime.combine(date_to + timedelta(days=1), time.min, LOCAL_ZONE).astimezone(timezone.utc) if date_to else None
    return start, end


def apply_dates(stmt, column, *, date_from=None, date_to=None, start_at=None, end_at=None):
    start, end = date_bounds(date_from, date_to)
    for boundary in (start, start_at):
        if boundary is not None:
            stmt = stmt.where(column >= boundary)
    if end is not None:
        stmt = stmt.where(column < end)
    if end_at is not None:
        stmt = stmt.where(column <= end_at)
    return stmt


def refund_totals_query():
    corrections = select(
        MovimientoEconomico.egreso_id.label("expense_id"),
        func.sum(MovimientoEconomico.monto_bob).label("amount"),
    ).where(MovimientoEconomico.evento == "ajuste_egreso").group_by(MovimientoEconomico.egreso_id).subquery()
    return select(
        Egreso.tabla_referencia.label("origin"), Egreso.id_referencia.label("source_id"),
        func.sum(Egreso.monto - func.coalesce(corrections.c.amount, 0)).label("refunded"),
    ).outerjoin(corrections, corrections.c.expense_id == Egreso.id).where(
        Egreso.tipo == "devolucion", Egreso.estado == "registrado",
    ).group_by(Egreso.tabla_referencia, Egreso.id_referencia).subquery()


def income_scope(*, source_type=None, payment_method=None, search=None, user_id=None,
                 currency_id=None, cut_id=None, date_from=None, date_to=None,
                 start_at=None, end_at=None):
    source_type = source_type.upper() if source_type else None
    payment_method = payment_method.lower() if payment_method else None
    if source_type and source_type not in SOURCES:
        raise HTTPException(422, "El tipo de ingreso no es válido.")
    if payment_method and payment_method not in METHODS:
        raise HTTPException(422, "El método de pago no es válido.")
    refunds = refund_totals_query()
    branches = []
    configurations = (
        ("VENTA_BOUTIQUE", VentaBoutique, VentaBoutique.fecha, VentaBoutique.total,
         VentaBoutique.total_moneda_original, VentaBoutique.estado, ItemBoutique.codigo,
         select(VentaBoutique).join(ItemBoutique, ItemBoutique.id == VentaBoutique.item_id)
         .outerjoin(Cliente, Cliente.id == VentaBoutique.cliente_id)),
        ("PAGO_PEDIDO", PagoPedido, PagoPedido.fecha, PagoPedido.monto_bob,
         PagoPedido.monto, PagoPedido.estado, Pedido.codigo,
         select(PagoPedido).join(Pedido, Pedido.id == PagoPedido.pedido_id).join(Cliente, Cliente.id == Pedido.cliente_id)),
        ("SALIDA_FLETE", SalidaFlete, SalidaFlete.fecha_registro, SalidaFlete.total_flete,
         SalidaFlete.total_flete_moneda_original, SalidaFlete.estado_salida, ItemBoutique.codigo,
         select(SalidaFlete).join(FleteVestido, FleteVestido.id == SalidaFlete.flete_id)
         .join(ItemBoutique, ItemBoutique.id == FleteVestido.item_id).join(Cliente, Cliente.id == SalidaFlete.cliente_id)),
    )
    # Names are SQL expressions, not Python properties on the ORM entities.
    client_name = func.concat_ws(" ", Cliente.nombres, Cliente.apellido_paterno, Cliente.apellido_materno)
    user_name = func.concat_ws(" ", Usuario.nombres, Usuario.apellido_paterno, Usuario.apellido_materno)
    for kind, model, stamp, amount, original, state, code, base in configurations:
        if source_type and kind != source_type:
            continue
        stmt = base.join(Usuario, Usuario.id == model.usuario_id).join(Moneda, Moneda.id == model.moneda_id)
        stmt = stmt.outerjoin(refunds, (refunds.c.origin == kind.lower()) & (refunds.c.source_id == model.id))
        stmt = stmt.with_only_columns(
            literal(kind).label("source_type"), model.id.label("source_id"),
            func.concat(kind.replace("_", " "), " #", model.id, " - ", code).label("source_code"),
            stamp.label("fecha"), client_name.label("cliente"), user_name.label("usuario"),
            cast(model.metodo_pago, String).label("metodo_pago"), Moneda.codigo.label("moneda"),
            Moneda.simbolo.label("simbolo_moneda"), original.label("monto_moneda_origen"),
            model.tipo_cambio_usado.label("tipo_cambio_usado"), amount.label("monto_bob"),
            func.upper(cast(state, String)).label("estado_origen"),
            func.coalesce(refunds.c.refunded, 0).label("monto_devuelto_bob"),
            ((cast(state,String).in_(("anulado","anulada","cancelada"))) |
             (Pedido.estado_general == "cancelado") if kind == "PAGO_PEDIDO" else cast(state,String).in_(("anulado","anulada","cancelada"))).label("pending_refund"),
            model.corte_id.label("corte_id"), model.usuario_id.label("user_id"), model.moneda_id.label("currency_id"),
        )
        if user_id is not None:
            stmt = stmt.where(model.usuario_id == user_id)
        if currency_id is not None:
            stmt = stmt.where(model.moneda_id == currency_id)
        if cut_id is not None:
            stmt = stmt.where(model.corte_id == cut_id)
        if payment_method:
            stmt = stmt.where(model.metodo_pago == payment_method)
        if search:
            term = "%" + search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            stmt = stmt.where(or_(code.ilike(term, escape="\\"), client_name.ilike(term, escape="\\"),
                                  user_name.ilike(term, escape="\\"), cast(model.id, String).ilike(term, escape="\\")))
        branches.append(apply_dates(stmt, stamp, date_from=date_from, date_to=date_to, start_at=start_at, end_at=end_at))
    return union_all(*branches).subquery("commercial_income")
