import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps.auth import get_enforcer, require_permission
from app.models.account import Cuenta
from app.models.boutique_enums import EstadoCorteCajaEnum, EstadoEgresoEnum, TipoEgresoEnum
from app.schemas.economy import (
    CashCutCloseRequest,
    CashCutCreateRequest,
    CashCutDetailResponse,
    CashCutListItem,
    CashCutOwnActiveResponse,
    CashCutOwnHistoryItem,
    ExpenseAnnulRequest,
    ExpenseCreateRequest,
    ExpenseDetailResponse,
    ExpenseListItem,
    IncomeListItem,
    IncomeStatementReportResponse,
    MyHistoryReportResponse,
    MyIncomeStatementResponse,
    MyPeriodReportResponse,
    RefundContextResponse,
    RefundFlowRequest,
    RefundFlowResponse,
)
from app.services.cash_cut_service import close_cash_cut, get_cash_cut_detail, get_my_active_cut, get_my_cut_history, list_cash_cuts, open_cash_cut
from app.services.economy_report_service import (
    CashFlowReportResponse,
    CashierReportResponse,
    get_cash_flow_report,
    get_cashier_report,
    get_income_statement_report,
    get_my_history_report,
    get_my_income_statement,
    get_my_period_report,
)
from app.services.expense_service import annul_expense, create_expense, get_expense_detail, list_expenses
from app.services.income_service import list_income_rows, get_income_refund_context
from app.services.refund_flow_service import apply_refund_flow


router = APIRouter()


def _csv_response(*, filename: str, headers: list[str], rows: list[list[object]]) -> Response:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    writer.writerows(rows)
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _ensure_export_permission(account: Cuenta, enforcer_instance) -> None:
    if not enforcer_instance.enforce(account.rol.codigo, "economy_reports:export", "use"):
        from fastapi import HTTPException

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos para exportar reportes económicos.")


@router.get("/ingresos", response_model=list[IncomeListItem])
def get_income_rows(
    search: str | None = Query(default=None, min_length=1),
    source_type: str | None = Query(default=None),
    user_id: int | None = Query(default=None, gt=0),
    currency_id: int | None = Query(default=None, gt=0),
    payment_method: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("economy_income:view")),
) -> list[IncomeListItem]:
    return list_income_rows(
        db,
        account=account,
        search=search,
        source_type=source_type.strip().upper() if source_type else None,
        user_id=user_id,
        currency_id=currency_id,
        payment_method=payment_method,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/ingresos/{origin_type}/{origin_id}/refund-context", response_model=RefundContextResponse)
def get_refund_context(
    origin_type: str,
    origin_id: int,
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("economy_refunds:create")),
) -> RefundContextResponse:
    return get_income_refund_context(
        db,
        origin_type=origin_type.strip().upper(),
        origin_id=origin_id,
    )


@router.post("/devoluciones", response_model=RefundFlowResponse, status_code=status.HTTP_201_CREATED)
def create_refund_flow(
    payload: RefundFlowRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("economy_refunds:create")),
) -> RefundFlowResponse:
    return apply_refund_flow(
        db,
        payload=payload,
        account=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get("/egresos", response_model=list[ExpenseListItem])
def get_expenses(
    search: str | None = Query(default=None, min_length=1),
    expense_type: TipoEgresoEnum | None = Query(default=None, alias="type"),
    state: EstadoEgresoEnum | None = Query(default=None),
    cut_id: int | None = Query(default=None, gt=0),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("economy_expenses:list")),
) -> list[ExpenseListItem]:
    return list_expenses(
        db,
        account=account,
        search=search,
        expense_type=expense_type,
        state=state,
        cut_id=cut_id,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/egresos/{expense_id}", response_model=ExpenseDetailResponse)
def get_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("economy_expenses:view")),
) -> ExpenseDetailResponse:
    return get_expense_detail(db, expense_id=expense_id, account=account)


@router.post("/egresos", response_model=ExpenseDetailResponse, status_code=status.HTTP_201_CREATED)
def post_expense(
    payload: ExpenseCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("economy_expenses:create")),
) -> ExpenseDetailResponse:
    return create_expense(
        db,
        payload=payload,
        created_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.patch("/egresos/{expense_id}/annul", response_model=ExpenseDetailResponse)
def patch_expense_annul(
    expense_id: int,
    payload: ExpenseAnnulRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("economy_expenses:annul")),
) -> ExpenseDetailResponse:
    return annul_expense(
        db,
        expense_id=expense_id,
        payload=payload,
        changed_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get("/cortes-caja/me", response_model=CashCutOwnActiveResponse)
def get_my_cash_cut(
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("cash_cuts:view_own")),
) -> CashCutOwnActiveResponse:
    return get_my_active_cut(db, account=account)


@router.get("/cortes-caja/me/history", response_model=list[CashCutOwnHistoryItem])
def get_my_cash_cut_history(
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("cash_cuts:view_own")),
) -> list[CashCutOwnHistoryItem]:
    return get_my_cut_history(db, account=account)


@router.get("/cortes-caja", response_model=list[CashCutListItem])
def get_cash_cuts(
    cajero_id: int | None = Query(default=None, gt=0),
    state: EstadoCorteCajaEnum | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("cash_cuts:list")),
) -> list[CashCutListItem]:
    return list_cash_cuts(
        db,
        account=account,
        cajero_id=cajero_id,
        state=state,
        date_from=date_from,
        date_to=date_to,
    )


@router.post("/cortes-caja", response_model=CashCutDetailResponse, status_code=status.HTTP_201_CREATED)
def create_cash_cut(
    payload: CashCutCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("cash_cuts:open")),
) -> CashCutDetailResponse:
    return open_cash_cut(
        db,
        payload=payload,
        opened_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get("/cortes-caja/{cut_id}", response_model=CashCutDetailResponse)
def get_cut_detail(
    cut_id: int,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("cash_cuts:view")),
) -> CashCutDetailResponse:
    return get_cash_cut_detail(db, cut_id=cut_id, account=account)


@router.patch("/cortes-caja/{cut_id}/close", response_model=CashCutDetailResponse)
def close_cut(
    cut_id: int,
    payload: CashCutCloseRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("cash_cuts:close")),
) -> CashCutDetailResponse:
    return close_cash_cut(
        db,
        cut_id=cut_id,
        payload=payload,
        closed_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get("/reportes/estado-resultados", response_model=IncomeStatementReportResponse)
def get_income_statement(
    format: str = Query(default="json", pattern="^(json|csv)$"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    cashier_id: int | None = Query(default=None, gt=0),
    source_type: str | None = Query(default=None),
    currency_id: int | None = Query(default=None, gt=0),
    payment_method: str | None = Query(default=None),
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("economy_reports:view_all")),
    enforcer_instance=Depends(get_enforcer),
):
    report = get_income_statement_report(
        db,
        account=account,
        date_from=date_from,
        date_to=date_to,
        cashier_id=cashier_id,
        source_type=source_type.strip().upper() if source_type else None,
        currency_id=currency_id,
        payment_method=payment_method,
    )
    if format == "csv":
        _ensure_export_permission(account, enforcer_instance)
        return _csv_response(
            filename="estado_resultados.csv",
            headers=["SECCION", "ETIQUETA", "TOTAL_BOB"],
            rows=[
                ["RESUMEN", "INGRESOS_TOTAL_BOB", report.ingresos_total_bob],
                ["RESUMEN", "EGRESOS_TOTAL_BOB", report.egresos_total_bob],
                ["RESUMEN", "RESULTADO_BOB", report.resultado_bob],
                *[["INGRESOS_POR_FUENTE", item.label, item.total_bob] for item in report.ingresos_por_fuente],
                *[["EGRESOS_POR_TIPO", item.label, item.total_bob] for item in report.egresos_por_tipo],
            ],
        )
    return report


@router.get("/reportes/flujo-efectivo", response_model=CashFlowReportResponse)
def get_cash_flow(
    format: str = Query(default="json", pattern="^(json|csv)$"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    cashier_id: int | None = Query(default=None, gt=0),
    source_type: str | None = Query(default=None),
    currency_id: int | None = Query(default=None, gt=0),
    payment_method: str | None = Query(default=None),
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("economy_reports:view_all")),
    enforcer_instance=Depends(get_enforcer),
):
    report = get_cash_flow_report(
        db,
        account=account,
        date_from=date_from,
        date_to=date_to,
        cashier_id=cashier_id,
        source_type=source_type.strip().upper() if source_type else None,
        currency_id=currency_id,
        payment_method=payment_method,
    )
    if format == "csv":
        _ensure_export_permission(account, enforcer_instance)
        return _csv_response(
            filename="flujo_efectivo.csv",
            headers=["PERIODO", "INGRESOS_BOB", "EGRESOS_BOB", "RESULTADO_BOB", "EFECTIVO", "QR", "TRANSACCION", "TARJETA", "TICKET_O_VALE"],
            rows=[
                [
                    item.period,
                    item.ingresos_total_bob,
                    item.egresos_total_bob,
                    item.resultado_bob,
                    item.efectivo,
                    item.qr,
                    item.transaccion,
                    item.tarjeta,
                    item.ticket_o_vale,
                ]
                for item in report.serie_periodica
            ],
        )
    return report


@router.get("/reportes/cajeros/{user_id}", response_model=CashierReportResponse)
def get_cashier_summary(
    user_id: int,
    format: str = Query(default="json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("economy_reports:view_all")),
    enforcer_instance=Depends(get_enforcer),
):
    report = get_cashier_report(db, account=account, cashier_user_id=user_id)
    if format == "csv":
        _ensure_export_permission(account, enforcer_instance)
        return _csv_response(
            filename=f"reporte_cajero_{user_id}.csv",
            headers=["CORTE_ID", "APERTURA", "CIERRE", "ESTADO", "INGRESOS_BOB", "EGRESOS_BOB", "RESULTADO_BOB"],
            rows=[
                [
                    cut.id,
                    cut.fecha_apertura.isoformat(),
                    cut.fecha_cierre.isoformat() if cut.fecha_cierre else "",
                    cut.estado.value.upper(),
                    cut.ingresos_total_bob,
                    cut.egresos_total_bob,
                    cut.resultado_bob,
                ]
                for cut in report.cortes
            ],
        )
    return report


@router.get("/reportes/mi-periodo", response_model=MyPeriodReportResponse)
def get_my_period(
    format: str = Query(default="json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("economy_reports:view")),
    enforcer_instance=Depends(get_enforcer),
):
    report = get_my_period_report(db, account=account)
    if format == "csv":
        _ensure_export_permission(account, enforcer_instance)
        return _csv_response(
            filename="mi_periodo.csv",
            headers=["CONCEPTO", "TOTAL_BOB"],
            rows=[
                ["INGRESOS_TOTAL_BOB", report.ingresos_total_bob],
                ["EGRESOS_TOTAL_BOB", report.egresos_total_bob],
                ["RESULTADO_BOB", report.resultado_bob],
            ],
        )
    return report


@router.get("/reportes/mi-estado-resultados", response_model=MyIncomeStatementResponse)
def get_my_income_statement_report(
    format: str = Query(default="json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("economy_reports:view")),
    enforcer_instance=Depends(get_enforcer),
):
    report = get_my_income_statement(db, account=account)
    if format == "csv":
        _ensure_export_permission(account, enforcer_instance)
        return _csv_response(
            filename="mi_estado_resultados.csv",
            headers=["CONCEPTO", "TOTAL_BOB"],
            rows=[
                ["INGRESOS_TOTAL_BOB", report.ingresos_total_bob],
                ["EGRESOS_TOTAL_BOB", report.egresos_total_bob],
                ["RESULTADO_BOB", report.resultado_bob],
            ],
        )
    return report


@router.get("/reportes/mi-historial", response_model=MyHistoryReportResponse)
def get_my_history(
    format: str = Query(default="json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("economy_reports:view")),
    enforcer_instance=Depends(get_enforcer),
):
    report = get_my_history_report(db, account=account)
    if format == "csv":
        _ensure_export_permission(account, enforcer_instance)
        return _csv_response(
            filename="mi_historial_cortes.csv",
            headers=["CORTE_ID", "APERTURA", "CIERRE", "ESTADO", "INGRESOS", "VENTAS", "PAGOS", "FLETES", "METODOS", "RESULTADO", "EGRESOS_BOB"],
            rows=[
                [
                    cut.id,
                    cut.fecha_apertura.isoformat(),
                    cut.fecha_cierre.isoformat() if cut.fecha_cierre else "",
                    cut.estado.value.upper(),
                    cut.ingresos_display,
                    cut.ventas_display,
                    cut.pagos_display,
                    cut.fletes_display,
                    cut.metodos_display,
                    cut.resultado_display,
                    cut.egresos_total_bob,
                ]
                for cut in report.cuts
            ],
        )
    return report
