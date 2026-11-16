import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, Query, Request, Response, status, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps.auth import get_enforcer, require_permission, get_current_account
from app.models.account import Cuenta
from app.models.boutique_enums import EstadoCorteCajaEnum, EstadoEgresoEnum, TipoEgresoEnum
from app.schemas.economy import (
    CashCutCloseRequest, CashCutPageResponse, CashCutOwnHistoryPageResponse,
    CashCutCreateRequest,
    CashCutDetailResponse,
    CashCutListItem,
    CashCutOwnActiveResponse,
    CashCutOwnHistoryItem,
    ExpenseAnnulRequest,
    ExpenseCreateRequest,
    ExpenseDetailResponse,
    ExpenseListItem,
    IncomeListItem, IncomePageResponse, ExpensePageResponse, OperativeCancellationRequest, GuaranteeMovementRequest,
    IncomeStatementReportResponse,
    MyHistoryReportResponse,
    MyIncomeStatementResponse,
    MyPeriodReportResponse,
    RefundContextResponse,
    RefundFlowRequest,
    RefundFlowResponse,
)
from app.services.cash_cut_service import close_cash_cut, get_cash_cut_detail, get_my_active_cut, get_my_cut_history, list_cash_cuts, open_cash_cut, get_my_cut_history_page
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
from app.services.refund_flow_service import apply_refund_flow, apply_operative_cancellation, apply_guarantee_movement
from app.services.economic_write_service import economic_write


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


@router.get("/ingresos", response_model=IncomePageResponse)
def get_income_rows(
    page: int = Query(default=1,ge=1),
    page_size: int = Query(default=25,ge=1,le=100),
    search: str | None = Query(default=None, min_length=1),
    source_type: str | None = Query(default=None),
    user_id: int | None = Query(default=None, gt=0),
    currency_id: int | None = Query(default=None, gt=0),
    payment_method: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("economy_income:view")),
) -> IncomePageResponse:
    return list_income_rows(
        db,page=page,page_size=page_size,
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
    account: Cuenta = Depends(require_permission("economy_refunds:create")),
) -> RefundContextResponse:
    return get_income_refund_context(
        db,
        origin_type=origin_type.strip().upper(),
        origin_id=origin_id,account=account,
    )


@router.post("/devoluciones", response_model=RefundFlowResponse, status_code=status.HTTP_201_CREATED)
def create_refund_flow(
    payload: RefundFlowRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("economy_refunds:create")),
) -> RefundFlowResponse:
    return economic_write(db,account=account,operation="refund",
        key=request.headers.get("Idempotency-Key"),payload={"body":payload.model_dump(mode="python"),"resource_id":None},
        execute=lambda: apply_refund_flow(
        db,
        payload=payload,
        account=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        commit=False,
    ))


@router.get("/egresos", response_model=ExpensePageResponse)
def get_expenses(
    page: int = Query(default=1,ge=1),
    page_size: int = Query(default=25,ge=1,le=100),
    search: str | None = Query(default=None, min_length=1),
    expense_type: TipoEgresoEnum | None = Query(default=None, alias="type"),
    state: EstadoEgresoEnum | None = Query(default=None),
    cut_id: int | None = Query(default=None, gt=0),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("economy_expenses:list")),
) -> ExpensePageResponse:
    return list_expenses(
        db,page=page,page_size=page_size,
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
    return economic_write(db,account=account,operation="expense_create",
        key=request.headers.get("Idempotency-Key"),payload={"body":payload.model_dump(mode="python"),"resource_id":None},
        execute=lambda: create_expense(
        db,
        payload=payload,
        created_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        commit=False,
    ))


@router.patch("/egresos/{expense_id}/annul", response_model=ExpenseDetailResponse)
def patch_expense_annul(
    expense_id: int,
    payload: ExpenseAnnulRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("economy_expenses:annul")),
) -> ExpenseDetailResponse:
    return economic_write(db,account=account,operation="expense_annul",
        key=request.headers.get("Idempotency-Key"),payload={"body":payload.model_dump(mode="python"),"resource_id":expense_id},
        execute=lambda: annul_expense(
        db,
        expense_id=expense_id,
        payload=payload,
        changed_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        commit=False,
    ))


@router.get("/cortes-caja/me", response_model=CashCutOwnActiveResponse)
def get_my_cash_cut(
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("cash_cuts:view_own")),
) -> CashCutOwnActiveResponse:
    return get_my_active_cut(db, account=account)


@router.get("/cortes-caja/me/history", response_model=CashCutOwnHistoryPageResponse)
def get_my_cash_cut_history(
    page: int = Query(default=1,ge=1),
    page_size: int = Query(default=25,ge=1,le=100),
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("cash_cuts:view_own")),
) -> CashCutOwnHistoryPageResponse:
    return get_my_cut_history_page(db, account=account,page=page,page_size=page_size)


@router.get("/cortes-caja", response_model=CashCutPageResponse)
def get_cash_cuts(
    page: int = Query(default=1,ge=1),
    page_size: int = Query(default=25,ge=1,le=100),
    cajero_id: int | None = Query(default=None, gt=0),
    state: EstadoCorteCajaEnum | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("cash_cuts:list")),
) -> CashCutPageResponse:
    return list_cash_cuts(
        db,page=page,page_size=page_size,
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
    return economic_write(db,account=account,operation="cut_open",
        key=request.headers.get("Idempotency-Key"),payload={"body":payload.model_dump(mode="python"),"resource_id":None},
        execute=lambda: open_cash_cut(
        db,
        payload=payload,
        opened_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        commit=False,
    ))


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
    return economic_write(db,account=account,operation="cut_close",
        key=request.headers.get("Idempotency-Key"),payload={"body":payload.model_dump(mode="python"),"resource_id":cut_id},
        execute=lambda: close_cash_cut(
        db,
        cut_id=cut_id,
        payload=payload,
        closed_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        commit=False,
    ))


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
                ["RESUMEN", "COMPARABILIDAD", report.comparison_note or "COMPARABLE"],
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
            headers=["PERIODO", "INGRESOS_BOB", "EGRESOS_BOB", "RESULTADO_BOB", "EFECTIVO", "QR", "TRANSACCION", "TARJETA", "TICKET_O_VALE", "COMPARABILIDAD"],
            rows=[
                ["RESUMEN",report.entradas_total_bob,report.egresos_total_bob,report.flujo_neto_bob,
                 "","","","","",report.comparison_note or "COMPARABLE"],
                *[ [
                    item.period,
                    item.ingresos_total_bob,
                    item.egresos_total_bob,
                    item.resultado_bob,
                    item.efectivo,
                    item.qr,
                    item.transaccion,
                    item.tarjeta,
                    item.ticket_o_vale,
                    report.comparison_note or "COMPARABLE",
                ]
                for item in report.serie_periodica]
            ],
        )
    return report


@router.get("/reportes/cajeros/{user_id}", response_model=CashierReportResponse)
def get_cashier_summary(
    user_id: int,
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    format: str = Query(default="json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("economy_reports:view_all")),
    enforcer_instance=Depends(get_enforcer),
):
    report = get_cashier_report(db, account=account, cashier_user_id=user_id,date_from=date_from,date_to=date_to)
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


@router.post("/anulaciones-operativas")
def operative_cancel(payload: OperativeCancellationRequest,request: Request,
                     db: Session=Depends(get_db),account: Cuenta=Depends(get_current_account),
                     enforcer_instance=Depends(get_enforcer)):
    permission={"VENTA_BOUTIQUE":"boutique_sales:cancel" if payload.target_state=="CANCELADA" else "boutique_sales:annul",
                "PAGO_PEDIDO":"order_payments:annul","SALIDA_FLETE":"flete_outputs:annul"}[payload.origin_type]
    if not enforcer_instance.enforce(account.rol.codigo,permission,"use"):
        raise HTTPException(403,"No tienes permiso para anular esta operaci?n.")
    return economic_write(db,account=account,operation="operative_cancel",key=request.headers.get("Idempotency-Key"),payload=payload,
        execute=lambda:apply_operative_cancellation(db,payload=payload,account=account,
            ip_address=request.client.host if request.client else None,user_agent=request.headers.get("user-agent"),commit=False))


@router.post("/garantias/{origin_id}/movimientos")
def guarantee_movement(origin_id:int,payload:GuaranteeMovementRequest,request:Request,
                       db:Session=Depends(get_db),account:Cuenta=Depends(require_permission("economy_refunds:create"))):
    return economic_write(db,account=account,operation="guarantee",key=request.headers.get("Idempotency-Key"),
        payload={"origin_id":origin_id,"body":payload.model_dump(mode="python")},
        execute=lambda:apply_guarantee_movement(db,origin_id=origin_id,payload=payload,account=account,
            ip_address=request.client.host if request.client else None,user_agent=request.headers.get("user-agent"),commit=False))


@router.get("/constancias-devolucion/{constancia_id}")
def refund_certificate(constancia_id:int,db:Session=Depends(get_db),
                       account:Cuenta=Depends(require_permission("economy_expenses:view"))):
    from app.models.economy import ConstanciaDevolucion,Egreso
    constancia=db.get(ConstanciaDevolucion,constancia_id)
    if constancia is None:
        raise HTTPException(404,"Constancia no encontrada.")
    expense=db.get(Egreso,constancia.egreso_id)
    if account.rol.codigo!="ADMIN" and expense.usuario_id!=account.usuario_id:
        raise HTTPException(403,"Solo puedes consultar tus constancias.")
    return {"id":constancia.id,"fecha":constancia.fecha,"snapshot":constancia.snapshot,"fiscal":False}


@router.get("/garantias/{origin_id}")
def guarantee_balance(origin_id:int,db:Session=Depends(get_db),
                      account:Cuenta=Depends(require_permission("economy_refunds:create"))):
    from app.models.flete import SalidaFlete
    from app.services.financial_source_service import ensure_source_access
    from app.services.income_service import _get_active_cut_for_cajero
    from app.services.economic_ledger_service import get_guarantee_balance
    source=db.get(SalidaFlete,origin_id)
    if source is None:
        raise HTTPException(404,"Salida no encontrada.")
    cut=None if account.rol.codigo=="ADMIN" else _get_active_cut_for_cajero(db,cajero_id=account.usuario_id)
    ensure_source_access(account,source,cut)
    return get_guarantee_balance(db,origin_id)
