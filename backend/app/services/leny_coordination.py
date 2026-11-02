"""Replaceable generation coordinator; PostgreSQL session lock, never a queue."""
from __future__ import annotations

from threading import Lock
from typing import Protocol

from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from app.services.leny_ollama import LenyError


LOCK_KEY = 0x4C454E590001


class GenerationLease(Protocol):
    def check(self) -> None: ...
    def close(self) -> None: ...


class PostgresLease:
    def __init__(self, engine, *, allow_quarantine=False):
        self._mutex = Lock()
        self._connection = None
        self._pid = None
        try:
            self._connection = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
            if not self._connection.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": LOCK_KEY}):
                raise LenyError("LENY_BUSY", "LENY está atendiendo otra solicitud. Intenta nuevamente en unos momentos.", 429)
            self._pid = self._connection.scalar(text("SELECT pg_backend_pid()"))
            if not allow_quarantine and self._connection.scalar(text("SELECT to_regclass('leny.inferencia_estado') IS NOT NULL")):
                if self._connection.scalar(text("SELECT EXISTS(SELECT 1 FROM leny.inferencia_estado WHERE state<>'idle')")):
                    raise LenyError('LENY_INFERENCE_UNCERTAIN','Una inferencia requiere reconciliación antes de usar LENY.',503)
            from app.core.config import settings
            if settings.leny_rag_enabled and not allow_quarantine and self._connection.scalar(text(
                'SELECT EXISTS(SELECT 1 FROM leny.rag_workers WHERE provider_inflight OR unsafe_reason IS NOT NULL)'
            )):
                raise LenyError('LENY_INFERENCE_UNCERTAIN', 'Una inferencia documental requiere reconciliación antes de usar LENY.', 503)
        except LenyError:
            self.close()
            raise
        except Exception:
            self.close()
            raise LenyError("LENY_COORDINATION_UNAVAILABLE", "No se pudo reservar la generación de LENY.") from None

    def check(self) -> None:
        with self._mutex:
            try:
                if self._connection is None or self._connection.closed or self._connection.invalidated:
                    raise RuntimeError("closed")
                if self._connection.scalar(text("SELECT pg_backend_pid()")) != self._pid:
                    raise RuntimeError("connection replaced")
            except Exception:
                raise LenyError("LENY_LOCK_LOST", "Se interrumpió la coordinación de LENY.") from None

    def close(self) -> None:
        with self._mutex:
            connection, self._connection = self._connection, None
            if connection is None:
                return
            try:
                connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": LOCK_KEY})
            except Exception:
                pass
            finally:
                # Never return a session-scoped lock to any connection pool.
                try:
                    connection.invalidate()
                finally:
                    connection.close()


class PostgresCoordinator:
    def __init__(self, url):
        # Dedicated physical connection, bounded connect/query/network failure.
        self.engine = create_engine(url, poolclass=NullPool, connect_args={
            "connect_timeout": 5, "options": "-c statement_timeout=5000",
            "keepalives": 1, "keepalives_idle": 5, "keepalives_interval": 2, "keepalives_count": 2,
        })

    def acquire(self) -> GenerationLease:
        return PostgresLease(self.engine)
