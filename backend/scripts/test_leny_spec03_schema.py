"""0025 integration checks on the verified PG55432 cluster, wholly rolled back.

No application startup, Google call, production connection, or committed DDL.
The companion PowerShell runner supplies the existing cluster's DPAPI secrets.
"""
import importlib.util
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID, uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


def migration(filename, name, connection):
    spec = importlib.util.spec_from_file_location(name, BACKEND / 'alembic/versions' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.op = Operations(MigrationContext.configure(connection))
    return module


def main():
    url = make_url(os.environ['TEST_MIGRATION_DATABASE_URL'])
    if (url.host, url.port, url.database, url.username) != ('127.0.0.1', 55432, 'bab_vdos_testing', 'bab_test_migrator'):
        raise RuntimeError('Only the identified isolated migration database is allowed.')
    manifest = json.loads(Path(os.environ['TEST_PG_MANIFEST']).read_text(encoding='utf-8-sig'))
    engine = create_engine(url, hide_parameters=True)
    checks = []
    try:
        with engine.connect() as db:
            outer = db.begin()
            try:
                assert db.scalar(text('SELECT instance_id FROM testing_control.instance')) == manifest['instance_id']
                assert Path(db.scalar(text('SHOW data_directory'))).resolve() == Path(manifest['data_directory']).resolve()
                revision = db.scalar(text('SELECT version_num FROM alembic_version'))
                assert revision in {'20261020_0021', '20261104_0023'}
                original_count = db.scalar(text('SELECT count(*) FROM leny.conversaciones'))
                assert not db.scalar(text("SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_schema='leny' AND table_name='conversaciones' AND column_name IN ('llm_provider','quality_profile'))"))
                provider = migration('20261105_0024_leny_conversation_providers.py', 'provider0024', db)
                # Existing isolated synthetic assistant fixtures use fake model
                # names. Normalize only within this never-committed transaction.
                db.execute(text("UPDATE leny.mensajes SET model='qwen3.5:4b-q4_K_M' WHERE role='assistant' AND (model IS NULL OR model<>'qwen3.5:4b-q4_K_M')"))
                provider.upgrade()
                profile = migration('20261105_0025_leny_quality_profile.py', 'profile0025', db)
                profile.upgrade()
                checks.append('upgrade0024_then0025_inside_outer_rollback')
                assert db.scalar(text("SELECT count(*) FROM leny.conversaciones WHERE quality_profile<>'baseline' OR quality_profile IS NULL")) == 0
                checks.append('all_historical_conversations_default_baseline')

                accounts = db.execute(text('SELECT id,usuario_id FROM public.cuentas ORDER BY id LIMIT 2')).all()
                assert len(accounts) == 2, 'Two existing isolated fixture accounts are required.'
                from app.services.leny_store import LenyActor, LenyStore
                from app.services.leny_llm_contracts import LenyError
                from app.services.leny_gemini_usage import GeminiUsage
                sessions = sessionmaker(bind=db, join_transaction_mode='create_savepoint')
                quota_config = SimpleNamespace(leny_gemini_rpm=15, leny_gemini_tpm=250000,
                    leny_gemini_rpd=500, leny_spec03_evaluation_daily_calls=2)
                evaluation = GeminiUsage(sessions, quota_config, evaluation=True)
                for _ in range(2):
                    evaluation.reserve('synthetic', 1)
                try:
                    evaluation.reserve('synthetic', 1)
                except LenyError as error:
                    assert error.code == 'LENY_EVALUATION_QUOTA'
                else:
                    raise AssertionError('Third evaluation request was accepted.')
                assert db.scalar(text('SELECT count(*) FROM leny.gemini_requests')) == 2
                GeminiUsage(sessions, quota_config).reserve('synthetic', 1)
                assert db.scalar(text("SELECT count(*) FROM leny.gemini_requests WHERE left(phase,5)='eval_'")) == 2
                assert db.scalar(text('SELECT count(*) FROM leny.gemini_requests')) == 3
                checks.append('evaluation_two_attempt_cap_without_rejected_reservation_or_regular_block')
                actor = LenyActor(accounts[0].id, accounts[0].usuario_id, str(uuid4()))
                other = LenyActor(accounts[1].id, accounts[1].usuario_id, str(uuid4()))
                store = LenyStore(sessions)
                # Isolate the store contract from the unrelated general audit
                # writer. SQL persistence, owner filtering and CHECKs are real.
                with patch.object(store, 'audit'):
                    baseline = store.create(actor)
                    candidate = store.create(actor, quality_profile='spec03')
                base_id, candidate_id = UUID(baseline['id']), UUID(candidate['id'])
                assert baseline['quality_profile'] == 'baseline'
                assert candidate['quality_profile'] == 'spec03'
                assert store.quality_profile_for(actor, base_id) == 'baseline'
                assert store.quality_profile_for(actor, candidate_id) == 'spec03'
                assert store.provider_for(actor, candidate_id) == ('ollama', 'qwen3.5:4b-q4_K_M')
                checks.append('real_store_default_explicit_profile_and_unchanged_provider_tuple')
                for getter in (store.quality_profile_for, store.provider_for):
                    try:
                        getter(other, candidate_id)
                    except LenyError as error:
                        assert error.code == 'LENY_NOT_FOUND'
                    else:
                        raise AssertionError('Another owner accessed the conversation.')
                checks.append('owner_scoped_profile_and_provider_getters')
                try:
                    with db.begin_nested():
                        db.execute(text('UPDATE leny.conversaciones SET quality_profile=:profile WHERE id=:id'), {'profile': 'invalid', 'id': base_id})
                except IntegrityError as error:
                    assert error.orig.diag.constraint_name == 'ck_leny_conversation_quality_profile'
                else:
                    raise AssertionError('Invalid profile accepted by PostgreSQL.')
                checks.append('invalid_profile_database_check')
                try:
                    profile.downgrade()
                except RuntimeError:
                    pass
                else:
                    raise AssertionError('Downgrade discarded a used SPEC03 profile.')
                assert store.quality_profile_for(actor, candidate_id) == 'spec03'
                checks.append('downgrade_guard_preserves_spec03_conversation')
                # Exercise the safe branch after deleting only our own fixture.
                db.execute(text('DELETE FROM leny.conversaciones WHERE id=:id'), {'id': candidate_id})
                profile.downgrade()
                checks.append('unused_profile_safe_downgrade')
            finally:
                outer.rollback()
            assert db.scalar(text('SELECT count(*) FROM leny.conversaciones')) == original_count
            assert db.scalar(text('SELECT version_num FROM alembic_version')) == revision
            assert not db.scalar(text("SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_schema='leny' AND table_name='conversaciones' AND column_name IN ('llm_provider','quality_profile'))"))
            assert db.scalar(text("SELECT to_regclass('leny.gemini_requests')")) is None
            checks.append('all_schema_rows_and_revision_rolled_back')
    finally:
        engine.dispose()
    report = dict(checks=checks, google_calls=0, production_database_used=False,
                  committed_schema_changes=False, audit_mocked=True)
    Path(sys.argv[1]).write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('Isolated SPEC03 schema/store checks passed:', len(checks))


if __name__ == '__main__':
    main()
