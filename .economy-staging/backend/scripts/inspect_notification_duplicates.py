"""Read-only notification duplicate diagnostic; prints SQL without connecting.

Explicit execution is restricted to the exclusive local testing instance:
  python -B scripts/inspect_notification_duplicates.py --inspect --expected-user TEST_ROLE
Set TEST_DATABASE_URL in the process only. No .env or application settings import.
Business database diagnostics require a separately reviewed, authorized procedure.
There is intentionally no --apply flag: the Alembic migration owns the repair.
"""

from __future__ import annotations

import argparse
import json
import os


DUPLICATE_SQL = """
WITH duplicate_groups AS (
    SELECT usu_id,
           upper(btrim(not_tipo)) AS tipo,
           nullif(upper(btrim(not_tabla_ref)), '') AS tabla_origen,
           not_id_ref,
           count(*) AS abiertas
    FROM notificacion
    WHERE not_resuelta = false
    GROUP BY usu_id, upper(btrim(not_tipo)),
             nullif(upper(btrim(not_tabla_ref)), ''), not_id_ref
    HAVING count(*) > 1
)
SELECT count(*) AS grupos_duplicados,
       coalesce(sum(abiertas), 0) AS filas_en_grupos,
       coalesce(sum(abiertas - 1), 0) AS cierres_propuestos
FROM duplicate_groups
""".strip()


def validate_target(raw_url: str, expected_user: str):
    """Fail closed: a testing name alone does not identify an isolated server."""
    from sqlalchemy.engine import make_url

    url = make_url(raw_url)
    if (
        url.drivername != "postgresql+psycopg2"
        or url.host != "127.0.0.1"
        or url.port != 55432
        or url.database != "bab_vdos_testing"
        or not expected_user
        or url.username != expected_user
        or not url.password
        or url.query
    ):
        raise ValueError("Target must match the explicit exclusive testing connection, without URL options.")
    return url


def inspect_duplicates(url, expected_user: str) -> dict[str, int]:
    from sqlalchemy import create_engine, text
    from sqlalchemy.pool import NullPool

    engine = create_engine(
        url,
        poolclass=NullPool,
        connect_args={
            "connect_timeout": 5,
            "options": "-c default_transaction_read_only=on -c statement_timeout=10000 -c lock_timeout=2000",
        },
    )
    try:
        with engine.connect() as connection:
            with connection.begin():
                connection.execute(text("SET TRANSACTION READ ONLY"))
                identity = connection.execute(text("""
                    SELECT current_database() AS database_name,
                           current_user AS role_name,
                           inet_server_port() AS port,
                           current_setting('transaction_read_only') AS read_only,
                           current_setting('server_version_num')::integer AS version
                """)).mappings().one()
                if (
                    identity["database_name"] != "bab_vdos_testing"
                    or identity["role_name"] != expected_user
                    or identity["port"] != 55432
                    or identity["read_only"] != "on"
                    or identity["version"] < 170000
                ):
                    raise ValueError("Server identity does not match the exclusive PostgreSQL testing target.")
                row = connection.execute(text(DUPLICATE_SQL)).mappings().one()
                return {key: int(value) for key, value in row.items()}
    finally:
        engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inspect", action="store_true", help="Execute SELECT against the explicit local testing target only.")
    parser.add_argument("--database-url-env", default="TEST_DATABASE_URL", choices=["TEST_DATABASE_URL"])
    parser.add_argument("--expected-user", help="Exact exclusive testing role; required with --inspect.")
    args = parser.parse_args()
    if not args.inspect:
        print("DRY RUN: no connection, no repair, no files written. SQL:")
        print(DUPLICATE_SQL + ";")
        return 0
    if not args.expected_user:
        parser.error("--expected-user is required with --inspect")
    raw_url = os.environ.get(args.database_url_env)
    if not raw_url:
        parser.error("TEST_DATABASE_URL must be explicitly supplied to this process; no application fallback is used")
    try:
        url = validate_target(raw_url, args.expected_user)
        result = inspect_duplicates(url, args.expected_user)
    except Exception:
        # Exception messages can contain connection strings, server details or
        # driver diagnostics; never print them. This script deliberately emits
        # aggregate counts only, not users, messages or reference details.
        print("Diagnostic failed or target rejected. No repair was performed.")
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
