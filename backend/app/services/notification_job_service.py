from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.boutique_enums import EstadoPedidoGeneralEnum, EstadoSalidaFleteEnum
from app.models.boutique_item import ItemBoutique
from app.models.flete import FleteVestido, SalidaFlete
from app.models.notification import Notificacion
from app.models.order import Pedido, PruebaPedido
from app.models.user import Usuario
from app.models.workshop import InventarioTaller
from app.services.email_service import send_welcome_email
from app.services.notification_service import (
    sync_boutique_stock_notification,
    sync_flete_max_outputs_notification,
    sync_flete_return_notifications_for_output,
    sync_order_delivery_notifications_for_order,
    sync_test_schedule_notifications_for_test,
    sync_workshop_stock_notification,
    utc_now,
)


def run_daily_notification_checks(db: Session, *, today: date | None = None) -> dict[str, int]:
    current_date = today or date.today()
    counters = {
        "boutique_stock_checked": 0,
        "workshop_stock_checked": 0,
        "orders_checked": 0,
        "tests_checked": 0,
        "flete_outputs_checked": 0,
        "fletes_checked": 0,
    }

    for item_id in db.execute(select(ItemBoutique.id)).scalars().all():
        sync_boutique_stock_notification(db, item_id=item_id)
        counters["boutique_stock_checked"] += 1

    for item_id in db.execute(select(InventarioTaller.id)).scalars().all():
        sync_workshop_stock_notification(db, item_id=item_id)
        counters["workshop_stock_checked"] += 1

    for order_id in db.execute(select(Pedido.id).where(Pedido.habilitado.is_(True), Pedido.estado_general == EstadoPedidoGeneralEnum.ACTIVO)).scalars().all():
        sync_order_delivery_notifications_for_order(db, order_id=order_id, today=current_date)
        counters["orders_checked"] += 1

    for test_id in db.execute(select(PruebaPedido.id)).scalars().all():
        sync_test_schedule_notifications_for_test(db, test_id=test_id, today=current_date)
        counters["tests_checked"] += 1

    for output_id in db.execute(
        select(SalidaFlete.id).where(SalidaFlete.estado_salida.in_((EstadoSalidaFleteEnum.RESERVADO, EstadoSalidaFleteEnum.EN_FLETE)))
    ).scalars().all():
        sync_flete_return_notifications_for_output(db, output_id=output_id, today=current_date)
        counters["flete_outputs_checked"] += 1

    for flete_id in db.execute(select(FleteVestido.id)).scalars().all():
        sync_flete_max_outputs_notification(db, flete_id=flete_id)
        counters["fletes_checked"] += 1

    db.commit()
    return counters


def retry_failed_email_notifications(db: Session) -> dict[str, int]:
    retried = 0
    skipped = 0
    notifications = db.execute(
        select(Notificacion)
        .join(Notificacion.usuario)
        .where(
            Notificacion.tipo == "ERROR_ENVIO_CORREO",
            Notificacion.resuelta.is_(False),
            Notificacion.id_referencia.is_not(None),
        )
    ).scalars().all()
    for notification in notifications:
        user = db.execute(select(Usuario).where(Usuario.id == notification.id_referencia)).scalar_one_or_none()
        if user is None or user.cuenta is None or user.cuenta.last_login_at is not None:
            skipped += 1
            continue
        initial_password = user.ci.upper()
        success, _error_message = send_welcome_email(
            recipient_email=user.correo,
            full_name=user.nombre_completo,
            username=user.cuenta.username,
            initial_password=initial_password,
        )
        if not success:
            skipped += 1
            continue
        user.cuenta.password_hash = hash_password(initial_password)
        user.cuenta.must_change_password = True
        notification.resuelta = True
        notification.fecha_resuelta = utc_now()
        notification.leida = True
        notification.fecha_leida = notification.fecha_resuelta
        retried += 1
    db.commit()
    return {"retried": retried, "skipped": skipped, "pending": max(len(notifications) - retried, 0)}
