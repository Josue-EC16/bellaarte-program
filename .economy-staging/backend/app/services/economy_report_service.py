from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import String, cast, func, literal, select, union_all
from app.models.account import Cuenta
from app.models.user import Usuario
from app.models.boutique_enums import EstadoCorteCajaEnum, EstadoEgresoEnum, TipoEgresoEnum
from app.models.economy import CorteCaja, Egreso, MovimientoEconomico
from app.schemas.economy import (CashFlowReportResponse,CashierReportResponse,IncomeStatementReportResponse,
    MyHistoryReportResponse,MyIncomeStatementResponse,MyPeriodReportResponse,NamedAmountBucket,TimeSeriesBucket,UserMiniSummary)
from app.services.cash_cut_service import (_to_cut_list_item,_to_expense_list_item,_to_user_summary,
    get_my_cut_history,_build_cut_metrics,_get_active_cut_for_cajero,_expense_net)
from app.services.income_service import collect_income_rows_for_period
from app.services.economy_query_service import income_scope,apply_dates


def _is_admin(account):
    return account.rol.codigo == "ADMIN"


def _to_float(value):
    return float(value or 0)


def _active_cut_for_cajero(db,*,cajero_id):
    return _get_active_cut_for_cajero(db,cajero_id=cajero_id)


def _collect_registered_expenses(db,**filters):
    stmt=select(Egreso).where(Egreso.estado==EstadoEgresoEnum.REGISTRADO)
    for key,column in (("user_id",Egreso.usuario_id),("cut_id",Egreso.corte_id),("expense_type",Egreso.tipo)):
        value=filters.pop(key,None)
        if value is not None:
            stmt=stmt.where(column==value)
    return db.execute(apply_dates(stmt,Egreso.fecha,**filters).order_by(Egreso.fecha.desc(),Egreso.id.desc())).scalars().all()


def _named_buckets_from_pairs(pairs):
    return [NamedAmountBucket(label=key,total_bob=value) for key,value in sorted(pairs.items())]


def expense_events(*,user_id=None,date_from=None,date_to=None):
    original=select(Egreso.fecha.label("fecha"),cast(Egreso.tipo,String).label("tipo"),Egreso.monto.label("amount")).where(Egreso.estado=="registrado")
    adjustment=select(MovimientoEconomico.fecha.label("fecha"),cast(Egreso.tipo,String).label("tipo"),(-MovimientoEconomico.monto_bob).label("amount"))\
        .join(Egreso,MovimientoEconomico.egreso_id==Egreso.id).where(MovimientoEconomico.evento=="ajuste_egreso",Egreso.estado=="registrado")
    if user_id is not None:
        original=original.where(Egreso.usuario_id==user_id)
        adjustment=adjustment.where(MovimientoEconomico.actor_id==user_id)
    original=apply_dates(original,Egreso.fecha,date_from=date_from,date_to=date_to)
    adjustment=apply_dates(adjustment,MovimientoEconomico.fecha,date_from=date_from,date_to=date_to)
    return union_all(original,adjustment).subquery("expense_events")


def _income_group(db,scope,column):
    return [NamedAmountBucket(label=str(label),total_bob=amount) for label,amount in
        db.execute(select(column,func.sum(scope.c.monto_bob)).group_by(column).order_by(column))]


def _economic_summary(db,*,account,date_from=None,date_to=None,cashier_id=None,source_type=None,currency_id=None,payment_method=None):
    if not _is_admin(account):
        raise HTTPException(403,"Solo el ADMIN puede consultar reportes globales.")
    scope=income_scope(user_id=cashier_id,source_type=source_type,currency_id=currency_id,
        payment_method=payment_method,date_from=date_from,date_to=date_to)
    expense=expense_events(user_id=cashier_id,date_from=date_from,date_to=date_to)
    gross=db.scalar(select(func.coalesce(func.sum(scope.c.monto_bob),0)))
    spent=db.scalar(select(func.coalesce(func.sum(expense.c.amount),0)))
    comparable=not any((source_type,currency_id,payment_method))
    note=None if comparable else "No comparable: el filtro limita ingresos y los egresos no tienen imputación equivalente. Se muestran egresos del período como referencia."
    by_type=[NamedAmountBucket(label=kind.upper(),total_bob=amount) for kind,amount in
        db.execute(select(expense.c.tipo,func.sum(expense.c.amount)).group_by(expense.c.tipo).order_by(expense.c.tipo))]
    income_month=func.to_char(func.timezone("America/La_Paz",scope.c.fecha),"YYYY-MM")
    expense_month=func.to_char(func.timezone("America/La_Paz",expense.c.fecha),"YYYY-MM")
    incomes={row.period:row for row in db.execute(select(income_month.label("period"),func.sum(scope.c.monto_bob).label("gross"),
        *[func.coalesce(func.sum(scope.c.monto_bob).filter(scope.c.metodo_pago==method),0).label(method)
          for method in ("efectivo","qr","transaccion","tarjeta","ticket_o_vale")]).group_by(income_month))}
    expenses=dict(db.execute(select(expense_month,func.sum(expense.c.amount)).group_by(expense_month)).all())
    series=[]
    for period in sorted(set(incomes)|set(expenses)):
        income=incomes.get(period)
        amount=income.gross if income else Decimal(0)
        out=expenses.get(period,Decimal(0))
        methods={key:getattr(income,key) if income else 0 for key in ("efectivo","qr","transaccion","tarjeta","ticket_o_vale")}
        series.append(TimeSeriesBucket(period=period,ingresos_total_bob=amount,egresos_total_bob=out,
            resultado_bob=amount-out if comparable else None,**methods))
    return dict(scope=scope,gross=gross,spent=spent,comparable=comparable,note=note,by_type=by_type,series=series)


def get_income_statement_report(db,**filters):
    data=_economic_summary(db,**filters)
    return IncomeStatementReportResponse(ingresos_total_bob=data["gross"],egresos_total_bob=data["spent"],
        resultado_bob=data["gross"]-data["spent"] if data["comparable"] else None,
        comparable=data["comparable"],comparison_note=data["note"],
        ingresos_por_fuente=_income_group(db,data["scope"],data["scope"].c.source_type),
        egresos_por_tipo=data["by_type"],serie_mensual=data["series"])


def get_cash_flow_report(db,**filters):
    data=_economic_summary(db,**filters)
    scope=data["scope"]
    return CashFlowReportResponse(entradas_total_bob=data["gross"],egresos_total_bob=data["spent"],
        flujo_neto_bob=data["gross"]-data["spent"] if data["comparable"] else None,
        comparable=data["comparable"],comparison_note=data["note"],
        entradas_por_metodo=_income_group(db,scope,scope.c.metodo_pago),
        entradas_por_fuente=_income_group(db,scope,scope.c.source_type),
        entradas_por_moneda=[NamedAmountBucket(label=code,total_bob=amount,amount_origin=original,currency_code=code,symbol=symbol)
            for code,symbol,amount,original in db.execute(select(scope.c.moneda,scope.c.simbolo_moneda,
                func.sum(scope.c.monto_bob),func.sum(scope.c.monto_moneda_origen)).group_by(scope.c.moneda,scope.c.simbolo_moneda).order_by(scope.c.moneda))],
        serie_periodica=data["series"])


def get_cashier_report(db,*,account,cashier_user_id,date_from=None,date_to=None):
    if not _is_admin(account):
        raise HTTPException(403,"Solo el ADMIN puede consultar reportes por cajero.")
    user=db.get(Usuario,cashier_user_id)
    if user is None:
        raise HTTPException(404,"No se encontró el usuario del historial.")
    stmt=apply_dates(select(CorteCaja).where(CorteCaja.cajero_id==cashier_user_id),CorteCaja.fecha_apertura,date_from=date_from,date_to=date_to)
    cuts=db.scalars(stmt.order_by(CorteCaja.fecha_apertura.desc(),CorteCaja.id.desc())).all()
    items=[_to_cut_list_item(db,cut=cut) for cut in cuts]
    return CashierReportResponse(cajero=_to_user_summary(user),cortes=items,comparativo_periodos=[TimeSeriesBucket(
        period=f"CORTE #{item.id}",ingresos_total_bob=item.ingresos_total_bob,egresos_total_bob=item.egresos_total_bob,
        resultado_bob=item.resultado_bob) for item in reversed(items)])


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
    income_rows,expenses,ingresos_total,egresos_total,resultado = _build_cut_metrics(db,cut=cut)
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
        by_type[expense.tipo.value.upper()] += _expense_net(expense)
    return MyPeriodReportResponse(
        has_active_cut=True,
        cut=_to_cut_list_item(db, cut=cut),
        ingresos_total_bob=ingresos_total,
        egresos_total_bob=egresos_total,
        resultado_bob=resultado,
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
        resultado_bob=round(period.ingresos_total_bob-period.egresos_total_bob,2),
    )


def get_my_history_report(
    db: Session,
    *,
    account: Cuenta,
) -> MyHistoryReportResponse:
    return MyHistoryReportResponse(cuts=get_my_cut_history(db, account=account))
