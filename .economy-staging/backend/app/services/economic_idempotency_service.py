"""Transaction-scoped economic idempotency. The coordinator owns commit/rollback."""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
import hashlib
import json

from fastapi import HTTPException
from sqlalchemy import select, text

from app.models.economy import SolicitudEconomica


def _json_default(value):
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(f"Unsupported economic payload value: {type(value).__name__}")


def canonical_payload(payload) -> str:
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump(mode="python")
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False, default=_json_default)


def begin_operation(db, account, operation: str, key: str | None, payload):
    """Return (request, replay JSON); lock before ANY economic/source row lock."""
    if not key or not key.strip() or len(key) > 120:
        raise HTTPException(status_code=422, detail="Se requiere Idempotency-Key de 1 a 120 caracteres.")
    operation = operation.strip()
    if not operation or len(operation) > 80:
        raise ValueError("Invalid economic operation name")
    key = key.strip()
    actor_id = account.usuario_id
    digest = hashlib.sha256(canonical_payload(payload).encode("utf-8")).hexdigest()
    lock_bytes = hashlib.sha256(f"economy:{actor_id}:{operation}:{key}".encode("utf-8")).digest()[:8]
    lock_id = int.from_bytes(lock_bytes, "big", signed=True)
    # Disable autoflush: lock acquisition must precede pending writes.
    with db.no_autoflush:
        db.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": lock_id})
        row = db.scalar(select(SolicitudEconomica).where(
            SolicitudEconomica.actor_id == actor_id,
            SolicitudEconomica.operacion == operation,
            SolicitudEconomica.clave == key,
        ))
    if row is not None:
        if row.payload_hash != digest:
            raise HTTPException(status_code=409, detail="La clave de idempotencia ya fue usada con datos diferentes.")
        if row.resultado is None:
            raise HTTPException(status_code=409, detail="La operación no tiene un resultado final; revise su estado antes de reintentar.")
        return row, row.resultado
    row = SolicitudEconomica(actor_id=actor_id, operacion=operation, clave=key, payload_hash=digest)
    db.add(row)
    return row, None


def finish_operation(db, row: SolicitudEconomica, result) -> dict:
    """Save the public result atomically with the business operation."""
    if hasattr(result, "model_dump"):
        result = result.model_dump(mode="json")
    value = json.loads(canonical_payload(result))
    if row.resultado is not None and row.resultado != value:
        raise ValueError("An idempotent result cannot be replaced")
    row.resultado = value
    return value
