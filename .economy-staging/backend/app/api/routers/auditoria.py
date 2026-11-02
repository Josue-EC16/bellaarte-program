import csv
import io
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps.auth import require_permission
from app.models.account import Cuenta
from app.models.boutique_enums import TipoAccionAuditoriaEnum
from app.schemas.audit import AuditDetailResponse, AuditEventResponse, AuditListItem, AuditQueryFilters
from app.services.audit_service import (
    build_audit_printable_html,
    export_audit_rows_for_csv,
    get_audit_detail,
    get_audit_event,
    list_audits,
)


router = APIRouter()


def _filters_from_query(
    *,
    user_id: int | None,
    module: str | None,
    submodule: str | None,
    table: str | None,
    record_id: str | None,
    action: TipoAccionAuditoriaEnum | None,
    functional_action: str | None,
    date_from: date | None,
    date_to: date | None,
    ip: str | None,
    device: str | None,
    browser: str | None,
    operating_system: str | None,
    http_method: str | None,
    event_id: UUID | None,
    search_description: str | None,
    search_old_value: str | None,
    search_new_value: str | None,
    search_field: str | None,
) -> AuditQueryFilters:
    return AuditQueryFilters(
        user_id=user_id,
        module=module,
        submodule=submodule,
        table=table,
        record_id=record_id,
        action=action,
        functional_action=functional_action,
        date_from=date_from,
        date_to=date_to,
        ip=ip,
        device=device,
        browser=browser,
        operating_system=operating_system,
        http_method=http_method,
        event_id=event_id,
        search_description=search_description,
        search_old_value=search_old_value,
        search_new_value=search_new_value,
        search_field=search_field,
    )


@router.get("/eventos/{event_id}", response_model=AuditEventResponse)
def get_audit_event_detail(
    event_id: UUID,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("audit:view_event")),
) -> AuditEventResponse:
    return get_audit_event(db, event_id=event_id, account=account)


@router.get("/export")
def export_audits(
    format: str = Query(default="csv", pattern="^(csv|html)$"),
    user_id: int | None = Query(default=None, gt=0),
    module: str | None = Query(default=None),
    submodule: str | None = Query(default=None),
    table: str | None = Query(default=None),
    record_id: str | None = Query(default=None),
    action: TipoAccionAuditoriaEnum | None = Query(default=None),
    functional_action: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    ip: str | None = Query(default=None),
    device: str | None = Query(default=None),
    browser: str | None = Query(default=None),
    operating_system: str | None = Query(default=None),
    http_method: str | None = Query(default=None),
    event_id: UUID | None = Query(default=None),
    search_description: str | None = Query(default=None, min_length=1),
    search_old_value: str | None = Query(default=None, min_length=1),
    search_new_value: str | None = Query(default=None, min_length=1),
    search_field: str | None = Query(default=None, min_length=1),
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("audit:export")),
):
    filters = _filters_from_query(
        user_id=user_id,
        module=module,
        submodule=submodule,
        table=table,
        record_id=record_id,
        action=action,
        functional_action=functional_action,
        date_from=date_from,
        date_to=date_to,
        ip=ip,
        device=device,
        browser=browser,
        operating_system=operating_system,
        http_method=http_method,
        event_id=event_id,
        search_description=search_description,
        search_old_value=search_old_value,
        search_new_value=search_new_value,
        search_field=search_field,
    )
    if format == "html":
        return Response(content=build_audit_printable_html(db, account=account, filters=filters), media_type="text/html")

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "AUD_ID",
            "FECHA",
            "USUARIO",
            "USERNAME",
            "MODULO",
            "SUBMODULO",
            "TABLA",
            "ID_REGISTRO",
            "ACCION",
            "ACCION_FUNCIONAL",
            "DESCRIPCION",
            "CAMPO",
            "VALOR_ANTERIOR",
            "VALOR_NUEVO",
            "HTTP_METHOD",
            "IP",
            "DISPOSITIVO",
            "NAVEGADOR",
            "SISTEMA_OPERATIVO",
            "ID_EVENTO",
        ]
    )
    writer.writerows(export_audit_rows_for_csv(db, account=account, filters=filters))
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="auditoria_sistema.csv"'},
    )


@router.get("", response_model=list[AuditListItem])
def get_audits(
    user_id: int | None = Query(default=None, gt=0),
    module: str | None = Query(default=None),
    submodule: str | None = Query(default=None),
    table: str | None = Query(default=None),
    record_id: str | None = Query(default=None),
    action: TipoAccionAuditoriaEnum | None = Query(default=None),
    functional_action: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    ip: str | None = Query(default=None),
    device: str | None = Query(default=None),
    browser: str | None = Query(default=None),
    operating_system: str | None = Query(default=None),
    http_method: str | None = Query(default=None),
    event_id: UUID | None = Query(default=None),
    search_description: str | None = Query(default=None, min_length=1),
    search_old_value: str | None = Query(default=None, min_length=1),
    search_new_value: str | None = Query(default=None, min_length=1),
    search_field: str | None = Query(default=None, min_length=1),
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("audit:list")),
) -> list[AuditListItem]:
    return list_audits(
        db,
        account=account,
        filters=_filters_from_query(
            user_id=user_id,
            module=module,
            submodule=submodule,
            table=table,
            record_id=record_id,
            action=action,
            functional_action=functional_action,
            date_from=date_from,
            date_to=date_to,
            ip=ip,
            device=device,
            browser=browser,
            operating_system=operating_system,
            http_method=http_method,
            event_id=event_id,
            search_description=search_description,
            search_old_value=search_old_value,
            search_new_value=search_new_value,
            search_field=search_field,
        ),
    )


@router.get("/{audit_id}", response_model=AuditDetailResponse)
def get_audit_record(
    audit_id: int,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("audit:view")),
) -> AuditDetailResponse:
    return get_audit_detail(db, audit_id=audit_id, account=account)
