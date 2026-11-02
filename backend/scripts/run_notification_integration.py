"""Run PostgreSQL integration only against the explicitly provisioned test cluster.

No server is created or started by this runner. Credentials are supplied by its
parent process, never loaded from the ERP .env or written to logs.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

BACKEND = Path(__file__).resolve().parents[1]


def validated_configuration():
    from sqlalchemy.engine import make_url

    manifest_path = os.environ.get('TEST_PG_MANIFEST')
    if not manifest_path:
        raise ValueError('TEST_PG_MANIFEST is required; no business configuration fallback.')
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8-sig'))
    expected_data = Path(os.environ['LOCALAPPDATA']) / 'BAB_VDOS' / 'postgresql-testing' / 'data'
    if Path(manifest['data_directory']).resolve() != expected_data.resolve():
        raise ValueError('Unexpected test data directory.')
    if (manifest.get('host'), manifest.get('port'), manifest.get('database')) != ('127.0.0.1', 55432, 'bab_vdos_testing'):
        raise ValueError('Unexpected test instance identity.')
    urls = {}
    for variable, role in (('TEST_DATABASE_URL', 'bab_test_runner'), ('TEST_MIGRATION_DATABASE_URL', 'bab_test_migrator')):
        raw = os.environ.get(variable)
        if not raw:
            raise ValueError(f'{variable} is required.')
        url = make_url(raw)
        if (url.drivername, url.host, url.port, url.database, url.username) != ('postgresql+psycopg2', '127.0.0.1', 55432, 'bab_vdos_testing', role):
            raise ValueError('Rejected connection target or role.')
        if url.query or not url.password:
            raise ValueError('Connection options or missing credentials are not allowed.')
        urls[variable] = raw
    return manifest, urls


def run_child(rebuild_rag_chat=False) -> int:
    manifest, urls = validated_configuration()
    import psycopg2
    from psycopg2.extensions import parse_dsn
    from sqlalchemy import create_engine, event, text
    from sqlalchemy.engine import Engine

    violations = []
    original_connect = psycopg2.connect

    def check_connection(parameters):
        identity = (parameters.get('host'), str(parameters.get('port')), parameters.get('dbname', parameters.get('database')), parameters.get('user'))
        if identity[:3] != ('127.0.0.1', '55432', 'bab_vdos_testing') or identity[3] not in {'bab_test_runner', 'bab_test_migrator'}:
            violations.append('unapproved PostgreSQL target')
            raise RuntimeError('Integration blocked a connection outside the dedicated test database.')
        if any(key in parameters for key in ('service', 'servicefile', 'passfile', 'hostaddr')):
            raise RuntimeError('Integration connection indirection is not allowed.')

    def guarded_connect(dsn=None, *args, **kwargs):
        parameters = parse_dsn(dsn or '')
        parameters.update(kwargs)
        check_connection(parameters)
        return original_connect(dsn, *args, **kwargs)

    def guard_engine(_dialect, _record, args, parameters):
        combined = parse_dsn(args[0]) if args else {}
        combined.update(parameters)
        check_connection(combined)

    psycopg2.connect = guarded_connect
    event.listen(Engine, 'do_connect', guard_engine)
    for variable in ('TEST_MIGRATION_DATABASE_URL', 'TEST_DATABASE_URL'):
        engine = create_engine(urls[variable])
        try:
            with engine.connect() as connection:
                identity = connection.execute(text('SELECT instance_id FROM testing_control.instance')).scalar_one()
                if identity != manifest['instance_id']:
                    raise RuntimeError('Test instance marker mismatch.')
                if connection.execute(text('SELECT current_database()')).scalar_one() != manifest['database']:
                    raise RuntimeError('Database identity mismatch.')
                if variable == 'TEST_MIGRATION_DATABASE_URL':
                    actual = connection.execute(text('SHOW data_directory')).scalar_one()
                    if Path(actual).resolve() != Path(manifest['data_directory']).resolve():
                        raise RuntimeError('PostgreSQL data directory mismatch.')
        finally:
            engine.dispose()

    os.environ['TEST_PG_VALIDATED_INSTANCE'] = manifest['instance_id']
    # Settings are first imported after verification, never from the ERP CWD.
    from app.core.config import settings
    from alembic import command
    from alembic.config import Config
    configuration = Config(str(BACKEND / 'alembic.ini'))
    configuration.set_main_option('script_location', str(BACKEND / 'alembic'))
    settings.database_url = urls['TEST_MIGRATION_DATABASE_URL']
    try:
        if rebuild_rag_chat:
            command.downgrade(configuration,'20261019_0020')
        command.upgrade(configuration, 'head')
    finally:
        settings.database_url = urls['TEST_DATABASE_URL']

    # Tables are owned by the migration role; runtime tests receive DML only.
    engine = create_engine(urls['TEST_MIGRATION_DATABASE_URL'])
    try:
        with engine.begin() as connection:
            connection.execute(text('GRANT USAGE ON SCHEMA public TO bab_test_runner'))
            connection.execute(text('GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO bab_test_runner'))
            connection.execute(text('GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO bab_test_runner'))
            connection.execute(text('GRANT USAGE ON SCHEMA leny TO bab_test_runner'))
            connection.execute(text('GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA leny TO bab_test_runner'))
    finally:
        engine.dispose()

    import smtplib
    import pytest
    from app.core.permissions import build_policy_lines
    from app.services import seed_service

    def forbidden(*_args, **_kwargs):
        violations.append('external SMTP/process operation')
        raise RuntimeError('External operations are disabled during integration tests.')

    smtplib.SMTP = forbidden
    smtplib.SMTP_SSL = forbidden

    def audit(event_name, _arguments):
        if event_name in {'subprocess.Popen', 'os.system', 'os.exec', 'os.posix_spawn'}:
            forbidden()
    sys.addaudithook(audit)

    def verify_policy():
        if (BACKEND / 'app/security/policy.csv').read_text(encoding='utf-8') != '\n'.join(build_policy_lines()) + '\n':
            raise RuntimeError('Policy drift; integration will not rewrite repository files.')
    seed_service.sync_policy_file = verify_policy
    verify_policy()

    class Guard:
        @pytest.hookimpl(trylast=True)
        def pytest_sessionfinish(self, session, exitstatus):
            if violations:
                session.exitstatus = pytest.ExitCode.TESTS_FAILED

    return int(pytest.main([
        '-c', str(BACKEND.parent / 'pytest.ini'), '--confcutdir', str(BACKEND / 'tests'),
        '--basetemp', str(Path.cwd() / 'pytest-tmp'), '-q', '-p', 'no:cacheprovider',
        str(BACKEND / 'tests/integration'),
    ], plugins=[Guard()]))


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rebuild-rag-chat',action='store_true',help='Explicit isolated-only reapplication of the unpublished0021 migration; guards reject publications/sources/uncertain inference.')
    arguments=parser.parse_args()
    try:
        _manifest, urls = validated_configuration()
    except (ValueError, KeyError, OSError):
        print('Integration configuration rejected. A dedicated authorized test cluster and explicit manifest/credentials are required.', file=sys.stderr)
        return 2
    # Reuse the base runner allowlist, then explicitly supply only test settings.
    from run_base_tests import _child_environment
    with TemporaryDirectory(prefix='bab-vdos-notification-integration-') as temporary:
        environment = _child_environment(temporary)
        environment.update(urls)
        environment['DATABASE_URL'] = urls['TEST_DATABASE_URL']
        environment['TEST_PG_MANIFEST'] = str(Path(os.environ['TEST_PG_MANIFEST']).resolve())
        environment['ENVIRONMENT'] = 'test'
        bootstrap = "import runpy,sys; m=runpy.run_path(sys.argv[1]); raise SystemExit(m['run_child'](sys.argv[2]=='true'))"
        completed = subprocess.run([sys.executable, '-B', '-c', bootstrap, str(Path(__file__).resolve()),str(arguments.rebuild_rag_chat).lower()], cwd=temporary, env=environment, check=False)
        return completed.returncode


if __name__ == '__main__':
    raise SystemExit(main())
