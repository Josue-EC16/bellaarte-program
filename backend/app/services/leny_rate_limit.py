"""PostgreSQL rolling quota, serialized by the actual person, across workers."""
from contextlib import contextmanager
from datetime import timedelta
from hashlib import sha256
import json
import math
from types import SimpleNamespace

from sqlalchemy import delete, func, select, text
from sqlalchemy.dialects.postgresql import insert

from app.core.audit import register_audit_event
from app.models.leny import LenyAdmission, LenyRateUser
from app.services.leny_ollama import LenyError
from app.services.leny_store import LenyConflict


class RateLimiter:
    def __init__(self, session_factory, limit=5, window_seconds=60):
        if limit < 1 or window_seconds <= 0:
            raise ValueError("Quota limit and window must be positive.")
        self.session_factory, self.limit, self.window_seconds = session_factory, limit, window_seconds

    @contextmanager
    def transaction(self):
        with self.session_factory() as db, db.begin():
            db.execute(text("SET LOCAL lock_timeout = '5s'"))
            db.execute(text("SET LOCAL statement_timeout = '10s'"))
            yield db

    @staticmethod
    def fingerprint(payload):
        encoded = json.dumps([str(payload.conversation_id), payload.message], ensure_ascii=False,
                             separators=(",", ":")).encode("utf-8")
        return sha256(encoded).hexdigest()

    def admit(self, actor, payload):
        failure = None
        with self.transaction() as db:
            db.execute(insert(LenyRateUser).values(user_id=actor.user_id).on_conflict_do_nothing())
            owner = db.scalar(select(LenyRateUser).where(LenyRateUser.user_id == actor.user_id).with_for_update())
            # clock_timestamp is sampled after lock acquisition, not transaction start.
            now = db.scalar(select(func.clock_timestamp()))
            previous = db.get(LenyAdmission, (actor.user_id, payload.request_id))
            fingerprint = self.fingerprint(payload)
            if previous is not None:
                if previous.fingerprint != fingerprint:
                    raise LenyConflict("LENY_REQUEST_REUSED", "El identificador de solicitud ya fue utilizado.")
                raise LenyConflict("LENY_REQUEST_DUPLICATE", "Esta solicitud ya fue registrada.",
                                   "interrupted" if previous.outcome == "admitted" else previous.outcome, payload.request_id)
            cutoff = now - timedelta(seconds=self.window_seconds)
            count, first = db.execute(select(func.count(), func.min(LenyAdmission.admitted_at)).where(
                LenyAdmission.user_id == actor.user_id, LenyAdmission.admitted_at > cutoff)).one()
            if count >= self.limit:
                retry_after = max(1, math.ceil((first + timedelta(seconds=self.window_seconds) - now).total_seconds()))
                failure = LenyError("LENY_RATE_LIMITED", "Alcanzaste el límite de solicitudes de LENY. Intenta nuevamente más tarde.", 429)
                failure.retry_after = retry_after
                if owner.last_quota_audit_at is None or owner.last_quota_audit_at <= cutoff:
                    register_audit_event(
                        db, action="LENY_QUOTA_EXCEEDED", description="LENY QUOTA EXCEEDED",
                        user=SimpleNamespace(id=actor.user_id), reference=str(actor.user_id), module="LENY",
                        submodule="ADMISION", table="leny.admissions", functional_action="LENY_QUOTA_EXCEEDED",
                        event_id=actor.event_id, http_method="POST", ip_address=actor.ip_address,
                        user_agent=actor.user_agent,
                    )
                    owner.last_quota_audit_at = now
            else:
                db.add(LenyAdmission(user_id=actor.user_id, request_id=payload.request_id,
                                     fingerprint=fingerprint, admitted_at=now, outcome="admitted"))
            # Keep deduplication for at least an hour and the whole active quota
            # window. Bounded, owner-only maintenance never takes another user's lock.
            expired = select(LenyAdmission.request_id).where(
                LenyAdmission.user_id == actor.user_id,
                LenyAdmission.admitted_at < now - timedelta(seconds=max(3600, self.window_seconds)),
            ).order_by(LenyAdmission.admitted_at).limit(100)
            db.execute(delete(LenyAdmission).where(LenyAdmission.user_id == actor.user_id,
                                                  LenyAdmission.request_id.in_(expired)))
        # Commit the aggregate audit before returning 429.
        if failure:
            raise failure

    def finish(self, actor, request_id, outcome):
        if not isinstance(outcome, str) or not outcome or len(outcome) > 32:
            raise ValueError("Invalid admission outcome.")
        with self.transaction() as db:
            admission = db.get(LenyAdmission, (actor.user_id, request_id), with_for_update=True)
            if admission is not None:
                admission.outcome = outcome
