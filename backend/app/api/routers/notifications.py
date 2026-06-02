from datetime import date

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps.auth import require_permission
from app.models.account import Cuenta
from app.models.boutique_enums import PrioridadNotificacionEnum
from app.schemas.notification import (
    NotificationDetailResponse,
    NotificationListItem,
    NotificationQueryFilters,
    NotificationReportSummary,
    NotificationResolveRequest,
    NotificationSummaryResponse,
)
from app.services.notification_service import (
    get_notification_detail,
    get_notification_report_summary,
    get_notification_summary,
    list_notifications,
    mark_all_notifications_read,
    mark_notification_read,
    resolve_notification,
    retry_email_notification,
)


router = APIRouter()


@router.get("/resumen", response_model=NotificationSummaryResponse)
def get_notifications_summary(
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("notifications:list")),
) -> NotificationSummaryResponse:
    return get_notification_summary(db, account=account)


@router.patch("/read-all")
def mark_all_read(
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("notifications:mark_all_read")),
) -> dict[str, int]:
    return mark_all_notifications_read(db, account=account)


@router.get("/reportes/resumen", response_model=NotificationReportSummary)
def get_notifications_report_summary(
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("notifications:report")),
) -> NotificationReportSummary:
    return get_notification_report_summary(db)


@router.get("", response_model=list[NotificationListItem])
def get_notifications(
    search: str | None = Query(default=None, min_length=1),
    user_id: int | None = Query(default=None, gt=0),
    role_code: str | None = Query(default=None),
    module: str | None = Query(default=None),
    type: str | None = Query(default=None),
    priority: PrioridadNotificacionEnum | None = Query(default=None),
    is_read: bool | None = Query(default=None),
    is_resolved: bool | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    table_ref: str | None = Query(default=None),
    record_id_ref: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("notifications:list")),
) -> list[NotificationListItem]:
    return list_notifications(
        db,
        account=account,
        search=search,
        filters=NotificationQueryFilters(
            user_id=user_id,
            role_code=role_code,
            module=module,
            type=type,
            priority=priority,
            is_read=is_read,
            is_resolved=is_resolved,
            date_from=date_from,
            date_to=date_to,
            table_ref=table_ref,
            record_id_ref=record_id_ref,
        ),
    )


@router.get("/{notification_id}", response_model=NotificationDetailResponse)
def get_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("notifications:view")),
) -> NotificationDetailResponse:
    return get_notification_detail(db, notification_id=notification_id, account=account)


@router.patch("/{notification_id}/read", response_model=NotificationDetailResponse)
def update_notification_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("notifications:mark_read")),
) -> NotificationDetailResponse:
    return mark_notification_read(db, notification_id=notification_id, account=account)


@router.patch("/{notification_id}/resolve", response_model=NotificationDetailResponse)
def resolve_notification_record(
    notification_id: int,
    payload: NotificationResolveRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("notifications:resolve")),
) -> NotificationDetailResponse:
    return resolve_notification(
        db,
        notification_id=notification_id,
        reason=payload.motivo,
        resolved_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.post("/{notification_id}/retry-email", response_model=NotificationDetailResponse, status_code=status.HTTP_200_OK)
def retry_notification_email(
    notification_id: int,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("notifications:retry_email")),
) -> NotificationDetailResponse:
    return retry_email_notification(
        db,
        notification_id=notification_id,
        retried_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
