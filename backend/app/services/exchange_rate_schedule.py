"""Pure Bolivia calendar policy; no scheduler or I/O."""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from app.services.exchange_rate_history_service import LA_PAZ, FAILURE_STATES


@dataclass(frozen=True)
class SyncDecision:
    reason: str
    target: date | None
    next_at: datetime | None
    used: int
    missing_days: int
    backlog: int


def five_am(day):
    return datetime.combine(day, time(5), tzinfo=LA_PAZ)


def next_after_failure(now):
    value = now + timedelta(hours=1)
    if value.astimezone(LA_PAZ).date() != now.astimezone(LA_PAZ).date():
        return max(value, five_am(value.astimezone(LA_PAZ).date()))
    return value


def decide_sync(rows, *, now, start_date, enabled, available=True):
    local = now.astimezone(LA_PAZ)
    today = local.date()
    done = {r.fecha_objetivo for r in rows if r.estado == "EXITOSO"}
    execution = [r for r in rows if r.fecha_intento.astimezone(LA_PAZ).date() == today and r.numero_intento > 0]
    used = max((r.numero_intento for r in execution), default=0)
    missing = 0
    cursor = today - timedelta(days=1)
    while start_date is not None and cursor >= start_date and cursor not in done:
        missing += 1
        cursor -= timedelta(days=1)
    if today in done:
        missing = 0  # Today recovered the operational episode; backlog remains separate.
    backlog = max((today - start_date).days, 0) - len({d for d in done if start_date <= d < today}) if start_date else 0
    def result(reason, target=None, next_at=None):
        return SyncDecision(reason, target, next_at, used, missing, backlog)
    if not enabled:
        return result("DISABLED")
    if start_date is None or today < start_date:
        return result("NOT_STARTED", next_at=five_am(start_date) if start_date else None)
    if not available:
        return result("PAUSED")
    initiated = [r for r in rows if r.estado == "INICIADO"]
    if initiated:
        return result("IN_PROGRESS", next_at=min(r.fecha_intento for r in initiated) + timedelta(seconds=120))
    if local < five_am(today):
        return result("WAITING", next_at=five_am(today))
    if used >= 10:
        return result("EXHAUSTED", next_at=five_am(today + timedelta(days=1)))
    scheduled = [r.proximo_intento for r in execution if r.estado in FAILURE_STATES and r.proximo_intento is not None]
    if scheduled and max(scheduled) > now:
        return result("WAITING", next_at=max(scheduled))
    if today not in done:
        return result("DUE", today, now)
    failed_today = {r.fecha_objetivo for r in execution if r.estado in FAILURE_STATES and r.fecha_objetivo < today}
    cursor = start_date
    while cursor < today:
        if cursor not in done and cursor not in failed_today:
            return result("DUE", cursor, now)
        cursor += timedelta(days=1)
    return result("COMPLETE", next_at=five_am(today + timedelta(days=1)))
