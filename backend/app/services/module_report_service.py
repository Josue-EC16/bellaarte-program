from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, Iterable

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.boutique_enums import EstadoPagoPedidoEnum, EstadoPedidoGeneralEnum, EstadoVentaBoutiqueEnum
from app.models.boutique_entry import EntradaItemBoutique
from app.models.boutique_item import ItemBoutique
from app.models.boutique_sale import VentaBoutique
from app.models.boutique_type import TipoItemBoutique
from app.models.client import Cliente
from app.models.currency import Moneda
from app.models.economy import CorteCaja, Egreso
from app.models.exchange_rate import TipoCambioMoneda
from app.models.flete import EstadoFleteEnum, EstadoSalidaFleteEnum, FleteVestido, SalidaFlete
from app.models.order import PagoPedido, Pedido, PedidoOtro, PedidoVestido, PruebaPedido
from app.models.provider import Proveedor
from app.models.receipt import ComprobanteInterno
from app.models.role import Rol
from app.models.user import Usuario
from app.models.workshop import EntradaInventarioTaller, InventarioTaller, SalidaMaterialTaller, TipoInventarioTaller
from app.schemas.reporting import AnalyticsReportResponse, ListingSummaryBreakdownItem, ListingSummaryResponse, ReportPeriod


def _to_float(value: Decimal | float | int | None) -> float:
    if value is None:
        return 0.0
    return float(value)


def _start_of_day(value: date) -> datetime:
    return datetime.combine(value, time.min)


def _end_of_day_exclusive(value: date) -> datetime:
    return datetime.combine(value + timedelta(days=1), time.min)


def resolve_period_window(
    *,
    period: ReportPeriod = "all",
    date_from: date | None = None,
    date_to: date | None = None,
) -> tuple[date | None, date | None]:
    if date_from or date_to:
        return date_from, date_to

    today = date.today()
    if period == "day":
        return today, today
    if period == "week":
        start = today - timedelta(days=today.weekday())
        return start, start + timedelta(days=6)
    if period == "month":
        start = today.replace(day=1)
        if start.month == 12:
            next_month = start.replace(year=start.year + 1, month=1, day=1)
        else:
            next_month = start.replace(month=start.month + 1, day=1)
        return start, next_month - timedelta(days=1)
    if period == "year":
        return today.replace(month=1, day=1), today.replace(month=12, day=31)
    return None, None


def _series_bucket_label(value: date | datetime, period: ReportPeriod) -> str:
    current = value.date() if isinstance(value, datetime) else value
    if period == "day":
        return current.strftime("%d/%m/%Y")
    if period == "week":
        week_start = current - timedelta(days=current.weekday())
        week_end = week_start + timedelta(days=6)
        return f"{week_start.strftime('%d/%m')} - {week_end.strftime('%d/%m')}"
    if period == "month":
        return current.strftime("%Y-%m")
    if period == "year":
        return current.strftime("%Y")
    return current.strftime("%Y-%m")


def _build_series(
    rows: Iterable[Any],
    *,
    value_getter,
    date_getter,
    period: ReportPeriod,
) -> list[dict[str, Any]]:
    buckets: dict[str, float] = defaultdict(float)
    for row in rows:
        raw_date = date_getter(row)
        if raw_date is None:
            continue
        buckets[_series_bucket_label(raw_date, period)] += float(value_getter(row))
    return [{"label": label, "value": round(total, 2)} for label, total in sorted(buckets.items(), key=lambda item: item[0])]


def _build_count_series(
    rows: Iterable[Any],
    *,
    date_getter,
    period: ReportPeriod,
) -> list[dict[str, Any]]:
    buckets: Counter[str] = Counter()
    for row in rows:
        raw_date = date_getter(row)
        if raw_date is None:
            continue
        buckets[_series_bucket_label(raw_date, period)] += 1
    return [{"label": label, "value": count} for label, count in sorted(buckets.items(), key=lambda item: item[0])]


def _to_listing_summary(global_total: int, filtered_total: int, breakdown: dict[str, int], *, labels: dict[str, str] | None = None) -> ListingSummaryResponse:
    return ListingSummaryResponse(
        global_total=global_total,
        filtered_total=filtered_total,
        breakdown=[
            ListingSummaryBreakdownItem(
                key=key,
                label=(labels or {}).get(key, key),
                count=value,
            )
            for key, value in breakdown.items()
        ],
    )


def _client_base_stmt(*, search: str | None = None, is_active: bool | None = None):
    stmt = select(Cliente)
    if is_active is not None:
        stmt = stmt.where(Cliente.habilitado.is_(is_active))
    if search:
        term = f"%{search.strip().upper()}%"
        stmt = stmt.where(
            or_(
                func.upper(Cliente.codigo).like(term),
                func.upper(Cliente.nombres).like(term),
                func.upper(Cliente.apellido_paterno).like(term),
                func.upper(func.coalesce(Cliente.apellido_materno, "")).like(term),
                func.upper(func.coalesce(Cliente.ci, "")).like(term),
                func.upper(Cliente.celular).like(term),
                func.upper(func.coalesce(Cliente.ciudad, "")).like(term),
            )
        )
    return stmt


def get_clients_summary(db: Session, *, search: str | None = None, is_active: bool | None = None) -> ListingSummaryResponse:
    filtered = db.execute(_client_base_stmt(search=search, is_active=is_active).order_by(Cliente.id.desc())).scalars().all()
    breakdown = {
        "ACTIVE": sum(1 for item in filtered if item.habilitado),
        "INACTIVE": sum(1 for item in filtered if not item.habilitado),
    }
    global_total = db.execute(select(func.count(Cliente.id))).scalar_one()
    return _to_listing_summary(global_total, len(filtered), breakdown, labels={"ACTIVE": "ACTIVOS", "INACTIVE": "INACTIVOS"})


def get_clients_report(
    db: Session,
    *,
    period: ReportPeriod = "all",
    date_from: date | None = None,
    date_to: date | None = None,
) -> AnalyticsReportResponse:
    start_date, end_date = resolve_period_window(period=period, date_from=date_from, date_to=date_to)
    stmt = select(Cliente)
    if start_date is not None:
        stmt = stmt.where(Cliente.fecha_registro >= _start_of_day(start_date))
    if end_date is not None:
        stmt = stmt.where(Cliente.fecha_registro < _end_of_day_exclusive(end_date))
    clients = db.execute(stmt.order_by(Cliente.fecha_registro.desc())).scalars().all()
    all_clients = db.execute(select(Cliente)).scalars().all()
    order_rows = db.execute(select(Pedido.cliente_id, func.count(Pedido.id)).where(Pedido.estado_general == EstadoPedidoGeneralEnum.ACTIVO, Pedido.habilitado.is_(True)).group_by(Pedido.cliente_id)).all()
    active_orders_by_client = {row[0]: row[1] for row in order_rows}

    by_country: Counter[str] = Counter()
    by_city: Counter[str] = Counter()
    for client in all_clients:
        if client.pais:
            by_country[client.pais] += 1
        if client.ciudad:
            by_city[client.ciudad] += 1

    top_clients = sorted(
        [
            {
                "client_id": client.id,
                "codigo": client.codigo,
                "full_name": client.nombre_completo,
                "active_orders": active_orders_by_client.get(client.id, 0),
                "pais": client.pais,
                "ciudad": client.ciudad,
            }
            for client in all_clients
            if active_orders_by_client.get(client.id, 0) > 0
        ],
        key=lambda item: (-item["active_orders"], item["full_name"]),
    )[:10]

    return AnalyticsReportResponse(
        filters_applied={"period": period, "date_from": start_date, "date_to": end_date},
        kpis=[
            {"key": "CLIENTS_TOTAL", "label": "CLIENTES TOTALES", "value": len(all_clients)},
            {"key": "CLIENTS_ACTIVE", "label": "CLIENTES ACTIVOS", "value": sum(1 for item in all_clients if item.habilitado)},
            {"key": "CLIENTS_INACTIVE", "label": "CLIENTES INACTIVOS", "value": sum(1 for item in all_clients if not item.habilitado)},
            {"key": "CLIENTS_PERIOD", "label": "REGISTROS EN EL PERÍODO", "value": len(clients)},
        ],
        series={"registrations": _build_count_series(clients, date_getter=lambda row: row.fecha_registro, period=period)},
        rankings={"top_active_orders": top_clients},
        table_rows={
            "by_country": [{"label": label, "value": value} for label, value in by_country.most_common(12)],
            "by_city": [{"label": label, "value": value} for label, value in by_city.most_common(12)],
            "top_active_orders": top_clients,
        },
    )


def get_boutique_types_summary(db: Session) -> ListingSummaryResponse:
    rows = db.execute(select(TipoItemBoutique).order_by(TipoItemBoutique.nombre.asc())).scalars().all()
    return _to_listing_summary(
        db.execute(select(func.count(TipoItemBoutique.id))).scalar_one(),
        len(rows),
        {"ACTIVE": sum(1 for row in rows if row.habilitado), "INACTIVE": sum(1 for row in rows if not row.habilitado)},
        labels={"ACTIVE": "ACTIVOS", "INACTIVE": "INACTIVOS"},
    )


def get_boutique_providers_summary(db: Session, *, search: str | None = None, is_active: bool | None = None) -> ListingSummaryResponse:
    stmt = select(Proveedor)
    if is_active is not None:
        stmt = stmt.where(Proveedor.habilitado.is_(is_active))
    if search:
        term = f"%{search.strip().upper()}%"
        stmt = stmt.where(
            or_(
                func.upper(Proveedor.nombres).like(term),
                func.upper(func.coalesce(Proveedor.nombre_comercial, "")).like(term),
                func.upper(func.coalesce(Proveedor.celular, "")).like(term),
                func.upper(func.coalesce(Proveedor.ciudad, "")).like(term),
            )
        )
    rows = db.execute(stmt.order_by(Proveedor.id.desc())).scalars().all()
    return _to_listing_summary(
        db.execute(select(func.count(Proveedor.id))).scalar_one(),
        len(rows),
        {"ACTIVE": sum(1 for row in rows if row.habilitado), "INACTIVE": sum(1 for row in rows if not row.habilitado)},
        labels={"ACTIVE": "ACTIVOS", "INACTIVE": "INACTIVOS"},
    )


def get_boutique_items_summary(
    db: Session,
    *,
    type_id: int | None = None,
    search: str | None = None,
    is_active: bool | None = None,
    low_stock: bool | None = None,
) -> ListingSummaryResponse:
    stmt = select(ItemBoutique).options(joinedload(ItemBoutique.tipo_item))
    if type_id is not None:
        stmt = stmt.where(ItemBoutique.tipo_item_id == type_id)
    if is_active is not None:
        stmt = stmt.where(ItemBoutique.estado.is_(is_active))
    if low_stock:
        stmt = stmt.where(ItemBoutique.stock <= ItemBoutique.stock_minimo)
    if search:
        term = f"%{search.strip().upper()}%"
        stmt = stmt.where(
            or_(
                func.upper(ItemBoutique.codigo).like(term),
                func.upper(ItemBoutique.nombre).like(term),
                func.upper(ItemBoutique.color_primario).like(term),
                func.upper(func.coalesce(ItemBoutique.color_secundario, "")).like(term),
            )
        )
    rows = db.execute(stmt.order_by(ItemBoutique.id.desc())).scalars().all()
    breakdown = {
        "ACTIVE": sum(1 for row in rows if row.estado),
        "INACTIVE": sum(1 for row in rows if not row.estado),
        "LOW_STOCK": sum(1 for row in rows if row.stock <= row.stock_minimo),
    }
    return _to_listing_summary(
        db.execute(select(func.count(ItemBoutique.id))).scalar_one(),
        len(rows),
        breakdown,
        labels={"ACTIVE": "ACTIVOS", "INACTIVE": "INACTIVOS", "LOW_STOCK": "STOCK BAJO"},
    )


def get_boutique_entries_summary(
    db: Session,
    *,
    search: str | None = None,
    item_id: int | None = None,
    is_active: bool | None = None,
) -> ListingSummaryResponse:
    stmt = select(EntradaItemBoutique)
    if item_id is not None:
        stmt = stmt.where(EntradaItemBoutique.item_id == item_id)
    if is_active is not None:
        stmt = stmt.where(EntradaItemBoutique.estado.is_(is_active))
    if search:
        term = f"%{search.strip().upper()}%"
        stmt = stmt.join(EntradaItemBoutique.item).outerjoin(EntradaItemBoutique.proveedor).where(
            or_(
                func.upper(ItemBoutique.codigo).like(term),
                func.upper(ItemBoutique.nombre).like(term),
                func.upper(func.coalesce(Proveedor.nombre_comercial, "")).like(term),
            )
        )
    rows = db.execute(stmt.order_by(EntradaItemBoutique.fecha.desc(), EntradaItemBoutique.id.desc())).scalars().all()
    return _to_listing_summary(
        db.execute(select(func.count(EntradaItemBoutique.id))).scalar_one(),
        len(rows),
        {"ACTIVE": sum(1 for row in rows if row.estado), "INACTIVE": sum(1 for row in rows if not row.estado)},
        labels={"ACTIVE": "ACTIVAS", "INACTIVE": "INACTIVAS"},
    )


def get_boutique_sales_summary(
    db: Session,
    *,
    search: str | None = None,
    item_id: int | None = None,
    client_id: int | None = None,
    payment_method: str | None = None,
    state: EstadoVentaBoutiqueEnum | None = None,
    currency_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> ListingSummaryResponse:
    stmt = select(VentaBoutique)
    if item_id is not None:
        stmt = stmt.where(VentaBoutique.item_id == item_id)
    if client_id is not None:
        stmt = stmt.where(VentaBoutique.cliente_id == client_id)
    if payment_method is not None:
        stmt = stmt.where(VentaBoutique.metodo_pago == payment_method)
    if state is not None:
        stmt = stmt.where(VentaBoutique.estado == state)
    if currency_id is not None:
        stmt = stmt.where(VentaBoutique.moneda_id == currency_id)
    if date_from is not None:
        stmt = stmt.where(VentaBoutique.fecha >= _start_of_day(date_from))
    if date_to is not None:
        stmt = stmt.where(VentaBoutique.fecha < _end_of_day_exclusive(date_to))
    if search:
        term = f"%{search.strip().upper()}%"
        stmt = stmt.join(VentaBoutique.item).outerjoin(VentaBoutique.cliente).where(
            or_(
                func.upper(ItemBoutique.codigo).like(term),
                func.upper(ItemBoutique.nombre).like(term),
                func.upper(func.coalesce(Cliente.codigo, "")).like(term),
                func.upper(func.concat(func.coalesce(Cliente.nombres, ""), " ", func.coalesce(Cliente.apellido_paterno, ""))).like(term),
            )
        )
    rows = db.execute(stmt.order_by(VentaBoutique.fecha.desc())).scalars().all()
    breakdown = {enum.value.upper(): sum(1 for row in rows if row.estado == enum) for enum in EstadoVentaBoutiqueEnum}
    return _to_listing_summary(db.execute(select(func.count(VentaBoutique.id))).scalar_one(), len(rows), breakdown)


def get_boutique_report(
    db: Session,
    *,
    period: ReportPeriod = "all",
    date_from: date | None = None,
    date_to: date | None = None,
) -> AnalyticsReportResponse:
    start_date, end_date = resolve_period_window(period=period, date_from=date_from, date_to=date_to)
    sales_stmt = select(VentaBoutique).options(joinedload(VentaBoutique.item).joinedload(ItemBoutique.tipo_item), joinedload(VentaBoutique.moneda))
    entries_stmt = select(EntradaItemBoutique).options(joinedload(EntradaItemBoutique.item).joinedload(ItemBoutique.tipo_item), joinedload(EntradaItemBoutique.proveedor))
    if start_date is not None:
        sales_stmt = sales_stmt.where(VentaBoutique.fecha >= _start_of_day(start_date))
        entries_stmt = entries_stmt.where(EntradaItemBoutique.fecha >= _start_of_day(start_date))
    if end_date is not None:
        sales_stmt = sales_stmt.where(VentaBoutique.fecha < _end_of_day_exclusive(end_date))
        entries_stmt = entries_stmt.where(EntradaItemBoutique.fecha < _end_of_day_exclusive(end_date))
    sales = db.execute(sales_stmt.order_by(VentaBoutique.fecha.desc())).unique().scalars().all()
    entries = db.execute(entries_stmt.order_by(EntradaItemBoutique.fecha.desc())).unique().scalars().all()
    items = db.execute(select(ItemBoutique).options(joinedload(ItemBoutique.tipo_item), joinedload(ItemBoutique.proveedor_rel))).unique().scalars().all()
    providers = db.execute(select(Proveedor)).scalars().all()
    types = db.execute(select(TipoItemBoutique)).scalars().all()

    sold_items: dict[str, dict[str, Any]] = defaultdict(lambda: {"quantity": 0, "total_bob": 0.0})
    sold_types: dict[str, dict[str, Any]] = defaultdict(lambda: {"quantity": 0, "total_bob": 0.0})
    methods_by_currency: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for sale in sales:
        item_key = f"{sale.item.codigo} - {sale.item.nombre}"
        sold_items[item_key]["quantity"] += sale.cantidad
        sold_items[item_key]["total_bob"] += _to_float(sale.total)
        type_key = sale.item.tipo_item.nombre
        sold_types[type_key]["quantity"] += sale.cantidad
        sold_types[type_key]["total_bob"] += _to_float(sale.total)
        methods_by_currency[sale.moneda.codigo][sale.metodo_pago.value.upper()] += _to_float(sale.total)

    entry_items: dict[str, float] = defaultdict(float)
    entries_by_provider: dict[str, float] = defaultdict(float)
    costs_by_item_provider: dict[tuple[int, str, str], list[float]] = defaultdict(list)
    for entry in entries:
        item_label = f"{entry.item.codigo} - {entry.item.nombre}"
        entry_items[item_label] += _to_float(entry.cantidad)
        provider_label = entry.proveedor.nombre_comercial if entry.proveedor and entry.proveedor.nombre_comercial else entry.proveedor.nombre_completo if entry.proveedor else "SIN PROVEEDOR"
        entries_by_provider[provider_label] += _to_float(entry.cantidad)
        costs_by_item_provider[(entry.item.id, item_label, provider_label)].append(_to_float(entry.costo_unitario))

    category_breakdown = Counter(item.tipo_item.nombre for item in items)
    min_cost_rows: list[dict[str, Any]] = []
    comparison_rows: list[dict[str, Any]] = []
    grouped_costs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for (_, item_label, provider_label), values in costs_by_item_provider.items():
        avg_cost = round(sum(values) / max(len(values), 1), 2)
        min_cost = round(min(values), 2)
        row = {"item": item_label, "provider": provider_label, "avg_cost": avg_cost, "min_cost": min_cost}
        comparison_rows.append(row)
        grouped_costs[item_label].append(row)
    for item_label, rows in grouped_costs.items():
        cheapest = min(rows, key=lambda row: row["min_cost"])
        min_cost_rows.append(cheapest)
    min_cost_rows.sort(key=lambda row: (row["item"], row["min_cost"]))

    sales_status_breakdown = Counter(sale.estado.value.upper() for sale in sales)

    return AnalyticsReportResponse(
        filters_applied={"period": period, "date_from": start_date, "date_to": end_date},
        kpis=[
            {"key": "BOUTIQUE_ITEMS", "label": "PRODUCTOS", "value": len(items)},
            {"key": "BOUTIQUE_TYPES", "label": "CATEGORÍAS", "value": len(types)},
            {"key": "BOUTIQUE_PROVIDERS", "label": "PROVEEDORES", "value": len(providers)},
            {"key": "BOUTIQUE_SALES_COUNT", "label": "VENTAS EN EL PERÍODO", "value": len(sales)},
            {"key": "BOUTIQUE_SALES_TOTAL", "label": "INGRESO EN VENTAS", "value": round(sum(_to_float(sale.total) for sale in sales), 2), "unit": "BOB"},
            {"key": "BOUTIQUE_ENTRIES_COUNT", "label": "ENTRADAS EN EL PERÍODO", "value": len(entries)},
        ],
        series={
            "sales_by_period": _build_series(sales, value_getter=lambda sale: _to_float(sale.total), date_getter=lambda sale: sale.fecha, period=period),
            "entries_by_period": _build_count_series(entries, date_getter=lambda entry: entry.fecha, period=period),
        },
        rankings={
            "sold_items": [
                {"label": label, "quantity": values["quantity"], "total_bob": round(values["total_bob"], 2)}
                for label, values in sorted(sold_items.items(), key=lambda item: (-item[1]["quantity"], item[0]))[:10]
            ],
            "sold_types": [
                {"label": label, "quantity": values["quantity"], "total_bob": round(values["total_bob"], 2)}
                for label, values in sorted(sold_types.items(), key=lambda item: (-item[1]["quantity"], item[0]))[:10]
            ],
            "entries_by_item": [{"label": label, "value": round(value, 2)} for label, value in sorted(entry_items.items(), key=lambda item: (-item[1], item[0]))[:10]],
        },
        table_rows={
            "category_breakdown": [{"label": label, "value": value} for label, value in category_breakdown.most_common()],
            "sales_status_breakdown": [{"label": label, "value": value} for label, value in sales_status_breakdown.most_common()],
            "entries_by_provider": [{"label": label, "value": round(value, 2)} for label, value in sorted(entries_by_provider.items(), key=lambda item: (-item[1], item[0]))[:10]],
            "cheapest_provider_by_item": min_cost_rows[:15],
            "cost_comparison": sorted(comparison_rows, key=lambda row: (row["item"], row["provider"]))[:40],
            "payment_methods_by_currency": [
                {"currency": currency, "method": method, "total_bob": round(total, 2)}
                for currency, methods in sorted(methods_by_currency.items(), key=lambda item: item[0])
                for method, total in sorted(methods.items(), key=lambda item: item[0])
            ],
        },
    )


def get_fletes_summary(db: Session, *, search: str | None = None, state: EstadoFleteEnum | None = None, is_enabled: bool | None = None) -> ListingSummaryResponse:
    stmt = select(FleteVestido).options(joinedload(FleteVestido.item))
    if state is not None:
        stmt = stmt.where(FleteVestido.estado == state)
    if is_enabled is not None:
        stmt = stmt.where(FleteVestido.habilitado.is_(is_enabled))
    if search:
        term = f"%{search.strip().upper()}%"
        stmt = stmt.join(FleteVestido.item).where(
            or_(
                func.upper(ItemBoutique.codigo).like(term),
                func.upper(ItemBoutique.nombre).like(term),
                func.upper(ItemBoutique.color_primario).like(term),
            )
        )
    rows = db.execute(stmt.order_by(FleteVestido.fecha_habilitacion.desc())).scalars().all()
    breakdown = {enum.value.upper(): sum(1 for row in rows if row.estado == enum) for enum in EstadoFleteEnum}
    breakdown["HABILITADOS"] = sum(1 for row in rows if row.habilitado)
    breakdown["INHABILITADOS"] = sum(1 for row in rows if not row.habilitado)
    return _to_listing_summary(db.execute(select(func.count(FleteVestido.id))).scalar_one(), len(rows), breakdown)


def get_flete_outputs_summary(
    db: Session,
    *,
    search: str | None = None,
    flete_id: int | None = None,
    client_id: int | None = None,
    currency_id: int | None = None,
    state: EstadoSalidaFleteEnum | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> ListingSummaryResponse:
    stmt = select(SalidaFlete).options(joinedload(SalidaFlete.flete).joinedload(FleteVestido.item), joinedload(SalidaFlete.cliente))
    if flete_id is not None:
        stmt = stmt.where(SalidaFlete.flete_id == flete_id)
    if client_id is not None:
        stmt = stmt.where(SalidaFlete.cliente_id == client_id)
    if currency_id is not None:
        stmt = stmt.where(SalidaFlete.moneda_id == currency_id)
    if state is not None:
        stmt = stmt.where(SalidaFlete.estado_salida == state)
    if date_from is not None:
        stmt = stmt.where(SalidaFlete.fecha_salida >= date_from)
    if date_to is not None:
        stmt = stmt.where(SalidaFlete.fecha_salida <= date_to)
    if search:
        term = f"%{search.strip().upper()}%"
        stmt = stmt.join(SalidaFlete.flete).join(FleteVestido.item).join(SalidaFlete.cliente).where(
            or_(
                func.upper(ItemBoutique.codigo).like(term),
                func.upper(ItemBoutique.nombre).like(term),
                func.upper(Cliente.codigo).like(term),
                func.upper(Cliente.nombres).like(term),
                func.upper(Cliente.apellido_paterno).like(term),
            )
        )
    rows = db.execute(stmt.order_by(SalidaFlete.fecha_registro.desc())).unique().scalars().all()
    breakdown = {enum.value.upper(): sum(1 for row in rows if row.estado_salida == enum) for enum in EstadoSalidaFleteEnum}
    return _to_listing_summary(db.execute(select(func.count(SalidaFlete.id))).scalar_one(), len(rows), breakdown)


def get_fletes_report(
    db: Session,
    *,
    period: ReportPeriod = "all",
    date_from: date | None = None,
    date_to: date | None = None,
) -> AnalyticsReportResponse:
    start_date, end_date = resolve_period_window(period=period, date_from=date_from, date_to=date_to)
    outputs_stmt = select(SalidaFlete).options(joinedload(SalidaFlete.flete).joinedload(FleteVestido.item), joinedload(SalidaFlete.cliente))
    if start_date is not None:
        outputs_stmt = outputs_stmt.where(SalidaFlete.fecha_salida >= start_date)
    if end_date is not None:
        outputs_stmt = outputs_stmt.where(SalidaFlete.fecha_salida <= end_date)
    outputs = db.execute(outputs_stmt.order_by(SalidaFlete.fecha_salida.desc())).unique().scalars().all()
    fletes = db.execute(select(FleteVestido).options(joinedload(FleteVestido.item))).scalars().all()
    today = date.today()
    critical_returns = []
    for output in outputs:
        if output.estado_salida in {EstadoSalidaFleteEnum.ANULADO, EstadoSalidaFleteEnum.DEVUELTO, EstadoSalidaFleteEnum.DEVUELTO_CON_OBSERVACION, EstadoSalidaFleteEnum.DEVUELTO_CON_ARREGLO}:
            continue
        status = "PROXIMA"
        if output.fecha_devolucion_prevista < today:
            status = "VENCIDA"
        elif output.fecha_devolucion_prevista == today:
            status = "HOY"
        elif output.fecha_devolucion_prevista <= today + timedelta(days=2):
            status = "2_DIAS"
        critical_returns.append(
            {
                "id": output.id,
                "item": f"{output.flete.item.codigo} - {output.flete.item.nombre}",
                "client_name": output.cliente.nombre_completo,
                "fecha_devolucion_prevista": output.fecha_devolucion_prevista.isoformat(),
                "estado_salida": output.estado_salida.value.upper(),
                "criticidad": status,
            }
        )
    critical_returns.sort(key=lambda row: (row["fecha_devolucion_prevista"], row["item"]))

    by_state = Counter(flete.estado.value.upper() for flete in fletes)
    output_states = Counter(output.estado_salida.value.upper() for output in outputs)
    top_fletes = sorted(
        [{"label": f"{flete.item.codigo} - {flete.item.nombre}", "value": flete.salidas_actuales, "state": flete.estado.value.upper()} for flete in fletes],
        key=lambda row: (-row["value"], row["label"]),
    )[:10]

    return AnalyticsReportResponse(
        filters_applied={"period": period, "date_from": start_date, "date_to": end_date},
        kpis=[
            {"key": "FLETES_TOTAL", "label": "VESTIDOS EN FLETE", "value": len(fletes)},
            {"key": "FLETES_AVAILABLE", "label": "DISPONIBLES", "value": sum(1 for flete in fletes if flete.estado == EstadoFleteEnum.DISPONIBLE)},
            {"key": "FLETES_IN_USE", "label": "EN FLETE", "value": sum(1 for flete in fletes if flete.estado == EstadoFleteEnum.EN_FLETE)},
            {"key": "OUTPUTS_PERIOD", "label": "SALIDAS EN EL PERÍODO", "value": len(outputs)},
            {"key": "OUTPUTS_ANNULLED", "label": "SALIDAS ANULADAS", "value": sum(1 for output in outputs if output.estado_salida == EstadoSalidaFleteEnum.ANULADO)},
            {"key": "RETURNS_OVERDUE", "label": "DEVOLUCIONES VENCIDAS", "value": sum(1 for row in critical_returns if row["criticidad"] == "VENCIDA")},
        ],
        series={"outputs_by_period": _build_count_series(outputs, date_getter=lambda row: row.fecha_salida, period=period)},
        rankings={"top_fletes_by_outputs": top_fletes},
        table_rows={
            "state_breakdown": [{"label": label, "value": value} for label, value in by_state.most_common()],
            "output_state_breakdown": [{"label": label, "value": value} for label, value in output_states.most_common()],
            "critical_returns": critical_returns[:20],
            "top_fletes_by_outputs": top_fletes,
        },
    )


def get_workshop_types_summary(db: Session) -> ListingSummaryResponse:
    rows = db.execute(select(TipoInventarioTaller).order_by(TipoInventarioTaller.nombre.asc())).scalars().all()
    return _to_listing_summary(
        db.execute(select(func.count(TipoInventarioTaller.id))).scalar_one(),
        len(rows),
        {"ACTIVE": sum(1 for row in rows if row.habilitado), "INACTIVE": sum(1 for row in rows if not row.habilitado)},
        labels={"ACTIVE": "ACTIVOS", "INACTIVE": "INACTIVOS"},
    )


def get_workshop_inventory_summary(
    db: Session,
    *,
    type_id: int | None = None,
    search: str | None = None,
    is_active: bool | None = None,
    low_stock: bool | None = None,
) -> ListingSummaryResponse:
    stmt = select(InventarioTaller).options(joinedload(InventarioTaller.tipo))
    if type_id is not None:
        stmt = stmt.where(InventarioTaller.tipo_id == type_id)
    if is_active is not None:
        stmt = stmt.where(InventarioTaller.estado.is_(is_active))
    if low_stock:
        stmt = stmt.where(InventarioTaller.stock <= InventarioTaller.stock_minimo)
    if search:
        term = f"%{search.strip().upper()}%"
        stmt = stmt.where(
            or_(
                func.upper(InventarioTaller.codigo).like(term),
                func.upper(InventarioTaller.nombre).like(term),
                func.upper(InventarioTaller.color).like(term),
                func.upper(func.coalesce(InventarioTaller.material, "")).like(term),
            )
        )
    rows = db.execute(stmt.order_by(InventarioTaller.id.desc())).scalars().all()
    return _to_listing_summary(
        db.execute(select(func.count(InventarioTaller.id))).scalar_one(),
        len(rows),
        {
            "ACTIVE": sum(1 for row in rows if row.estado),
            "INACTIVE": sum(1 for row in rows if not row.estado),
            "LOW_STOCK": sum(1 for row in rows if row.stock <= row.stock_minimo),
        },
        labels={"ACTIVE": "ACTIVOS", "INACTIVE": "INACTIVOS", "LOW_STOCK": "STOCK BAJO"},
    )


def get_workshop_entries_summary(db: Session, *, search: str | None = None, item_id: int | None = None, is_active: bool | None = None) -> ListingSummaryResponse:
    stmt = select(EntradaInventarioTaller)
    if item_id is not None:
        stmt = stmt.where(EntradaInventarioTaller.item_id == item_id)
    if is_active is not None:
        stmt = stmt.where(EntradaInventarioTaller.estado.is_(is_active))
    if search:
        term = f"%{search.strip().upper()}%"
        stmt = stmt.join(EntradaInventarioTaller.item).where(
            or_(func.upper(InventarioTaller.codigo).like(term), func.upper(InventarioTaller.nombre).like(term))
        )
    rows = db.execute(stmt.order_by(EntradaInventarioTaller.fecha.desc(), EntradaInventarioTaller.id.desc())).scalars().all()
    return _to_listing_summary(
        db.execute(select(func.count(EntradaInventarioTaller.id))).scalar_one(),
        len(rows),
        {"ACTIVE": sum(1 for row in rows if row.estado), "INACTIVE": sum(1 for row in rows if not row.estado)},
        labels={"ACTIVE": "ACTIVAS", "INACTIVE": "INACTIVAS"},
    )


def get_workshop_outputs_summary(db: Session, *, search: str | None = None, item_id: int | None = None, is_active: bool | None = None) -> ListingSummaryResponse:
    stmt = select(SalidaMaterialTaller)
    if item_id is not None:
        stmt = stmt.where(SalidaMaterialTaller.item_id == item_id)
    if is_active is not None:
        stmt = stmt.where(SalidaMaterialTaller.estado.is_(is_active))
    if search:
        term = f"%{search.strip().upper()}%"
        stmt = stmt.join(SalidaMaterialTaller.item).where(
            or_(
                func.upper(InventarioTaller.codigo).like(term),
                func.upper(InventarioTaller.nombre).like(term),
                func.upper(SalidaMaterialTaller.destino).like(term),
            )
        )
    rows = db.execute(stmt.order_by(SalidaMaterialTaller.fecha.desc(), SalidaMaterialTaller.id.desc())).scalars().all()
    return _to_listing_summary(
        db.execute(select(func.count(SalidaMaterialTaller.id))).scalar_one(),
        len(rows),
        {"ACTIVE": sum(1 for row in rows if row.estado), "INACTIVE": sum(1 for row in rows if not row.estado)},
        labels={"ACTIVE": "ACTIVAS", "INACTIVE": "INACTIVAS"},
    )


def get_workshop_report(
    db: Session,
    *,
    period: ReportPeriod = "all",
    date_from: date | None = None,
    date_to: date | None = None,
) -> AnalyticsReportResponse:
    start_date, end_date = resolve_period_window(period=period, date_from=date_from, date_to=date_to)
    entries_stmt = select(EntradaInventarioTaller).options(joinedload(EntradaInventarioTaller.item).joinedload(InventarioTaller.tipo), joinedload(EntradaInventarioTaller.proveedor))
    outputs_stmt = select(SalidaMaterialTaller).options(joinedload(SalidaMaterialTaller.item).joinedload(InventarioTaller.tipo))
    if start_date is not None:
        entries_stmt = entries_stmt.where(EntradaInventarioTaller.fecha >= _start_of_day(start_date))
        outputs_stmt = outputs_stmt.where(SalidaMaterialTaller.fecha >= _start_of_day(start_date))
    if end_date is not None:
        entries_stmt = entries_stmt.where(EntradaInventarioTaller.fecha < _end_of_day_exclusive(end_date))
        outputs_stmt = outputs_stmt.where(SalidaMaterialTaller.fecha < _end_of_day_exclusive(end_date))
    entries = db.execute(entries_stmt.order_by(EntradaInventarioTaller.fecha.desc())).unique().scalars().all()
    outputs = db.execute(outputs_stmt.order_by(SalidaMaterialTaller.fecha.desc())).unique().scalars().all()
    inventory = db.execute(select(InventarioTaller).options(joinedload(InventarioTaller.tipo), joinedload(InventarioTaller.proveedor))).unique().scalars().all()
    types = db.execute(select(TipoInventarioTaller)).scalars().all()

    type_breakdown = Counter(item.tipo.nombre for item in inventory)
    top_outputs: dict[str, float] = defaultdict(float)
    top_entries: dict[str, float] = defaultdict(float)
    destinations: dict[str, float] = defaultdict(float)
    entries_by_provider: dict[str, float] = defaultdict(float)
    cost_matrix: list[dict[str, Any]] = []
    cheapest_by_item: dict[str, dict[str, Any]] = {}

    for output in outputs:
        item_label = f"{output.item.codigo} - {output.item.nombre}"
        top_outputs[item_label] += _to_float(output.cantidad)
        destinations[output.destino] += _to_float(output.cantidad)
    for entry in entries:
        item_label = f"{entry.item.codigo} - {entry.item.nombre}"
        top_entries[item_label] += _to_float(entry.cantidad)
        provider_label = entry.proveedor.nombre_comercial if entry.proveedor and entry.proveedor.nombre_comercial else entry.proveedor.nombre_completo if entry.proveedor else "SIN PROVEEDOR"
        entries_by_provider[provider_label] += _to_float(entry.cantidad)
        row = {
            "item": item_label,
            "provider": provider_label,
            "unit_cost": round(_to_float(entry.costo_unitario), 2),
            "quantity": round(_to_float(entry.cantidad), 2),
        }
        cost_matrix.append(row)
        current = cheapest_by_item.get(item_label)
        if current is None or row["unit_cost"] < current["unit_cost"]:
            cheapest_by_item[item_label] = row

    return AnalyticsReportResponse(
        filters_applied={"period": period, "date_from": start_date, "date_to": end_date},
        kpis=[
            {"key": "WORKSHOP_ITEMS", "label": "MATERIALES", "value": len(inventory)},
            {"key": "WORKSHOP_TYPES", "label": "TIPOS DE TALLER", "value": len(types)},
            {"key": "WORKSHOP_LOW_STOCK", "label": "STOCK BAJO", "value": sum(1 for item in inventory if item.stock <= item.stock_minimo)},
            {"key": "WORKSHOP_ENTRIES", "label": "ENTRADAS EN EL PERÍODO", "value": len(entries)},
            {"key": "WORKSHOP_OUTPUTS", "label": "SALIDAS EN EL PERÍODO", "value": len(outputs)},
        ],
        series={
            "entries_by_period": _build_count_series(entries, date_getter=lambda row: row.fecha, period=period),
            "outputs_by_period": _build_count_series(outputs, date_getter=lambda row: row.fecha, period=period),
        },
        rankings={
            "top_outputs": [{"label": label, "value": round(value, 2)} for label, value in sorted(top_outputs.items(), key=lambda item: (-item[1], item[0]))[:10]],
            "top_entries": [{"label": label, "value": round(value, 2)} for label, value in sorted(top_entries.items(), key=lambda item: (-item[1], item[0]))[:10]],
        },
        table_rows={
            "type_breakdown": [{"label": label, "value": value} for label, value in type_breakdown.most_common()],
            "destinations": [{"label": label, "value": round(value, 2)} for label, value in sorted(destinations.items(), key=lambda item: (-item[1], item[0]))[:12]],
            "entries_by_provider": [{"label": label, "value": round(value, 2)} for label, value in sorted(entries_by_provider.items(), key=lambda item: (-item[1], item[0]))[:12]],
            "cheapest_by_item": sorted(cheapest_by_item.values(), key=lambda row: (row["item"], row["unit_cost"]))[:20],
            "cost_matrix": sorted(cost_matrix, key=lambda row: (row["item"], row["provider"]))[:40],
        },
    )


def get_currencies_summary(db: Session, *, search: str | None = None, is_active: bool | None = None) -> ListingSummaryResponse:
    stmt = select(Moneda)
    if is_active is not None:
        stmt = stmt.where(Moneda.habilitado.is_(is_active))
    if search:
        term = f"%{search.strip().upper()}%"
        stmt = stmt.where(or_(func.upper(Moneda.codigo).like(term), func.upper(Moneda.nombre).like(term)))
    rows = db.execute(stmt.order_by(Moneda.es_base.desc(), Moneda.codigo.asc())).scalars().all()
    return _to_listing_summary(
        db.execute(select(func.count(Moneda.id))).scalar_one(),
        len(rows),
        {
            "ACTIVE": sum(1 for row in rows if row.habilitado),
            "INACTIVE": sum(1 for row in rows if not row.habilitado),
            "BASE": sum(1 for row in rows if row.es_base),
        },
        labels={"ACTIVE": "ACTIVAS", "INACTIVE": "INACTIVAS", "BASE": "BASE"},
    )


def get_exchange_rates_summary(db: Session, *, moneda_id: int | None = None, is_active: bool | None = None) -> ListingSummaryResponse:
    stmt = select(TipoCambioMoneda)
    if moneda_id is not None:
        stmt = stmt.where(TipoCambioMoneda.moneda_id == moneda_id)
    if is_active is not None:
        stmt = stmt.where(TipoCambioMoneda.activo.is_(is_active))
    rows = db.execute(stmt.order_by(TipoCambioMoneda.fecha_registro.desc())).scalars().all()
    return _to_listing_summary(
        db.execute(select(func.count(TipoCambioMoneda.id))).scalar_one(),
        len(rows),
        {"ACTIVE": sum(1 for row in rows if row.activo), "INACTIVE": sum(1 for row in rows if not row.activo)},
        labels={"ACTIVE": "ACTIVOS", "INACTIVE": "INACTIVOS"},
    )


def get_currencies_report(
    db: Session,
    *,
    period: ReportPeriod = "all",
    date_from: date | None = None,
    date_to: date | None = None,
    currency_id: int | None = None,
) -> AnalyticsReportResponse:
    start_date, end_date = resolve_period_window(period=period, date_from=date_from, date_to=date_to)
    currencies = db.execute(select(Moneda).order_by(Moneda.es_base.desc(), Moneda.codigo.asc())).scalars().all()
    rates_stmt = select(TipoCambioMoneda).options(joinedload(TipoCambioMoneda.moneda), joinedload(TipoCambioMoneda.usuario))
    if currency_id is not None:
        rates_stmt = rates_stmt.where(TipoCambioMoneda.moneda_id == currency_id)
    if start_date is not None:
        rates_stmt = rates_stmt.where(TipoCambioMoneda.fecha_registro >= _start_of_day(start_date))
    if end_date is not None:
        rates_stmt = rates_stmt.where(TipoCambioMoneda.fecha_registro < _end_of_day_exclusive(end_date))
    rates = db.execute(rates_stmt.order_by(TipoCambioMoneda.fecha_registro.asc())).scalars().all()

    sales_stmt = select(VentaBoutique).options(joinedload(VentaBoutique.moneda))
    payments_stmt = select(PagoPedido).options(joinedload(PagoPedido.moneda)).where(PagoPedido.estado == EstadoPagoPedidoEnum.REGISTRADO)
    flete_stmt = select(SalidaFlete).options(joinedload(SalidaFlete.moneda))
    if start_date is not None:
        sales_stmt = sales_stmt.where(VentaBoutique.fecha >= _start_of_day(start_date))
        payments_stmt = payments_stmt.where(PagoPedido.fecha >= _start_of_day(start_date))
        flete_stmt = flete_stmt.where(SalidaFlete.fecha_registro >= _start_of_day(start_date))
    if end_date is not None:
        sales_stmt = sales_stmt.where(VentaBoutique.fecha < _end_of_day_exclusive(end_date))
        payments_stmt = payments_stmt.where(PagoPedido.fecha < _end_of_day_exclusive(end_date))
        flete_stmt = flete_stmt.where(SalidaFlete.fecha_registro < _end_of_day_exclusive(end_date))
    sales = db.execute(sales_stmt).scalars().all()
    payments = db.execute(payments_stmt).scalars().all()
    fletes = db.execute(flete_stmt).scalars().all()

    usage_by_currency: dict[str, float] = defaultdict(float)
    methods_by_currency: dict[tuple[str, str], float] = defaultdict(float)
    for sale in sales:
        usage_by_currency[sale.moneda.codigo] += _to_float(sale.total)
        methods_by_currency[(sale.moneda.codigo, sale.metodo_pago.value.upper())] += _to_float(sale.total)
    for payment in payments:
        usage_by_currency[payment.moneda.codigo] += _to_float(payment.monto_bob)
        methods_by_currency[(payment.moneda.codigo, payment.metodo_pago.value.upper())] += _to_float(payment.monto_bob)
    for output in fletes:
        usage_by_currency[output.moneda.codigo] += _to_float(output.total_flete)
        methods_by_currency[(output.moneda.codigo, output.metodo_pago.value.upper())] += _to_float(output.total_flete)

    selected_currency = None
    if currency_id is not None:
        selected_currency = next((currency for currency in currencies if currency.id == currency_id), None)
    if selected_currency is None and currencies:
        selected_currency = next((currency for currency in currencies if not currency.es_base), currencies[0])

    selected_series = [
        {
            "label": rate.fecha_registro.strftime("%Y-%m-%d"),
            "value": round(_to_float(rate.valor_bob), 4),
            "currency_code": rate.moneda.codigo,
        }
        for rate in rates
        if selected_currency is None or rate.moneda_id == selected_currency.id
    ]

    latest_rates = []
    for currency in currencies:
        rate = db.execute(
            select(TipoCambioMoneda)
            .where(TipoCambioMoneda.moneda_id == currency.id)
            .order_by(TipoCambioMoneda.fecha_registro.desc())
        ).scalar_one_or_none()
        if rate is not None:
            latest_rates.append(
                {
                    "currency": currency.codigo,
                    "name": currency.nombre,
                    "value_bob": round(_to_float(rate.valor_bob), 4),
                    "active": rate.activo,
                    "registered_at": rate.fecha_registro.isoformat(),
                }
            )

    return AnalyticsReportResponse(
        filters_applied={
            "period": period,
            "date_from": start_date,
            "date_to": end_date,
            "currency_id": selected_currency.id if selected_currency else None,
            "currency_code": selected_currency.codigo if selected_currency else None,
        },
        kpis=[
            {"key": "CURRENCIES_TOTAL", "label": "MONEDAS", "value": len(currencies)},
            {"key": "CURRENCIES_ACTIVE", "label": "MONEDAS ACTIVAS", "value": sum(1 for currency in currencies if currency.habilitado)},
            {"key": "CURRENCIES_BASE", "label": "MONEDA BASE", "value": next((currency.codigo for currency in currencies if currency.es_base), "SIN BASE")},
            {"key": "RATES_PERIOD", "label": "TIPOS DE CAMBIO EN EL PERÍODO", "value": len(rates)},
        ],
        series={"exchange_rate_series": selected_series},
        rankings={"commercial_usage": [{"label": label, "value": round(value, 2)} for label, value in sorted(usage_by_currency.items(), key=lambda item: (-item[1], item[0]))]},
        table_rows={
            "currencies_breakdown": [{"label": currency.codigo, "active": currency.habilitado, "base": currency.es_base} for currency in currencies],
            "latest_rates": latest_rates,
            "methods_by_currency": [
                {"currency": currency, "method": method, "total_bob": round(total, 2)}
                for (currency, method), total in sorted(methods_by_currency.items(), key=lambda item: (item[0][0], item[0][1]))
            ],
            "commercial_usage": [{"label": label, "value": round(value, 2)} for label, value in sorted(usage_by_currency.items(), key=lambda item: (-item[1], item[0]))],
        },
    )
