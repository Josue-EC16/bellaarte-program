from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.account import Cuenta
from app.models.boutique_enums import EstadoCorteCajaEnum, EstadoEgresoEnum, TipoEgresoEnum
from app.models.economy import CorteCaja, Egreso
from app.schemas.economy import (
    CashFlowReportResponse,
    CashCutListItem,
    CashierReportResponse,
    ExpenseListItem,
    IncomeStatementReportResponse,
    MyHistoryReportResponse,
    MyIncomeStatementResponse,
    MyPeriodReportResponse,
    NamedAmountBucket,
    TimeSeriesBucket,
    UserMiniSummary,
)
from app.services.cash_cut_service import _to_cut_list_item, _to_expense_list_item, _to_user_summary, get_my_cut_history
from app.services.income_service import collect_income_rows_for_period


def _is_admin(account: Cuenta) -> bool:
    return account.rol.codigo == "ADMIN"


def _to_float(value: Decimal | float | int | None) -> float:
    if value is None:
        return 0.0
    return float(value)


def _active_cut_for_cajero(db: Session, *, cajero_id: int) -> CorteCaja | None:
    return db.execute(
        select(CorteCaja).where(CorteCaja.cajero_id == cajero_id, CorteCaja.estado == EstadoCorteCajaEnum.ABIERTO)
    ).scalar_one_or_none()


def _collect_registered_expenses(
    db: Session,
    *,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    user_id: int | None = None,
    cut_id: int | None = None,
    expense_type: TipoEgresoEnum | None = None,
    date_from=None,
    date_to=None,
) -> list[Egreso]:
    stmt = select(Egreso).where(Egreso.estado == EstadoEgresoEnum.REGISTRADO).order_by(Egreso.fecha.desc(), Egreso.id.desc())
    if user_id is not None:
        stmt = stmt.where(Egreso.usuario_id == user_id)
    if cut_id is not None:
        stmt = stmt.where(Egreso.corte_id == cut_id)
    if expense_type is not None:
        stmt = stmt.where(Egreso.tipo == expense_type)
    if start_at is not None:
        stmt = stmt.where(Egreso.fecha >= start_at)
    if end_at is not None:
        stmt = stmt.where(Egreso.fecha <= end_at)
    if date_from is not None:
        stmt = stmt.where(func.date(Egreso.fecha) >= date_from)
    if date_to is not None:
        stmt = stmt.where(func.date(Egreso.fecha) <= date_to)
    return db.execute(stmt).scalars().all()


def _named_buckets_from_pairs(pairs: dict[str, float]) -> list[NamedAmountBucket]:
    return [
        NamedAmountBucket(label=label, total_bob=round(total, 2))
        for label, total in sorted(pairs.items(), key=lambda item: item[0])
    ]


def _build_month_series(income_rows, expenses) -> list[TimeSeriesBucket]:
    buckets: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "ingresos_total_bob": 0.0,
            "egresos_total_bob": 0.0,
            "efectivo": 0.0,
            "qr": 0.0,
            "transaccion": 0.0,
            "tarjeta": 0.0,
            "ticket_o_vale": 0.0,
        }
    )
    for item in income_rows:
        period = item.fecha.strftime("%Y-%m")
        bucket = buckets[period]
        bucket["ingresos_total_bob"] += item.monto_bob
        method_key = (item.metodo_pago or "").lower()
        if method_key in bucket:
            bucket[method_key] += item.monto_bob
    for expense in expenses:
        period = expense.fecha.strftime("%Y-%m")
        buckets[period]["egresos_total_bob"] += _to_float(expense.monto)
    series = []
    for period in sorted(buckets):
        bucket = buckets[period]
        ingresos = round(bucket["ingresos_total_bob"], 2)
        egresos = round(bucket["egresos_total_bob"], 2)
        series.append(
            TimeSeriesBucket(
                period=period,
                ingresos_total_bob=ingresos,
                egresos_total_bob=egresos,
                resultado_bob=round(ingresos - egresos, 2),
                efectivo=round(bucket["efectivo"], 2),
                qr=round(bucket["qr"], 2),
                transaccion=round(bucket["transaccion"], 2),
                tarjeta=round(bucket["tarjeta"], 2),
                ticket_o_vale=round(bucket["ticket_o_vale"], 2),
            )
        )
    return series


def get_income_statement_report(
    db: Session,
    *,
    account: Cuenta,
    date_from=None,
    date_to=None,
    cashier_id: int | None = None,
    source_type=None,
    currency_id: int | None = None,
    payment_method: str | None = None,
) -> IncomeStatementReportResponse:
    if not _is_admin(account):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el ADMIN puede ver este reporte.")
    income_rows = collect_income_rows_for_period(
        db,
        user_id=cashier_id,
        source_type=source_type,
        currency_id=currency_id,
        payment_method=payment_method,
        date_from=date_from,
        date_to=date_to,
    )
    expenses = _collect_registered_expenses(db, user_id=cashier_id, date_from=date_from, date_to=date_to)
    income_by_source: dict[str, float] = defaultdict(float)
    for row in income_rows:
        income_by_source[row.source_type] += row.monto_bob
    expense_by_type: dict[str, float] = defaultdict(float)
    for expense in expenses:
        expense_by_type[expense.tipo.value.upper()] += _to_float(expense.monto)
    ingresos_total = round(sum(row.monto_bob for row in income_rows), 2)
    egresos_total = round(sum(_to_float(expense.monto) for expense in expenses), 2)
    return IncomeStatementReportResponse(
        ingresos_total_bob=ingresos_total,
        egresos_total_bob=egresos_total,
        resultado_bob=round(ingresos_total - egresos_total, 2),
        ingresos_por_fuente=_named_buckets_from_pairs(dict(income_by_source)),
        egresos_por_tipo=_named_buckets_from_pairs(dict(expense_by_type)),
        serie_mensual=_build_month_series(income_rows, expenses),
    )


def get_cash_flow_report(
    db: Session,
    *,
    account: Cuenta,
    date_from=None,
    date_to=None,
    cashier_id: int | None = None,
    source_type=None,
    currency_id: int | None = None,
    payment_method: str | None = None,
) -> CashFlowReportResponse:
    if not _is_admin(account):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el ADMIN puede ver este reporte.")
    income_rows = collect_income_rows_for_period(
        db,
        user_id=cashier_id,
        source_type=source_type,
        currency_id=currency_id,
        payment_method=payment_method,
        date_from=date_from,
        date_to=date_to,
    )
    expenses = _collect_registered_expenses(db, user_id=cashier_id, date_from=date_from, date_to=date_to)
    by_method: dict[str, float] = defaultdict(float)
    by_source: dict[str, float] = defaultdict(float)
    by_currency: dict[str, float] = defaultdict(float)
    currency_meta: dict[str, tuple[str | None, str | None]] = {}
    for row in income_rows:
        by_method[row.metodo_pago or "SIN METODO"] += row.monto_bob
        by_source[row.source_type] += row.monto_bob
        currency_label = row.moneda or "SIN MONEDA"
        by_currency[currency_label] += row.monto_bob
        currency_meta[currency_label] = (row.moneda, row.simbolo_moneda)
    entradas_total = round(sum(row.monto_bob for row in income_rows), 2)
    egresos_total = round(sum(_to_float(expense.monto) for expense in expenses), 2)
    return CashFlowReportResponse(
        entradas_total_bob=entradas_total,
        egresos_total_bob=egresos_total,
        flujo_neto_bob=round(entradas_total - egresos_total, 2),
        entradas_por_metodo=_named_buckets_from_pairs(dict(by_method)),
        entradas_por_fuente=_named_buckets_from_pairs(dict(by_source)),
        entradas_por_moneda=[
            NamedAmountBucket(
                label=label,
                total_bob=round(total, 2),
                currency_code=currency_meta[label][0],
                symbol=currency_meta[label][1],
            )
            for label, total in sorted(by_currency.items(), key=lambda item: item[0])
        ],
        serie_periodica=_build_month_series(income_rows, expenses),
    )


def get_cashier_report(
    db: Session,
    *,
    account: Cuenta,
    cashier_user_id: int,
) -> CashierReportResponse:
    if not _is_admin(account):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el ADMIN puede ver reportes por cajero.")
    cashier = db.execute(select(Cuenta).where(Cuenta.usuario_id == cashier_user_id)).scalar_one_or_none()
    if cashier is None or cashier.rol.codigo != "CAJA":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se encontró un cajero válido para el reporte.")
    cuts = db.execute(
        select(CorteCaja)
        .where(CorteCaja.cajero_id == cashier_user_id)
        .order_by(CorteCaja.fecha_apertura.desc(), CorteCaja.id.desc())
    ).scalars().all()
    cut_items = [_to_cut_list_item(db, cut=cut) for cut in cuts]
    comparison = [
        TimeSeriesBucket(
            period=f"CORTE #{cut.id}",
            ingresos_total_bob=cut.ingresos_total_bob,
            egresos_total_bob=cut.egresos_total_bob,
            resultado_bob=cut.resultado_bob,
        )
        for cut in reversed(cut_items)
    ]
    return CashierReportResponse(
        cajero=UserMiniSummary(
            id=cashier.usuario.id,
            full_name=cashier.usuario.nombre_completo,
            username=cashier.username,
        ),
        cortes=cut_items,
        comparativo_periodos=comparison,
    )


def get_my_period_report(
    db: Session,
    *,
    account: Cuenta,
) -> MyPeriodReportResponse:
    cut = _active_cut_for_cajero(db, cajero_id=account.usuario_id)
    if cut is None:
        return MyPeriodReportResponse(
            has_active_cut=False,
            message="NO TIENES UN CORTE ACTIVO.",
        )
    income_rows = collect_income_rows_for_period(
        db,
        start_at=cut.fecha_apertura,
        end_at=cut.fecha_cierre,
        user_id=account.usuario_id,
    )
    expenses = _collect_registered_expenses(db, cut_id=cut.id)
    by_source: dict[str, float] = defaultdict(float)
    by_method: dict[str, float] = defaultdict(float)
    by_currency: dict[str, float] = defaultdict(float)
    currency_meta: dict[str, tuple[str | None, str | None]] = {}
    for row in income_rows:
        by_source[row.source_type] += row.monto_bob
        by_method[row.metodo_pago or "SIN METODO"] += row.monto_bob
        label = row.moneda or "SIN MONEDA"
        by_currency[label] += row.monto_bob
        currency_meta[label] = (row.moneda, row.simbolo_moneda)
    by_type: dict[str, float] = defaultdict(float)
    for expense in expenses:
        by_type[expense.tipo.value.upper()] += _to_float(expense.monto)
    ingresos_total = round(sum(item.monto_bob for item in income_rows), 2)
    egresos_total = round(sum(_to_float(expense.monto) for expense in expenses), 2)
    return MyPeriodReportResponse(
        has_active_cut=True,
        cut=_to_cut_list_item(db, cut=cut),
        ingresos_total_bob=ingresos_total,
        egresos_total_bob=egresos_total,
        resultado_bob=round(ingresos_total + _to_float(cut.fondo_asignado) - egresos_total, 2),
        ingresos_por_fuente=_named_buckets_from_pairs(dict(by_source)),
        ingresos_por_metodo_pago=_named_buckets_from_pairs(dict(by_method)),
        ingresos_por_moneda=[
            NamedAmountBucket(
                label=label,
                total_bob=round(total, 2),
                currency_code=currency_meta[label][0],
                symbol=currency_meta[label][1],
            )
            for label, total in sorted(by_currency.items(), key=lambda item: item[0])
        ],
        egresos_por_tipo=_named_buckets_from_pairs(dict(by_type)),
        egresos=[_to_expense_list_item(expense) for expense in expenses],
    )


def get_my_income_statement(
    db: Session,
    *,
    account: Cuenta,
) -> MyIncomeStatementResponse:
    period = get_my_period_report(db, account=account)
    if not period.has_active_cut:
        return MyIncomeStatementResponse(
            has_active_cut=False,
            message=period.message,
        )
    return MyIncomeStatementResponse(
        has_active_cut=True,
        ingresos_total_bob=period.ingresos_total_bob,
        egresos_total_bob=period.egresos_total_bob,
        resultado_bob=period.resultado_bob,
    )


def get_my_history_report(
    db: Session,
    *,
    account: Cuenta,
) -> MyHistoryReportResponse:
    return MyHistoryReportResponse(cuts=get_my_cut_history(db, account=account))
