"""Real PostgreSQL assertions; import application modules only after guard fixtures."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from queue import Queue
from threading import Barrier
from time import monotonic, sleep
from types import SimpleNamespace

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def _insert(connection, user_id, *, kind="SISTEMA", revision_date=None, read=False, resolved=False):
    return connection.execute(text("""
        INSERT INTO notificacion (usu_id,not_tipo,not_prioridad,not_titulo,not_mensaje,not_leida,not_fec,
                                  not_resuelta,not_fec_resuelta,not_revision_fecha)
        VALUES (:user,:kind,'alta','QA SINTETICO','SOLO TEST',:read,CURRENT_TIMESTAMP,:resolved,
                CASE WHEN :resolved THEN CURRENT_TIMESTAMP ELSE NULL END,
                coalesce(:date,CURRENT_TIMESTAMP)) RETURNING not_id
    """), {"user": user_id, "kind": kind, "read": read, "resolved": resolved, "date": revision_date}).scalar_one()


def _upsert(session, recipient, *, zero=False, message="STOCK BAJO"):
    from app.models.boutique_enums import PrioridadNotificacionEnum
    from app.models.user import Usuario
    from app.services.notification_sync_service import create_notification_for_user

    return create_notification_for_user(session, user=session.get(Usuario, recipient.user_id),
        tipo="STOCK_BAJO_BOUTIQUE", prioridad=PrioridadNotificacionEnum.URGENTE if zero else PrioridadNotificacionEnum.ALTA,
        titulo="QA STOCK", mensaje=message, modulo="BOUTIQUE", tabla_referencia=None,
        id_referencia=None, stock_zero=zero)


def test_database_rejects_two_open_null_keys(pg_cluster, synthetic_recipient):
    with pg_cluster.engine.begin() as connection:
        _insert(connection, synthetic_recipient.user_id)
        with pytest.raises(IntegrityError) as error:
            with connection.begin_nested():
                _insert(connection, synthetic_recipient.user_id)
        assert error.value.orig.diag.constraint_name == "ux_notificacion_abierta"
        _insert(connection, synthetic_recipient.user_id, resolved=True)


def test_two_independent_sessions_upsert_one_open_episode(pg_cluster, synthetic_recipient):
    barrier = Barrier(2)

    def worker():
        with Session(pg_cluster.engine) as session:
            barrier.wait(timeout=10)
            entity = _upsert(session, synthetic_recipient)
            identifier = entity.id
            session.commit()
            return identifier

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(worker) for _ in range(2)]
        identifiers = [future.result(timeout=25) for future in futures]
    assert identifiers[0] == identifiers[1]
    with pg_cluster.engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM notificacion WHERE usu_id=:user AND NOT not_resuelta"),
                                  {"user": synthetic_recipient.user_id}).scalar_one() == 1


def test_acknowledgement_survives_updates_and_zero_escalates_only_once(pg_cluster, synthetic_recipient):
    from app.services.notification_query_service import mark_notification_read

    account = SimpleNamespace(usuario_id=synthetic_recipient.user_id)
    with Session(pg_cluster.engine) as session:
        first = _upsert(session, synthetic_recipient)
        identifier = first.id
        session.commit()
        mark_notification_read(session, notification_id=identifier, account=account, revision=1)
        changed = _upsert(session, synthetic_recipient, message="OTRO NIVEL TODAVIA BAJO")
        assert (changed.id, changed.revision, changed.leida) == (identifier, 1, True)
        session.commit()
        urgent = _upsert(session, synthetic_recipient, zero=True, message="CERO")
        assert (urgent.id, urgent.revision, urgent.leida) == (identifier, 2, False)
        session.commit()
        mark_notification_read(session, notification_id=identifier, account=account, revision=2)
        _upsert(session, synthetic_recipient, message="REPOSICION AUN INSUFICIENTE")
        session.commit()
        urgent_again = _upsert(session, synthetic_recipient, zero=True, message="CERO OTRA VEZ")
        assert (urgent_again.id, urgent_again.revision, urgent_again.leida) == (identifier, 2, True)
        session.commit()


def test_source_transaction_rollback_leaves_no_alert_in_other_session(pg_cluster, synthetic_recipient):
    with Session(pg_cluster.engine) as session:
        _upsert(session, synthetic_recipient)
        session.rollback()
    with pg_cluster.engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM notificacion WHERE usu_id=:user"),
                                  {"user": synthetic_recipient.user_id}).scalar_one() == 0


def test_read_cannot_consume_a_newer_revision(pg_cluster, synthetic_recipient):
    from fastapi import HTTPException
    from app.services.notification_query_service import mark_notification_read

    with Session(pg_cluster.engine) as session:
        entity = _upsert(session, synthetic_recipient)
        identifier = entity.id
        session.commit()
        _upsert(session, synthetic_recipient, zero=True)
        session.commit()
    with Session(pg_cluster.engine) as session:
        with pytest.raises(HTTPException) as error:
            mark_notification_read(session, notification_id=identifier,
                                   account=SimpleNamespace(usuario_id=synthetic_recipient.user_id), revision=1)
        assert error.value.status_code == 409
        session.rollback()
    with pg_cluster.engine.connect() as connection:
        assert connection.execute(text("SELECT not_leida FROM notificacion WHERE not_id=:id"), {"id": identifier}).scalar_one() is False


def test_read_all_snapshot_does_not_consume_concurrent_escalation(pg_cluster, synthetic_recipient):
    from app.services.notification_query_service import mark_all_notifications_read

    with pg_cluster.engine.begin() as connection:
        identifier = _insert(connection, synthetic_recipient.user_id, kind="STOCK_BAJO_BOUTIQUE")
    worker_pid = Queue()
    account = SimpleNamespace(usuario_id=synthetic_recipient.user_id)

    def reader():
        with Session(pg_cluster.engine) as session:
            worker_pid.put(session.execute(text("SELECT pg_backend_pid()")).scalar_one())
            return mark_all_notifications_read(session, account=account)

    with ThreadPoolExecutor(max_workers=1) as executor:
        with pg_cluster.engine.connect() as locker:
            transaction = locker.begin()
            try:
                locker.execute(text("SELECT not_id FROM notificacion WHERE not_id=:id FOR UPDATE"), {"id": identifier})
                future = executor.submit(reader)
                pid = worker_pid.get(timeout=10)
                deadline = monotonic() + 5
                while not locker.execute(text("SELECT cardinality(pg_blocking_pids(:pid)) > 0"), {"pid": pid}).scalar_one():
                    if monotonic() >= deadline:
                        pytest.fail("Read-all never reached the expected concurrent row-lock wait.")
                    sleep(0.01)
                locker.execute(text("""
                    UPDATE notificacion SET not_revision=2,not_revision_fecha=CURRENT_TIMESTAMP,
                        not_stock_cero_detectado=true,not_leida=false,not_fec_leida=NULL WHERE not_id=:id
                """), {"id": identifier})
                transaction.commit()
            finally:
                if transaction.is_active:
                    transaction.rollback()
        assert future.result(timeout=20) == {"updated": 0}
    with pg_cluster.engine.connect() as connection:
        row = connection.execute(text("SELECT not_revision,not_leida FROM notificacion WHERE not_id=:id"), {"id": identifier}).one()
        assert tuple(row) == (2, False)


def test_claim_is_at_most_once_across_two_sessions_and_reload(pg_cluster, synthetic_recipient):
    from app.services.notification_delivery_service import claim_desktop_notifications, set_notification_preferences

    account = SimpleNamespace(usuario_id=synthetic_recipient.user_id)
    with Session(pg_cluster.engine) as session:
        set_notification_preferences(session, account=account, desktop_enabled=True)
    with pg_cluster.engine.begin() as connection:
        identifier = _insert(connection, synthetic_recipient.user_id)
    barrier = Barrier(2)

    def worker():
        with Session(pg_cluster.engine) as session:
            barrier.wait(timeout=10)
            return [item.id for item in claim_desktop_notifications(session, account=account).items]

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(worker) for _ in range(2)]
        delivered = [item for future in futures for item in future.result(timeout=25)]
    assert delivered == [identifier]
    with Session(pg_cluster.engine) as session:
        assert claim_desktop_notifications(session, account=account).items == []


def test_claim_excludes_backlog_read_resolved_and_older_than_fifteen_minutes(pg_cluster, synthetic_recipient, monkeypatch):
    from app.services import notification_delivery_service as delivery

    now = datetime.now(timezone.utc)
    monkeypatch.setattr(delivery, "utc_now", lambda: now)
    account = SimpleNamespace(usuario_id=synthetic_recipient.user_id)
    with pg_cluster.engine.begin() as connection:
        connection.execute(text("INSERT INTO preferencia_notificacion(usuario_id,escritorio_habilitado_desde) VALUES (:user,:since)"),
                           {"user": synthetic_recipient.user_id, "since": now - timedelta(minutes=30)})
        _insert(connection, synthetic_recipient.user_id, kind="SISTEMA", revision_date=now - timedelta(minutes=16))
        _insert(connection, synthetic_recipient.user_id, kind="PRUEBA_1_ALISTAR_MATERIAL", read=True, revision_date=now)
        _insert(connection, synthetic_recipient.user_id, kind="PRUEBA_2_ALISTAR_MATERIAL", resolved=True, revision_date=now)
        eligible = _insert(connection, synthetic_recipient.user_id, kind="ENTREGA_PEDIDO_HOY", revision_date=now)
    with Session(pg_cluster.engine) as session:
        assert [item.id for item in delivery.claim_desktop_notifications(session, account=account).items] == [eligible]


def test_summary_and_read_all_are_personal_even_for_admin(pg_cluster, synthetic_recipient):
    from app.services.notification_query_service import get_notification_summary, mark_all_notifications_read

    account = SimpleNamespace(usuario_id=synthetic_recipient.user_id, rol=SimpleNamespace(codigo="ADMIN"))
    with pg_cluster.engine.begin() as connection:
        _insert(connection, synthetic_recipient.user_id)
        _insert(connection, synthetic_recipient.user_id, kind="PRUEBA_1_ALISTAR_MATERIAL", resolved=True)
    with Session(pg_cluster.engine) as session:
        summary = get_notification_summary(session, account=account)
        assert summary.unread_count == 1
        assert summary.unresolved_count == 1
        assert len(summary.latest) == 1
        assert mark_all_notifications_read(session, account=account) == {"updated": 1}
