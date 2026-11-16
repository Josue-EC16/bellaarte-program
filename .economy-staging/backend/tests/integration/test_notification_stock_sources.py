"""Business stock sources and notification episodes in the same real transaction."""

from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from time import monotonic, sleep

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session


def contract(source):
    from app.models.boutique_item import ItemBoutique
    from app.models.workshop import InventarioTaller
    from app.services import notification_sync_service as sync

    return ((ItemBoutique, sync.sync_boutique_stock_notification, "tipo_item") if source.kind == "boutique"
            else (InventarioTaller, sync.sync_workshop_stock_notification, "tipo"))


def latest(session, source):
    from app.models.notification import Notificacion

    return session.execute(select(Notificacion).where(
        Notificacion.usuario_id == source.recipient.user_id, Notificacion.tipo == source.notification_type,
        Notificacion.tabla_referencia == source.table.upper(), Notificacion.id_referencia == source.id,
    ).order_by(Notificacion.id.desc()).execution_options(populate_existing=True)).scalars().first()


def test_real_stock_sequence_preserves_acknowledgement_and_opens_new_episode_after_recovery(pg_cluster, synthetic_stock_source):
    from app.services.notification_query_service import mark_notification_read

    source = synthetic_stock_source
    model, synchronize, _relationship = contract(source)
    actor = SimpleNamespace(usuario_id=source.recipient.user_id)
    with Session(pg_cluster.engine) as session:
        item = session.get(model, source.id)
        synchronize(session, item_id=source.id)  # Stock 2, minimum 3.
        session.commit()
        first = latest(session, source)
        first_id = first.id
        assert (first.revision, first.leida, first.resuelta) == (1, False, False)
        mark_notification_read(session, notification_id=first_id, account=actor, revision=1)
        item.stock = 0
        synchronize(session, item_id=source.id)
        session.commit()
        zero = latest(session, source)
        assert (zero.id, zero.revision, zero.leida, zero.resuelta) == (first_id, 2, False, False)
        mark_notification_read(session, notification_id=first_id, account=actor, revision=2)
        for stock in (1, 0):
            item.stock = stock
            synchronize(session, item_id=source.id)
            session.commit()
            current = latest(session, source)
            assert (current.id, current.revision, current.leida, current.resuelta) == (first_id, 2, True, False)
        item.stock = 4
        synchronize(session, item_id=source.id)
        session.commit()
        closed = latest(session, source)
        assert closed.id == first_id and closed.resuelta is True
        assert closed.motivo_cierre == "CONDICION_CORREGIDA"
        item.stock = 2
        synchronize(session, item_id=source.id)
        session.commit()
        reopened = latest(session, source)
        assert reopened.id != first_id
        assert (reopened.revision, reopened.leida, reopened.resuelta) == (1, False, False)


@pytest.mark.parametrize("deactivate", ["source", "category"])
def test_deactivating_actual_source_or_category_closes_stock_alert(pg_cluster, synthetic_stock_source, deactivate):
    source = synthetic_stock_source
    model, synchronize, relationship = contract(source)
    with Session(pg_cluster.engine) as session:
        item = session.get(model, source.id)
        synchronize(session, item_id=source.id)
        session.commit()
        identifier = latest(session, source).id
        if deactivate == "source":
            item.estado = False
        else:
            getattr(item, relationship).habilitado = False
        synchronize(session, item_id=source.id)
        session.commit()
        closed = latest(session, source)
        assert closed.id == identifier and closed.resuelta is True


def test_real_source_mutation_and_alert_both_rollback_before_business_commit(pg_cluster, synthetic_stock_source):
    source = synthetic_stock_source
    model, synchronize, _relationship = contract(source)
    with Session(pg_cluster.engine) as session:
        item = session.get(model, source.id)
        item.stock = 0
        synchronize(session, item_id=source.id)
        assert latest(session, source) is not None
        session.rollback()
    with Session(pg_cluster.engine) as observer:
        assert observer.get(model, source.id).stock == 2
        assert latest(observer, source) is None


@pytest.mark.parametrize("first", ["notification", "deactivation"])
def test_recipient_deactivation_and_stock_sync_leave_no_open_alert(pg_cluster, synthetic_stock_source, first):
    from app.models.account import Cuenta
    from app.services.notification_sync_service import reconcile_user_notification_eligibility

    source = synthetic_stock_source
    _model, synchronize, _relationship = contract(source)
    worker_pid = Queue()

    def deactivate(session):
        account = session.execute(select(Cuenta).where(Cuenta.id == source.recipient.account_id)
                                  .with_for_update()).scalar_one()
        account.is_active = False
        reconcile_user_notification_eligibility(session, user_ids=[source.recipient.user_id])

    def worker():
        with Session(pg_cluster.engine) as session:
            worker_pid.put(session.execute(text("SELECT pg_backend_pid()")).scalar_one())
            if first == "notification":
                deactivate(session)
            else:
                synchronize(session, item_id=source.id)
            session.commit()

    with ThreadPoolExecutor(max_workers=1) as executor:
        with Session(pg_cluster.engine) as locker:
            if first == "notification":
                synchronize(locker, item_id=source.id)
            else:
                deactivate(locker)
            future = executor.submit(worker)
            pid = worker_pid.get(timeout=10)
            deadline = monotonic() + 5
            try:
                while not locker.execute(text("SELECT cardinality(pg_blocking_pids(:pid)) > 0"), {"pid": pid}).scalar_one():
                    if monotonic() >= deadline:
                        pytest.fail("Concurrent recipient change did not reach its account lock.")
                    sleep(0.01)
                locker.commit()
            finally:
                locker.rollback()
        future.result(timeout=20)
    with Session(pg_cluster.engine) as observer:
        assert observer.get(Cuenta, source.recipient.account_id).is_active is False
        row = latest(observer, source)
        assert row is None or row.resuelta is True
