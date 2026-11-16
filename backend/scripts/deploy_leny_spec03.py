"""Explicit, backed-up 0024 -> 0025 deployment; never run at application startup.

Read-only target/revision check by default. --apply requires operational
authorization, an idle inference lease and a verified private checkpoint.
Does not restart services, change profiles of existing chats or alter .env.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
PREVIOUS = '20261105_0024'
TARGET = '20261105_0025'


def fingerprints(db):
    """Protect original business/document rows, ignoring additive chat fields."""
    from sqlalchemy import text
    names = db.execute(text("SELECT schemaname,tablename FROM pg_tables WHERE "
        "(schemaname='public' AND tablename NOT IN ('alembic_version','sesion_cuenta','auth_login_bucket')) "
        "OR (schemaname='leny' AND tablename IN ('conversaciones','mensajes','documentos','documento_versiones',"
        "'documento_roles_lectura','carpeta_roles_lectura','rag_indexaciones','rag_fragmentos','rag_embeddings')) ORDER BY 1,2")).all()
    result = {}
    quote = db.dialect.identifier_preparer.quote
    for schema, table in names:
        value = "to_jsonb(t)-'llm_provider'-'llm_model'-'quality_profile'" if (schema, table) == ('leny', 'conversaciones') else 'to_jsonb(t)'
        row = db.execute(text(f"SELECT count(*),md5(coalesce(string_agg(h,'' ORDER BY h),'')) FROM "
            f"(SELECT md5(({value})::text) h FROM {quote(schema)}.{quote(table)} t) h")).one()
        result[schema + '.' + table] = list(row)
    return result


def schema_signature(db):
    """Only the expected column/CHECK may differ, in the LENY schema."""
    from sqlalchemy import text
    columns = db.execute(text("SELECT table_schema,table_name,column_name,data_type,is_nullable,column_default "
        "FROM information_schema.columns WHERE table_schema IN ('public','leny') AND NOT "
        "(table_schema='leny' AND table_name='conversaciones' AND column_name='quality_profile') ORDER BY 1,2,3")).all()
    constraints = db.execute(text("SELECT n.nspname,c.relname,k.conname,pg_get_constraintdef(k.oid) "
        "FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace "
        "WHERE n.nspname IN ('public','leny') AND NOT (n.nspname='leny' AND c.relname='conversaciones' "
        "AND k.conname='ck_leny_conversation_quality_profile') ORDER BY 1,2,3")).all()
    return hashlib.sha256(json.dumps([list(map(list, columns)), list(map(list, constraints))], sort_keys=True).encode()).hexdigest()


def checkpoint_directory():
    root = (Path(os.environ['LOCALAPPDATA']) / 'BAB_VDOS/leny-spec03').resolve()
    private = Path((root / 'active.txt').read_text(encoding='utf-8-sig').strip()).resolve()
    if private == root or not private.is_relative_to(root) or not private.is_dir():
        raise RuntimeError('An existing private SPEC03 checkpoint is required.')
    from app.services.leny_document_storage import _check_path, protect_directory
    _check_path(private)
    protect_directory(private)
    return private


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    os.chdir(BACKEND)
    from app.core.config import Settings, settings
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url
    from sqlalchemy.orm import sessionmaker
    config = Settings(_env_file=BACKEND / '.env')
    url = make_url(config.effective_database_url)
    if not (url.host in ('127.0.0.1', 'localhost') and (url.port or 5432) == 5432 and url.database == 'bellaarte_db'):
        raise RuntimeError('Deployment is restricted to the reviewed original database.')
    if make_url(settings.effective_database_url) != url:
        raise RuntimeError('Runtime and migration destinations differ.')
    engine = create_engine(url, hide_parameters=True)
    coordinator = lease = None
    report = None
    private = None

    def record():
        if report is not None and private is not None:
            (private / 'deployment.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

    try:
        with engine.connect() as db:
            revision = db.scalar(text('SELECT version_num FROM alembic_version'))
        print('Target bellaarte_db:5432; revision', revision, flush=True)
        if not args.apply:
            return
        if revision != PREVIOUS:
            raise RuntimeError('Expected previous revision 0024; no migration attempted.')
        private = checkpoint_directory()
        report = dict(revision_before=revision, revision_after=None,
            started_at=datetime.now(timezone.utc).isoformat(), business_restore_executed=False,
            status='preparing', google_calls=0, configuration_changed=False, backend_restarted=False)
        record()
        from app.services.leny_coordination import PostgresCoordinator
        from app.core.backup_runtime import backup_lock
        from app.services.leny_document_storage import DocumentStorage, protect_directory
        from app.services.leny_document_backup import freeze_library, build_bundle, verify_bundle
        coordinator = PostgresCoordinator(config.effective_database_url)
        lease = coordinator.acquire()
        with backup_lock({'operation': 'LENY_SPEC03_0025'}):
            with engine.connect() as db:
                assert not db.scalar(text("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid() AND backend_type='client backend' AND state='active'")), 'Another operation is active.'
                assert not db.scalar(text("SELECT count(*) FROM leny.rag_trabajos WHERE status IN ('queued','running')")), 'Document work is pending.'
                assert db.scalar(text('SELECT version_num FROM alembic_version')) == PREVIOUS
                assert not db.scalar(text("SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_schema='leny' AND table_name='conversaciones' AND column_name='quality_profile')"))
                before = fingerprints(db)
                schema_before = schema_signature(db)
            storage = DocumentStorage(config)
            storage.initialize()
            destination = storage.root / 'backups'
            destination.mkdir(parents=True, exist_ok=True)
            protect_directory(destination)
            dump = destination / ('leny-spec03-before-0025-' + uuid4().hex + '.dump')
            bundle = dump.with_suffix('.zip')
            binaries = Path(r'C:\laragon\bin\postgresql\postgresql-17.9-1\bin')
            env = {key: value for key, value in os.environ.items() if not key.upper().startswith('PG')}
            env.update(PGPASSWORD=url.password or '', PGCONNECT_TIMEOUT='5')
            with freeze_library(config):
                with (private / 'backup-errors.log').open('wb') as errors:
                    subprocess.run([str(binaries / 'pg_dump.exe'), '-h', url.host, '-p', '5432', '-U', url.username,
                        '-d', 'bellaarte_db', '-Fc', '-f', str(dump)], env=env, stderr=errors,
                        stdout=subprocess.DEVNULL, check=True, timeout=180)
                    subprocess.run([str(binaries / 'pg_restore.exe'), '--list', str(dump)], stderr=errors,
                        stdout=subprocess.DEVNULL, check=True, timeout=60)
                    subprocess.run([str(binaries / 'pg_restore.exe'), '--file', os.devnull, str(dump)], stderr=errors,
                        stdout=subprocess.DEVNULL, check=True, timeout=180)
                build_bundle(dump, bundle, sessionmaker(engine), storage)
                assert verify_bundle(bundle)['alembic_revision'] == PREVIOUS
            report.update(backup_path=str(bundle), backup_sha256=hashlib.sha256(bundle.read_bytes()).hexdigest(),
                backup_bytes=bundle.stat().st_size, backup_verified=True, fingerprints_before=before,
                schema_signature_before=schema_before, status='backed_up')
            record()
            lease.check()
            from alembic import command
            from alembic.config import Config
            configuration = Config(str(BACKEND / 'alembic.ini'))
            configuration.set_main_option('script_location', str(BACKEND / 'alembic'))
            previous_options = os.environ.get('PGOPTIONS')
            try:
                os.environ['PGOPTIONS'] = '-c lock_timeout=5000 -c statement_timeout=30000'
                command.upgrade(configuration, TARGET)
            finally:
                if previous_options is None:
                    os.environ.pop('PGOPTIONS', None)
                else:
                    os.environ['PGOPTIONS'] = previous_options
            with engine.connect() as db:
                report['revision_after'] = db.scalar(text('SELECT version_num FROM alembic_version'))
                after = fingerprints(db)
                report['tables_changed'] = sorted(key for key in set(before) | set(after) if before.get(key) != after.get(key))
                report['schema_signature_after'] = schema_signature(db)
                report['nonbaseline_existing_chats'] = db.scalar(text("SELECT count(*) FROM leny.conversaciones WHERE quality_profile<>'baseline' OR quality_profile IS NULL"))
                column = db.execute(text("SELECT data_type,is_nullable,column_default FROM information_schema.columns WHERE table_schema='leny' AND table_name='conversaciones' AND column_name='quality_profile'")).one()
                report['profile_column'] = list(column)
                report['profile_check_present'] = bool(db.scalar(text("SELECT EXISTS(SELECT 1 FROM pg_constraint WHERE conrelid='leny.conversaciones'::regclass AND conname='ck_leny_conversation_quality_profile')")))
            record()
            assert report['revision_after'] == TARGET and not report['tables_changed']
            assert report['schema_signature_after'] == schema_before
            assert report['nonbaseline_existing_chats'] == 0
            assert report['profile_column'][0:2] == ['character varying', 'NO']
            assert 'baseline' in report['profile_column'][2] and report['profile_check_present']
            report.update(status='applied_verified', completed_at=datetime.now(timezone.utc).isoformat())
            record()
            print('0025 applied; private backup verified; original rows/schema preserved; historical chats baseline.', flush=True)
    except BaseException as error:
        if report is not None:
            report.update(status='failed_requires_review', error_type=type(error).__name__)
            record()
        raise
    finally:
        if lease is not None:
            lease.close()
        if coordinator is not None:
            coordinator.engine.dispose()
        engine.dispose()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Keep connection details and SQL/record values out of the console.
        print('Deployment stopped:', type(error).__name__, '; review the private checkpoint.', file=sys.stderr)
        sys.exit(1)
