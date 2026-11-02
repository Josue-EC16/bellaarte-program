from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session, joinedload

from app.core.audit import register_audit_event
from app.core.notification_catalog import build_notification_action_path, can_resolve_manually, utc_now
from app.models.account import Cuenta
from app.models.boutique_enums import PrioridadNotificacionEnum
from app.models.notification import Notificacion
from app.models.role import Rol
from app.models.user import Usuario
from app.schemas.notification import (
    NotificationDetailResponse, NotificationListItem, NotificationPageResponse,
    NotificationQueryFilters, NotificationRecipientSummary, NotificationReportBucket,
    NotificationReportSummary, NotificationSummaryResponse,
)


def notification_query():
    return select(Notificacion).options(
        joinedload(Notificacion.usuario).joinedload(Usuario.cuenta).joinedload(Cuenta.rol)
    )


def to_list_item(entity: Notificacion) -> NotificationListItem:
    user = entity.usuario
    account = user.cuenta
    return NotificationListItem(
        id=entity.id, tipo=entity.tipo, prioridad=entity.prioridad,
        titulo=entity.titulo, mensaje=entity.mensaje, modulo=entity.modulo,
        leida=entity.leida, resuelta=entity.resuelta, fecha=entity.fecha,
        fecha_leida=entity.fecha_leida, fecha_resuelta=entity.fecha_resuelta,
        tabla_referencia=entity.tabla_referencia, id_referencia=entity.id_referencia,
        revision=entity.revision, revision_fecha=entity.revision_fecha,
        can_resolve=not entity.resuelta and can_resolve_manually(entity.tipo),
        motivo_cierre=entity.motivo_cierre, duplicada_de_id=entity.duplicada_de_id,
        recipient=NotificationRecipientSummary(
            user_id=user.id, full_name=user.nombre_completo,
            role_code=account.rol.codigo if account and account.rol else None,
            role_name=account.rol.nombre if account and account.rol else None,
            username=account.username if account else None,
        ),
    )


def to_detail_response(entity: Notificacion) -> NotificationDetailResponse:
    return NotificationDetailResponse(
        **to_list_item(entity).model_dump(),
        action_path=build_notification_action_path(entity.tabla_referencia, entity.id_referencia),
    )


def get_notification_detail(db: Session, *, notification_id: int, account: Cuenta, supervision: bool = False) -> NotificationDetailResponse:
    stmt = notification_query().where(Notificacion.id == notification_id)
    if not supervision:
        stmt = stmt.where(Notificacion.usuario_id == account.usuario_id)
    entity = db.execute(stmt).scalar_one_or_none()
    if entity is None:
        raise HTTPException(status_code=404, detail="Notificación no encontrada.")
    return to_detail_response(entity)


def filtered_notification_query(
    db: Session, *, account: Cuenta, filters: NotificationQueryFilters,
    search: str | None = None, supervision: bool = False,
):
    stmt = select(Notificacion).join(Notificacion.usuario).outerjoin(Usuario.cuenta).outerjoin(Cuenta.rol)
    if not supervision:
        stmt = stmt.where(Notificacion.usuario_id == account.usuario_id)
    else:
        if filters.user_id is not None:
            stmt = stmt.where(Notificacion.usuario_id == filters.user_id)
        if filters.role_code:
            stmt = stmt.where(Rol.codigo == filters.role_code)
    for value, column in (
        (filters.module, Notificacion.modulo), (filters.type, Notificacion.tipo),
        (filters.priority, Notificacion.prioridad), (filters.table_ref, Notificacion.tabla_referencia),
        (filters.record_id_ref, Notificacion.id_referencia),
    ):
        if value is not None:
            stmt = stmt.where(column == value)
    if filters.is_read is not None:
        stmt = stmt.where(Notificacion.leida.is_(filters.is_read))
    if filters.is_resolved is not None:
        stmt = stmt.where(Notificacion.resuelta.is_(filters.is_resolved))
    timezone = ZoneInfo("America/La_Paz")
    if filters.date_from is not None:
        stmt = stmt.where(Notificacion.fecha >= datetime.combine(filters.date_from, time.min, tzinfo=timezone))
    if filters.date_to is not None:
        stmt = stmt.where(Notificacion.fecha < datetime.combine(filters.date_to + timedelta(days=1), time.min, tzinfo=timezone))
    if search and search.strip():
        term = f"%{search.strip()}%"
        stmt = stmt.where(or_(
            Notificacion.titulo.ilike(term), Notificacion.mensaje.ilike(term),
            Notificacion.tipo.ilike(term), Usuario.nombres.ilike(term), Usuario.apellido_paterno.ilike(term),
        ))
    return stmt


def list_notifications(db: Session, *, account: Cuenta, filters: NotificationQueryFilters,
    search: str | None = None, page: int = 1, page_size: int = 25, supervision: bool = False) -> NotificationPageResponse:
    page, page_size = max(page, 1), min(max(page_size, 1), 100)
    stmt = filtered_notification_query(db, account=account, filters=filters, search=search, supervision=supervision)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.options(joinedload(Notificacion.usuario).joinedload(Usuario.cuenta).joinedload(Cuenta.rol))
        .order_by(Notificacion.fecha.desc(), Notificacion.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    ).unique().scalars().all()
    return NotificationPageResponse(items=[to_list_item(row) for row in rows], total=total, page=page, page_size=page_size)


def get_notification_summary(db: Session, *, account: Cuenta, limit: int = 8) -> NotificationSummaryResponse:
    own_open = (Notificacion.usuario_id == account.usuario_id, Notificacion.resuelta.is_(False))
    counts = db.execute(select(
        func.count().filter(Notificacion.leida.is_(False)),
        func.count(),
        func.count().filter(Notificacion.prioridad == PrioridadNotificacionEnum.URGENTE),
    ).select_from(Notificacion).where(*own_open)).one()
    priority_counts = {row[0].value.upper(): row[1] for row in db.execute(
        select(Notificacion.prioridad, func.count()).where(*own_open).group_by(Notificacion.prioridad)
    ).all()}
    rows = db.execute(notification_query().where(*own_open, Notificacion.leida.is_(False))
                      .order_by(Notificacion.revision_fecha.desc(), Notificacion.id.desc()).limit(min(max(limit, 1), 25))).unique().scalars().all()
    return NotificationSummaryResponse(
        unread_count=counts[0], unresolved_count=counts[1], urgent_count=counts[2],
        priority_counts=priority_counts, latest=[to_list_item(row) for row in rows],
    )


def mark_notification_read(db: Session, *, notification_id: int, account: Cuenta, revision: int) -> NotificationDetailResponse:
    # Only a simple row is locked: joined outer relationships cannot be FOR UPDATE targets.
    entity = db.execute(select(Notificacion).where(
        Notificacion.id == notification_id, Notificacion.usuario_id == account.usuario_id,
    ).with_for_update().execution_options(populate_existing=True)).scalar_one_or_none()
    if entity is None:
        raise HTTPException(status_code=404, detail="Notificación no encontrada.")
    if entity.revision != revision:
        raise HTTPException(status_code=409, detail="La notificación cambió. Actualiza para reconocer su revisión actual.")
    if not entity.leida:
        entity.leida, entity.fecha_leida = True, utc_now()
    db.commit()
    return get_notification_detail(db, notification_id=notification_id, account=account)


def mark_all_notifications_read(db: Session, *, account: Cuenta) -> dict[str, int]:
    # Capture revisions first. A zero-stock escalation between this read and UPDATE
    # must remain unread, even though the user requested 'read all'.
    snapshot = select(Notificacion.id.label("notification_id"), Notificacion.revision.label("observed_revision")).where(
        Notificacion.usuario_id == account.usuario_id, Notificacion.leida.is_(False), Notificacion.resuelta.is_(False),
    ).cte("pending_snapshot").prefix_with("MATERIALIZED")
    result = db.execute(update(Notificacion).where(
        Notificacion.id == snapshot.c.notification_id, Notificacion.usuario_id == account.usuario_id,
        Notificacion.revision == snapshot.c.observed_revision, Notificacion.leida.is_(False),
    ).values(leida=True, fecha_leida=utc_now()).execution_options(synchronize_session=False))
    updated = result.rowcount
    db.commit()
    return {"updated": updated}


def resolve_notification(db: Session, *, notification_id: int, reason: str, resolved_by: Cuenta,
                         ip_address: str | None, user_agent: str | None) -> NotificationDetailResponse:
    entity = db.execute(select(Notificacion).where(Notificacion.id == notification_id).with_for_update()).scalar_one_or_none()
    if entity is None:
        raise HTTPException(status_code=404, detail="Notificación no encontrada.")
    if not can_resolve_manually(entity.tipo):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Esta incidencia se cierra automáticamente cuando se corrige su origen. Puedes marcarla como leída.")
    if not entity.resuelta:
        entity.resuelta, entity.fecha_resuelta, entity.motivo_cierre = True, utc_now(), "MANUAL"
        entity.leida, entity.fecha_leida = True, entity.fecha_leida or entity.fecha_resuelta
        register_audit_event(db, action="NOTIFICATION_RESOLVED", description=f"Se resolvió la tarea #{entity.id}. Motivo: {reason}.",
                             account=resolved_by, user=resolved_by.usuario, reference=str(entity.id),
                             ip_address=ip_address, user_agent=user_agent)
    db.commit()
    return get_notification_detail(db, notification_id=notification_id, account=resolved_by, supervision=True)


def get_notification_report_summary(db: Session, *, account: Cuenta,
    filters: NotificationQueryFilters | None = None, search: str | None = None) -> NotificationReportSummary:
    filtered = filtered_notification_query(db, account=account, filters=filters or NotificationQueryFilters(),
                                           search=search, supervision=True)
    matching_ids = filtered.with_only_columns(Notificacion.id).correlate(None)
    scope = Notificacion.id.in_(matching_ids)
    counts = db.execute(select(
        func.count(), func.count().filter(Notificacion.leida.is_(False), Notificacion.resuelta.is_(False)),
        func.count().filter(Notificacion.resuelta.is_(False)),
        func.count().filter(Notificacion.resuelta.is_(False), Notificacion.prioridad == PrioridadNotificacionEnum.URGENTE),
    ).select_from(Notificacion).where(scope)).one()

    def collect(stmt):
        return [NotificationReportBucket(label=(value.value if hasattr(value, "value") else value or "SIN_DATO").upper(), count=count)
                for value, count in db.execute(stmt).all()]

    by_module = collect(select(Notificacion.modulo, func.count()).where(scope).group_by(Notificacion.modulo))
    by_priority = collect(select(Notificacion.prioridad, func.count()).where(scope).group_by(Notificacion.prioridad))
    by_role = collect(select(Rol.codigo, func.count()).select_from(Notificacion).join(Notificacion.usuario)
                      .outerjoin(Usuario.cuenta).outerjoin(Cuenta.rol).where(scope).group_by(Rol.codigo))
    by_type = collect(select(Notificacion.tipo, func.count()).where(scope).group_by(Notificacion.tipo))
    return NotificationReportSummary(total=counts[0], unread=counts[1], unresolved=counts[2], urgent_unresolved=counts[3],
                                     by_module=by_module, by_priority=by_priority, by_role=by_role, by_type=by_type)
