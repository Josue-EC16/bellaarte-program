"""Transactional DDL exercise, only on the explicitly provisioned isolated cluster."""

import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text


def test_upgrade_repairs_null_key_duplicates_without_deleting_history(pg_cluster, synthetic_recipient):
    migration_path = Path(__file__).resolve().parents[2] / "alembic" / "versions" / "20261018_0014_notification_reliability.py"
    spec = importlib.util.spec_from_file_location("notification_reliability_migration_test", migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with pg_cluster.migration_engine.connect() as connection:
        transaction = connection.begin()
        try:
            pg_cluster.assert_identity(connection, pg_cluster.manifest, migrator=True)
            with Operations.context(MigrationContext.configure(connection)):
                migration.downgrade()
                rows = []
                for kind, read in ((" sistema ", True), ("SISTEMA", False)):
                    rows.append(connection.execute(text("""
                        INSERT INTO notificacion (usu_id,not_tipo,not_prioridad,not_titulo,not_mensaje,not_leida,
                                                  not_fec,not_resuelta,not_tabla_ref,not_id_ref)
                        VALUES (:user,:kind,'media','QA MIGRACION','HISTORIA SINTETICA',:read,
                                CURRENT_TIMESTAMP,false,NULL,NULL) RETURNING not_id
                    """), {"user": synthetic_recipient.user_id, "kind": kind, "read": read}).scalar_one())
                migration.upgrade()
            data = connection.execute(text("""
                SELECT not_id,not_leida,not_resuelta,not_duplicada_de_id,not_motivo_cierre,
                       not_revision,not_escritorio_revision_reclamada,not_tipo
                FROM notificacion WHERE usu_id=:user ORDER BY not_id
            """), {"user": synthetic_recipient.user_id}).all()
            assert len(data) == 2
            assert tuple(data[0]) == (rows[0], True, False, None, None, 1, 1, "SISTEMA")
            assert tuple(data[1]) == (rows[1], False, True, rows[0], "DUPLICADA", 1, 1, "SISTEMA")
            assert connection.execute(text("""
                SELECT count(*) FROM auditoria_sistema WHERE aud_accion_funcional='CIERRE_DUPLICADA'
                AND aud_id_registro=:id
            """), {"id": str(rows[1])}).scalar_one() == 1
        finally:
            # DDL, repair rows and audits are rolled back, including on failure.
            transaction.rollback()
