from fastapi import APIRouter, Body, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps.auth import require_permission
from app.models.account import Cuenta
from app.schemas.notification import (
    NotificationDesktopClaimResponse, NotificationDetailResponse, NotificationEmailRetryRequest,
    NotificationPageResponse, NotificationPreferencesRequest, NotificationPreferencesResponse,
    NotificationQueryFilters, NotificationReadRequest, NotificationReportSummary,
    NotificationResolveRequest, NotificationSummaryResponse,
)
from app.services.notification_service import (
    claim_desktop_notifications, get_notification_detail, get_notification_preferences,
    get_notification_report_summary, get_notification_summary, list_notifications,
    mark_all_notifications_read, mark_notification_read, resolve_notification,
    retry_email_notification, set_notification_preferences,
)

router = APIRouter()


@router.get("/resumen", response_model=NotificationSummaryResponse)
def get_notifications_summary(db: Session = Depends(get_db), account: Cuenta = Depends(require_permission("notifications:list"))):
    return get_notification_summary(db, account=account)


@router.get("/preferencias", response_model=NotificationPreferencesResponse)
def get_preferences(db: Session = Depends(get_db), account: Cuenta = Depends(require_permission("notifications:list"))):
    return get_notification_preferences(db, account=account)


@router.patch("/preferencias", response_model=NotificationPreferencesResponse)
def update_preferences(payload: NotificationPreferencesRequest, db: Session = Depends(get_db),
                       account: Cuenta = Depends(require_permission("notifications:list"))):
    return set_notification_preferences(db, account=account, desktop_enabled=payload.desktop_enabled)


@router.post("/escritorio/reclamar", response_model=NotificationDesktopClaimResponse)
def claim_desktop(db: Session = Depends(get_db), account: Cuenta = Depends(require_permission("notifications:list"))):
    return claim_desktop_notifications(db, account=account)


@router.patch("/read-all")
def mark_all_read(db: Session = Depends(get_db), account: Cuenta = Depends(require_permission("notifications:mark_all_read"))):
    return mark_all_notifications_read(db, account=account)


@router.get("/supervision", response_model=NotificationPageResponse)
def get_supervision(filters: NotificationQueryFilters = Depends(), search: str | None = Query(default=None, min_length=1),
                    page: int = Query(default=1, ge=1), page_size: int = Query(default=25, ge=1, le=100),
                    db: Session = Depends(get_db), account: Cuenta = Depends(require_permission("notifications:list_all"))):
    return list_notifications(db, account=account, filters=filters, search=search, page=page, page_size=page_size, supervision=True)


@router.get("/supervision/{notification_id}", response_model=NotificationDetailResponse)
def get_supervision_detail(notification_id: int, db: Session = Depends(get_db),
                           account: Cuenta = Depends(require_permission("notifications:list_all"))):
    return get_notification_detail(db, notification_id=notification_id, account=account, supervision=True)


@router.get("/reportes/resumen", response_model=NotificationReportSummary)
def get_notifications_report_summary(filters: NotificationQueryFilters = Depends(), search: str | None = Query(default=None, min_length=1),
                                     db: Session = Depends(get_db), account: Cuenta = Depends(require_permission("notifications:report"))):
    return get_notification_report_summary(db, account=account, filters=filters, search=search)


@router.get("", response_model=NotificationPageResponse)
def get_notifications(filters: NotificationQueryFilters = Depends(), search: str | None = Query(default=None, min_length=1),
                      page: int = Query(default=1, ge=1), page_size: int = Query(default=25, ge=1, le=100),
                      db: Session = Depends(get_db), account: Cuenta = Depends(require_permission("notifications:list"))):
    return list_notifications(db, account=account, filters=filters, search=search, page=page, page_size=page_size)


@router.get("/{notification_id}", response_model=NotificationDetailResponse)
def get_notification(notification_id: int, db: Session = Depends(get_db),
                     account: Cuenta = Depends(require_permission("notifications:view"))):
    return get_notification_detail(db, notification_id=notification_id, account=account)


@router.patch("/{notification_id}/read", response_model=NotificationDetailResponse)
def update_notification_as_read(notification_id: int, payload: NotificationReadRequest, db: Session = Depends(get_db),
                                account: Cuenta = Depends(require_permission("notifications:mark_read"))):
    return mark_notification_read(db, notification_id=notification_id, account=account, revision=payload.revision)


@router.patch("/{notification_id}/resolve", response_model=NotificationDetailResponse)
def resolve_notification_record(notification_id: int, payload: NotificationResolveRequest, request: Request,
                                db: Session = Depends(get_db), account: Cuenta = Depends(require_permission("notifications:resolve"))):
    return resolve_notification(db, notification_id=notification_id, reason=payload.motivo, resolved_by=account,
        ip_address=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))


@router.post("/{notification_id}/retry-email", response_model=NotificationDetailResponse)
def retry_notification_email(notification_id: int, request: Request,
                             payload: NotificationEmailRetryRequest | None = Body(default=None),
                             db: Session = Depends(get_db), account: Cuenta = Depends(require_permission("notifications:retry_email"))):
    return retry_email_notification(db, notification_id=notification_id, retried_by=account,
        confirm_uncertain=payload.confirm_uncertain if payload else False,
        ip_address=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))
