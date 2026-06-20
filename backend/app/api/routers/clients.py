from datetime import date

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps.auth import require_permission
from app.models.account import Cuenta
from app.schemas.client import (
    ClienteCreateRequest,
    ClienteDetailResponse,
    ClienteListItem,
    ClienteStatusUpdateRequest,
    ClienteUpdateRequest,
)
from app.schemas.reporting import AnalyticsReportResponse, ListingSummaryResponse, ReportPeriod
from app.services.module_report_service import get_clients_report, get_clients_summary
from app.services.client_service import create_client, get_client, list_clients, set_client_status, update_client


router = APIRouter()


@router.get("", response_model=list[ClienteListItem])
def get_clients(
    search: str | None = Query(default=None, min_length=1),
    is_active: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("clients:list")),
) -> list[ClienteListItem]:
    return list_clients(db, search=search, is_active=is_active)


@router.get("/resumen", response_model=ListingSummaryResponse)
def get_clients_summary_endpoint(
    search: str | None = Query(default=None, min_length=1),
    is_active: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("clients:list")),
) -> ListingSummaryResponse:
    return get_clients_summary(db, search=search, is_active=is_active)


@router.get("/reportes/panel", response_model=AnalyticsReportResponse)
def get_clients_reports_panel(
    period: ReportPeriod = Query(default="all"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("clients_reports:view")),
) -> AnalyticsReportResponse:
    return get_clients_report(db, period=period, date_from=date_from, date_to=date_to)


@router.get("/{client_id}", response_model=ClienteDetailResponse)
def get_client_detail(
    client_id: int,
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("clients:view")),
) -> ClienteDetailResponse:
    return get_client(db, client_id)


@router.post("", response_model=ClienteDetailResponse, status_code=status.HTTP_201_CREATED)
def create_client_record(
    payload: ClienteCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("clients:create")),
) -> ClienteDetailResponse:
    return create_client(
        db,
        payload=payload,
        created_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.patch("/{client_id}", response_model=ClienteDetailResponse)
def update_client_record(
    client_id: int,
    payload: ClienteUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("clients:update")),
) -> ClienteDetailResponse:
    return update_client(
        db,
        client_id=client_id,
        payload=payload,
        updated_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.patch("/{client_id}/status", response_model=ClienteDetailResponse)
def update_client_record_status(
    client_id: int,
    payload: ClienteStatusUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("clients:update_status")),
) -> ClienteDetailResponse:
    return set_client_status(
        db,
        client_id=client_id,
        habilitado=payload.habilitado,
        changed_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
