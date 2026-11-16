"""Transactional 0024/ledger checks on the identified existing PG55432 only."""
import importlib.util
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from alembic.migration import MigrationContext
from alembic.operations import Operations

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BACKEND))


def main():
    url = make_url(os.environ['TEST_MIGRATION_DATABASE_URL'])
    assert (url.host,url.port,url.database,url.username)==('127.0.0.1',55432,'bab_vdos_testing','bab_test_migrator')
    manifest = json.loads(Path(os.environ['TEST_PG_MANIFEST']).read_text(encoding='utf-8-sig'))
    engine = create_engine(url,hide_parameters=True)
    spec = importlib.util.spec_from_file_location('gemini0024',BACKEND/'alembic/versions/20261105_0024_leny_conversation_providers.py')
    migration = importlib.util.module_from_spec(spec);spec.loader.exec_module(migration)
    checks = []
    with engine.connect() as db:
        transaction = db.begin()
        try:
            assert db.scalar(text('SELECT instance_id FROM testing_control.instance'))==manifest['instance_id']
            assert Path(db.scalar(text('SHOW data_directory'))).resolve()==Path(manifest['data_directory']).resolve()
            assert db.scalar(text("SELECT count(*) FROM information_schema.columns WHERE table_schema='leny' AND table_name='conversaciones' AND column_name='llm_provider'"))==0
            migration.op = Operations(MigrationContext.configure(db))
            unknown = db.scalar(text("SELECT EXISTS(SELECT 1 FROM leny.mensajes WHERE role='assistant' AND (model IS NULL OR model<>'qwen3.5:4b-q4_K_M'))"))
            if unknown:
                try: migration.upgrade()
                except RuntimeError: checks.append('unknown_synthetic_models_rejected')
                else: raise AssertionError('Unknown models accepted')
                # Synthetic cluster only, rolled back with the outer transaction.
                # Exercise the positive branch without changing production data.
                db.execute(text("UPDATE leny.mensajes SET model='qwen3.5:4b-q4_K_M' WHERE role='assistant'"))
            migration.upgrade()
            checks.append('upgrade0024')
            columns=db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_schema='leny' AND table_name='conversaciones'")).scalars().all()
            assert 'llm_provider' in columns and 'llm_model' in columns
            checks.append('provider_columns')
            from app.services.leny_gemini_usage import GeminiUsage
            from app.services.leny_llm_contracts import LenyError
            usage=GeminiUsage(sessionmaker(bind=db,join_transaction_mode='create_savepoint'),
                SimpleNamespace(leny_gemini_rpm=15,leny_gemini_tpm=250000,leny_gemini_rpd=500))
            for _ in range(15):
                identity=usage.reserve('synthetic',100)
                usage.finish(identity,metrics=dict(prompt_eval_count=40,eval_count=10,thinking_tokens=20))
            try:usage.reserve('synthetic',100)
            except LenyError as error:assert error.code=='LENY_GEMINI_QUOTA'
            else:raise AssertionError('RPM not enforced')
            assert db.scalar(text('SELECT count(*) FROM leny.gemini_requests'))==15
            checks.append('durable_rpm_fifteen_including_all_phases')
            db.execute(text('DELETE FROM leny.gemini_requests'))
            identity=usage.reserve('synthetic',249999)
            try:usage.reserve('synthetic',2)
            except LenyError:pass
            else:raise AssertionError('TPM not enforced')
            checks.append('tpm_reservation')
            db.execute(text('DELETE FROM leny.gemini_requests'))
            assert usage.block_daily()>0
            try:usage.reserve('synthetic',1)
            except LenyError as error:assert error.retry_after>60
            else:raise AssertionError('Daily hold not enforced')
            checks.append('daily_provider_exhaustion')
            db.execute(text('DELETE FROM leny.gemini_requests'))
            # All attempts remain chargeable, including HTTP failures. The
            # Owner-supplied 3.1 Flash-Lite quota: 500 daily attempts.
            for _ in range(500):
                db.execute(text("INSERT INTO leny.gemini_requests(id,phase,reserved_tokens,status) "
                                "VALUES(:id,'synthetic',1,'failed')"),{'id':uuid4()})
            try:usage.reserve('synthetic',1)
            except LenyError as error:assert error.code=='LENY_GEMINI_QUOTA' and error.retry_after>60
            else:raise AssertionError('501st daily attempt was accepted')
            checks.append('daily_five_hundred_including_failed_attempts')
            db.execute(text('DELETE FROM leny.gemini_requests'))
            migration.downgrade()
            checks.append('safe_downgrade_before_use')
        finally:
            transaction.rollback()
        assert db.scalar(text("SELECT to_regclass('leny.gemini_requests')")) is None
        checks.append('all_schema_and_rows_rolled_back')
    engine.dispose()
    report=dict(checks=checks,google_calls=0,production_database_used=False,committed_schema_changes=False)
    Path(sys.argv[1]).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('Isolated schema/ledger checks passed:',len(checks))


if __name__=='__main__':main()
