"""HTTP transaction boundary for retriable economic writes."""
from app.services.economic_idempotency_service import begin_operation, finish_operation


def economic_write(db, *, account, operation, key, payload, execute):
    try:
        row, replay = begin_operation(db, account, operation, key, payload)
        if replay is not None:
            return replay
        result = execute()
        result = finish_operation(db, row, result)
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise
