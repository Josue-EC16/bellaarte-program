from datetime import timedelta

from sqlalchemy import case, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.notification_catalog import utc_now
from app.models.account import Cuenta
from app.models.boutique_enums import PrioridadNotificacionEnum
from app.models.notification import Notificacion, PreferenciaNotificacion
from app.schemas.notification import NotificationDesktopClaimResponse, NotificationPreferencesResponse
from app.services.notification_query_service import to_detail_response


def get_notification_preferences(db: Session, *, account: Cuenta) -> NotificationPreferencesResponse:
    preference = db.get(PreferenciaNotificacion, account.usuario_id)
    enabled_since = preference.escritorio_habilitado_desde if preference else None
    return NotificationPreferencesResponse(desktop_enabled=enabled_since is not None, desktop_enabled_since=enabled_since)


def set_notification_preferences(db: Session, *, account: Cuenta, desktop_enabled: bool) -> NotificationPreferencesResponse:
    db.execute(insert(PreferenciaNotificacion).values(usuario_id=account.usuario_id)
               .on_conflict_do_nothing(index_elements=[PreferenciaNotificacion.usuario_id]))
    preference = db.execute(select(PreferenciaNotificacion).where(
        PreferenciaNotificacion.usuario_id == account.usuario_id,
    ).with_for_update().execution_options(populate_existing=True)).scalar_one()
    if desktop_enabled and preference.escritorio_habilitado_desde is None:
        preference.escritorio_habilitado_desde = utc_now()
    elif not desktop_enabled:
        preference.escritorio_habilitado_desde = None
    response = NotificationPreferencesResponse(
        desktop_enabled=preference.escritorio_habilitado_desde is not None,
        desktop_enabled_since=preference.escritorio_habilitado_desde,
    )
    db.commit()
    return response


def claim_desktop_notifications(db: Session, *, account: Cuenta) -> NotificationDesktopClaimResponse:
    preference = db.execute(select(PreferenciaNotificacion).where(
        PreferenciaNotificacion.usuario_id == account.usuario_id,
    ).with_for_update()).scalar_one_or_none()
    if preference is None or preference.escritorio_habilitado_desde is None:
        db.commit()
        return NotificationDesktopClaimResponse(items=[])
    cutoff = max(preference.escritorio_habilitado_desde, utc_now() - timedelta(minutes=15))
    rows = db.execute(select(Notificacion).where(
        Notificacion.usuario_id == account.usuario_id,
        Notificacion.resuelta.is_(False), Notificacion.leida.is_(False),
        Notificacion.revision_fecha >= cutoff,
        Notificacion.escritorio_revision_reclamada < Notificacion.revision,
    ).order_by(case(
        (Notificacion.prioridad == PrioridadNotificacionEnum.URGENTE, 0),
        (Notificacion.prioridad == PrioridadNotificacionEnum.ALTA, 1),
        (Notificacion.prioridad == PrioridadNotificacionEnum.MEDIA, 2), else_=3,
    ), Notificacion.revision_fecha, Notificacion.id).limit(3)
      .with_for_update(skip_locked=True).execution_options(populate_existing=True)).scalars().all()
    for row in rows:
        row.escritorio_revision_reclamada = row.revision
    response = NotificationDesktopClaimResponse(items=[to_detail_response(row) for row in rows])
    # A lost response consumes the claim. Never reset/retry it automatically:
    # database at-most-once authorization cannot guarantee browser presentation.
    db.commit()
    return response
