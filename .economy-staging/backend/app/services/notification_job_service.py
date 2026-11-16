from contextlib import contextmanager
from datetime import date
import logging
from time import monotonic

from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.notification_catalog import business_today
from app.models.account import Cuenta
from app.models.boutique_item import ItemBoutique
from app.models.flete import FleteVestido, SalidaFlete
from app.models.notification import EnvioNotificacionCorreo, Notificacion
from app.models.order import Pedido, PruebaPedido
from app.models.workshop import InventarioTaller
from app.services.notification_email_service import attempt_credential_email
from app.services.notification_sync_service import (
    sync_boutique_stock_notification, sync_flete_max_outputs_notification,
    sync_flete_return_notifications_for_output, sync_order_delivery_notifications_for_order,
    sync_test_schedule_notifications_for_test, sync_workshop_stock_notification,
    reconcile_material_preparation_recipients,
)

logger = logging.getLogger(__name__)
BATCH_SIZE = 200


@contextmanager
def notification_job_lock(engine, mode: str):
    key = {"daily": 1, "retry-emails": 2}[mode]
    with engine.connect() as connection:
        acquired = connection.execute(text("SELECT pg_try_advisory_lock(:namespace, :job)"),
                                      {"namespace": 184913, "job": key}).scalar_one()
        connection.commit()
        try:
            yield bool(acquired)
        finally:
            if acquired:
                try:
                    connection.execute(text("SELECT pg_advisory_unlock(:namespace, :job)"),
                                       {"namespace": 184913, "job": key})
                    connection.commit()
                except Exception:
                    connection.invalidate()  # A pooled connection must never retain a session lock.
                    raise


def run_daily_notification_checks(db: Session, *, today: date | None = None) -> dict:
    current_date = today or business_today()
    counters = {"created": 0, "updated": 0, "unchanged": 0, "resolved": 0, "errors": 0, "batches": 0}
    previous_counters = db.info.get("notification_counters")
    db.info["notification_counters"] = counters
    start = monotonic()
    def synchronize_test(test_id):
        sync_test_schedule_notifications_for_test(db, test_id=test_id, today=current_date)
        reconcile_material_preparation_recipients(db, test_id=test_id)

    jobs = (
        ("boutique_stock_checked", ItemBoutique, lambda value: sync_boutique_stock_notification(db, item_id=value)),
        ("workshop_stock_checked", InventarioTaller, lambda value: sync_workshop_stock_notification(db, item_id=value)),
        ("orders_checked", Pedido, lambda value: sync_order_delivery_notifications_for_order(db, order_id=value, today=current_date)),
        ("tests_checked", PruebaPedido, synchronize_test),
        ("flete_outputs_checked", SalidaFlete, lambda value: sync_flete_return_notifications_for_output(db, output_id=value, today=current_date)),
        ("fletes_checked", FleteVestido, lambda value: sync_flete_max_outputs_notification(db, flete_id=value)),
    )
    try:
        for name, model, synchronize in jobs:
            last_id = 0
            counters[name] = 0
            while True:
                ids = db.execute(select(model.id).where(model.id > last_id).order_by(model.id).limit(BATCH_SIZE)).scalars().all()
                if not ids:
                    break
                # Each origin commits independently: do not hold recipient locks
                # while acquiring the next commercial source in the batch.
                db.commit()
                for record_id in ids:
                    saved = {key: counters[key] for key in ("created", "updated", "unchanged", "resolved")}
                    try:
                        with db.begin_nested():
                            synchronize(record_id)
                        db.commit()
                    except Exception as error:
                        db.rollback()
                        counters.update(saved)
                        counters["errors"] += 1
                        logger.error("NOTIFICATION_CHECK_FAILED module=%s record_id=%s category=%s", name, record_id, type(error).__name__)
                        if isinstance(error, DBAPIError) and error.connection_invalidated:
                            raise
                    counters[name] += 1
                last_id = ids[-1]
                db.commit()
                counters["batches"] += 1
        counters["status"] = "failed" if counters["errors"] else "ok"
        counters["duration_seconds"] = round(monotonic() - start, 3)
        return counters
    finally:
        db.info.pop("notification_counters", None)
        if previous_counters is not None:
            db.info["notification_counters"] = previous_counters


def retry_failed_email_notifications(db: Session) -> dict:
    counters = {"checked": 0, "sent": 0, "already_sent": 0, "failed": 0, "uncertain": 0, "blocked": 0, "skipped": 0, "errors": 0}
    last_user_id = 0
    start = monotonic()
    while True:
        # Include durable attempts even if a crash happened before an ADMIN
        # notification could be created. Recipient copies are not separate jobs.
        error_users = select(Notificacion.id_referencia.label("user_id")).where(
            Notificacion.tipo == "ERROR_ENVIO_CORREO", Notificacion.resuelta.is_(False),
            Notificacion.tabla_referencia == "USUARIOS", Notificacion.id_referencia.is_not(None),
        )
        attempt_users = select(Cuenta.usuario_id.label("user_id")).join(
            EnvioNotificacionCorreo, EnvioNotificacionCorreo.cuenta_id == Cuenta.id,
        # Include terminal failures too: a process can stop after persisting its
        # result but before publishing the ADMIN notification. Republishing is
        # idempotent and never authorizes another SMTP attempt for these states.
        ).where(EnvioNotificacionCorreo.estado.in_(("EN_CURSO", "FALLIDO", "INCIERTO", "BLOQUEADO")))
        candidates = error_users.union(attempt_users).subquery()
        user_ids = db.execute(select(candidates.c.user_id).where(candidates.c.user_id > last_user_id)
                             .order_by(candidates.c.user_id).limit(BATCH_SIZE)).scalars().all()
        if not user_ids:
            break
        for user_id in user_ids:
            try:
                result = attempt_credential_email(db, user_id=user_id)
                counters[result["status"]] += 1
            except Exception as error:
                db.rollback()
                counters["errors"] += 1
                logger.error("NOTIFICATION_EMAIL_CHECK_FAILED user_id=%s category=%s", user_id, type(error).__name__)
                if isinstance(error, DBAPIError) and error.connection_invalidated:
                    raise
            counters["checked"] += 1
        last_user_id = user_ids[-1]
        db.commit()
    counters["status"] = "failed" if any(counters[key] for key in ("errors", "failed", "uncertain", "blocked")) else "ok"
    counters["duration_seconds"] = round(monotonic() - start, 3)
    return counters
