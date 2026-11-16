"""Small process-wide PostgreSQL notification listener with durable fallback.

Only account IDs/revisions enter NOTIFY. Each stream loads its own authorized
snapshot in a short session; the shared listener borrows one connection while
subscribers exist and releases it when the final subscriber disconnects.
"""
import asyncio
import json
import logging
import select as io_select
import threading
import time

import anyio
from fastapi import HTTPException

from app.core.config import settings
from app.services.auth_session_service import AUTH_CHANNEL, auth_error, validate_session


logger = logging.getLogger(__name__)


class AuthEventBroker:
    def __init__(self):
        self.lock = threading.Lock()
        self.subscribers = 0
        self.revisions: dict[int, int] = {}
        self.thread = None

    def subscribe(self, account_id):
        with self.lock:
            self.subscribers += 1
            self.revisions.setdefault(account_id, 0)
            if self.thread is None or not self.thread.is_alive():
                self.thread = threading.Thread(target=self._listen, name="bab-auth-events", daemon=True)
                self.thread.start()

    def unsubscribe(self):
        with self.lock:
            self.subscribers = max(0, self.subscribers - 1)

    def revision(self, account_id):
        with self.lock:
            return self.revisions.get(account_id, 0)

    def _listen(self):
        while True:
            with self.lock:
                if not self.subscribers:
                    self.thread = None
                    self.revisions.clear()
                    return
            try:
                self._listen_once()
                return
            except Exception:
                # Recover LISTEN without requiring every browser to reconnect.
                # The per-stream database check remains authoritative meanwhile.
                logger.warning("AUTH_EVENTS_LISTENER_UNAVAILABLE")
                time.sleep(2)

    def _listen_once(self):
        from app.core.database import engine
        # A dedicated raw DBAPI connection, never a transaction or Session.
        # Its autocommit/LISTEN state must not leak into an ERP request pool.
        from sqlalchemy.pool import NullPool
        from sqlalchemy import create_engine
        listener_engine = create_engine(engine.url, poolclass=NullPool,
                                        connect_args={"connect_timeout": 3})
        try:
            with listener_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
                raw = connection.connection.driver_connection
                connection.exec_driver_sql(f"LISTEN {AUTH_CHANNEL}")
                while True:
                    with self.lock:
                        if not self.subscribers:
                            self.thread = None
                            self.revisions.clear()
                            return
                    if io_select.select([raw], [], [], 0.5)[0]:
                        raw.poll()
                        while raw.notifies:
                            notification = raw.notifies.pop(0)
                            try:
                                account_id = int(json.loads(notification.payload)["account_id"])
                            except (ValueError, KeyError, TypeError):
                                continue
                            with self.lock:
                                if account_id in self.revisions:
                                    self.revisions[account_id] += 1
        finally:
            listener_engine.dispose()


broker = AuthEventBroker()


def session_snapshot(account_id: int, payload: dict) -> dict:
    from app.core.database import SessionLocal
    from app.services.auth_service import get_account_by_id
    from app.services.user_service import build_user_summary
    with SessionLocal() as db:
        account = get_account_by_id(db, account_id)
        if account is None:
            raise auth_error()
        validate_session(db, account, payload)
        return {"type": "session", "user": build_user_summary(account).model_dump(mode="json"),
                "version": account.security_version}


async def session_events(request, account_id: int, payload: dict):
    broker.subscribe(account_id)
    revision = -1
    next_check = 0.0
    last_snapshot = None
    last_heartbeat = time.monotonic()
    try:
        while not await request.is_disconnected():
            if time.time() >= payload["exp"]:
                yield json.dumps({"type": "expired", "code": "ACCESS_TOKEN_EXPIRED"}) + "\n"
                return
            current_revision = broker.revision(account_id)
            now = time.monotonic()
            if revision != current_revision or now >= next_check:
                try:
                    snapshot = await anyio.to_thread.run_sync(session_snapshot, account_id, payload)
                except HTTPException as error:
                    code = error.detail.get("code", "SESSION_REVOKED") if isinstance(error.detail, dict) else "SESSION_REVOKED"
                    yield json.dumps({"type": "revoked", "code": code}) + "\n"
                    return
                except Exception:
                    # Do not preserve a privileged view when its authorization
                    # cannot be checked. This event asks for a clean reconnect.
                    yield json.dumps({"type": "unavailable", "code": "AUTH_STATE_UNAVAILABLE"}) + "\n"
                    return
                if snapshot != last_snapshot:
                    yield json.dumps(snapshot, ensure_ascii=False) + "\n"
                    last_snapshot = snapshot
                revision = current_revision
                next_check = now + settings.auth_event_recheck_seconds
            if now - last_heartbeat >= 15:
                yield '{"type":"heartbeat"}\n'
                last_heartbeat = now
            await asyncio.sleep(0.2)
    finally:
        broker.unsubscribe()
