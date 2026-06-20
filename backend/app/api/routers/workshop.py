from datetime import date

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps.auth import require_permission
from app.models.account import Cuenta
from app.schemas.workshop import (
    TallerEntryCreateRequest,
    TallerEntryDetailResponse,
    TallerEntryListItem,
    TallerEntryStatusUpdateRequest,
    TallerInventoryCreateRequest,
    TallerInventoryDetailResponse,
    TallerInventoryListItem,
    TallerInventoryStatusUpdateRequest,
    TallerInventoryUpdateRequest,
    TallerOutputCreateRequest,
    TallerOutputDetailResponse,
    TallerOutputListItem,
    TallerOutputStatusUpdateRequest,
    TallerTypeCreateRequest,
    TallerTypeResponse,
    TallerTypeStatusUpdateRequest,
    TallerTypeUpdateRequest,
)
from app.schemas.reporting import AnalyticsReportResponse, ListingSummaryResponse, ReportPeriod
from app.services.module_report_service import (
    get_workshop_entries_summary,
    get_workshop_inventory_summary,
    get_workshop_outputs_summary,
    get_workshop_report,
    get_workshop_types_summary,
)
from app.services.workshop_service import (
    create_workshop_entry,
    create_workshop_inventory,
    create_workshop_output,
    create_workshop_type,
    get_workshop_entry_detail,
    get_workshop_inventory_detail,
    get_workshop_output_detail,
    get_workshop_type,
    list_workshop_entries,
    list_workshop_inventory,
    list_workshop_outputs,
    list_workshop_types,
    set_workshop_entry_status,
    set_workshop_inventory_status,
    set_workshop_output_status,
    set_workshop_type_status,
    update_workshop_inventory,
    update_workshop_type,
)


router = APIRouter()


@router.get("/types", response_model=list[TallerTypeResponse])
def get_types(
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("workshop_types:list")),
) -> list[TallerTypeResponse]:
    return list_workshop_types(db)


@router.get("/types/resumen", response_model=ListingSummaryResponse)
def get_types_summary(
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("workshop_types:list")),
) -> ListingSummaryResponse:
    return get_workshop_types_summary(db)


@router.get("/types/{type_id}", response_model=TallerTypeResponse)
def get_type(
    type_id: int,
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("workshop_types:view")),
) -> TallerTypeResponse:
    return get_workshop_type(db, type_id)


@router.post("/types", response_model=TallerTypeResponse, status_code=status.HTTP_201_CREATED)
def create_type(
    payload: TallerTypeCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("workshop_types:create")),
) -> TallerTypeResponse:
    return create_workshop_type(
        db,
        payload=payload,
        created_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.patch("/types/{type_id}", response_model=TallerTypeResponse)
def update_type(
    type_id: int,
    payload: TallerTypeUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("workshop_types:update")),
) -> TallerTypeResponse:
    return update_workshop_type(
        db,
        type_id=type_id,
        payload=payload,
        updated_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.patch("/types/{type_id}/status", response_model=TallerTypeResponse)
def update_type_status(
    type_id: int,
    payload: TallerTypeStatusUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("workshop_types:update_status")),
) -> TallerTypeResponse:
    return set_workshop_type_status(
        db,
        type_id=type_id,
        enabled=payload.habilitado,
        changed_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get("/inventory", response_model=list[TallerInventoryListItem])
def get_inventory(
    type_id: int | None = Query(default=None, gt=0),
    search: str | None = Query(default=None, min_length=1),
    is_active: bool | None = Query(default=None),
    low_stock: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("workshop_inventory:list")),
) -> list[TallerInventoryListItem]:
    return list_workshop_inventory(db, type_id=type_id, search=search, is_active=is_active, low_stock=low_stock)


@router.get("/inventory/resumen", response_model=ListingSummaryResponse)
def get_inventory_summary(
    type_id: int | None = Query(default=None, gt=0),
    search: str | None = Query(default=None, min_length=1),
    is_active: bool | None = Query(default=None),
    low_stock: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("workshop_inventory:list")),
) -> ListingSummaryResponse:
    return get_workshop_inventory_summary(db, type_id=type_id, search=search, is_active=is_active, low_stock=low_stock)


@router.get("/inventory/{item_id}", response_model=TallerInventoryDetailResponse)
def get_inventory_item(
    item_id: int,
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("workshop_inventory:view")),
) -> TallerInventoryDetailResponse:
    return get_workshop_inventory_detail(db, item_id)


@router.post("/inventory", response_model=TallerInventoryDetailResponse, status_code=status.HTTP_201_CREATED)
def create_inventory_item(
    payload: TallerInventoryCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("workshop_inventory:create")),
) -> TallerInventoryDetailResponse:
    return create_workshop_inventory(
        db,
        payload=payload,
        created_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.patch("/inventory/{item_id}", response_model=TallerInventoryDetailResponse)
def update_inventory_item(
    item_id: int,
    payload: TallerInventoryUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("workshop_inventory:update")),
) -> TallerInventoryDetailResponse:
    return update_workshop_inventory(
        db,
        item_id=item_id,
        payload=payload,
        updated_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.patch("/inventory/{item_id}/status", response_model=TallerInventoryDetailResponse)
def update_inventory_status(
    item_id: int,
    payload: TallerInventoryStatusUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("workshop_inventory:update_status")),
) -> TallerInventoryDetailResponse:
    return set_workshop_inventory_status(
        db,
        item_id=item_id,
        is_active=payload.is_active,
        changed_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get("/entries", response_model=list[TallerEntryListItem])
def get_entries(
    search: str | None = Query(default=None, min_length=1),
    item_id: int | None = Query(default=None, gt=0),
    is_active: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("workshop_entries:list")),
) -> list[TallerEntryListItem]:
    return list_workshop_entries(db, search=search, item_id=item_id, is_active=is_active)


@router.get("/entries/resumen", response_model=ListingSummaryResponse)
def get_entries_summary(
    search: str | None = Query(default=None, min_length=1),
    item_id: int | None = Query(default=None, gt=0),
    is_active: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("workshop_entries:list")),
) -> ListingSummaryResponse:
    return get_workshop_entries_summary(db, search=search, item_id=item_id, is_active=is_active)


@router.get("/entries/{entry_id}", response_model=TallerEntryDetailResponse)
def get_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("workshop_entries:view")),
) -> TallerEntryDetailResponse:
    return get_workshop_entry_detail(db, entry_id)


@router.post("/entries", response_model=TallerEntryDetailResponse, status_code=status.HTTP_201_CREATED)
def create_entry(
    payload: TallerEntryCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("workshop_entries:create")),
) -> TallerEntryDetailResponse:
    return create_workshop_entry(
        db,
        payload=payload,
        created_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.patch("/entries/{entry_id}/status", response_model=TallerEntryDetailResponse)
def update_entry_status(
    entry_id: int,
    payload: TallerEntryStatusUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("workshop_entries:update_status")),
) -> TallerEntryDetailResponse:
    return set_workshop_entry_status(
        db,
        entry_id=entry_id,
        is_active=payload.is_active,
        changed_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get("/outputs", response_model=list[TallerOutputListItem])
def get_outputs(
    search: str | None = Query(default=None, min_length=1),
    item_id: int | None = Query(default=None, gt=0),
    is_active: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("workshop_outputs:list")),
) -> list[TallerOutputListItem]:
    return list_workshop_outputs(db, search=search, item_id=item_id, is_active=is_active)


@router.get("/outputs/resumen", response_model=ListingSummaryResponse)
def get_outputs_summary(
    search: str | None = Query(default=None, min_length=1),
    item_id: int | None = Query(default=None, gt=0),
    is_active: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("workshop_outputs:list")),
) -> ListingSummaryResponse:
    return get_workshop_outputs_summary(db, search=search, item_id=item_id, is_active=is_active)


@router.get("/reportes/panel", response_model=AnalyticsReportResponse)
def get_workshop_reports_panel(
    period: ReportPeriod = Query(default="all"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("workshop_reports:view")),
) -> AnalyticsReportResponse:
    return get_workshop_report(db, period=period, date_from=date_from, date_to=date_to)


@router.get("/outputs/{output_id}", response_model=TallerOutputDetailResponse)
def get_output(
    output_id: int,
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("workshop_outputs:view")),
) -> TallerOutputDetailResponse:
    return get_workshop_output_detail(db, output_id)


@router.post("/outputs", response_model=TallerOutputDetailResponse, status_code=status.HTTP_201_CREATED)
def create_output(
    payload: TallerOutputCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("workshop_outputs:create")),
) -> TallerOutputDetailResponse:
    return create_workshop_output(
        db,
        payload=payload,
        created_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.patch("/outputs/{output_id}/status", response_model=TallerOutputDetailResponse)
def update_output_status(
    output_id: int,
    payload: TallerOutputStatusUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("workshop_outputs:update_status")),
) -> TallerOutputDetailResponse:
    return set_workshop_output_status(
        db,
        output_id=output_id,
        is_active=payload.is_active,
        changed_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
