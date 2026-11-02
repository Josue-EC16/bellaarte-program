"""Serve the real ERP on loopback against the existing isolated test database.

Use start_leny_smoke.ps1. Never reads the ERP .env, migrates, provisions, or seeds.
The password must be supplied through LENY_SMOKE_PASSWORD, never a CLI argument.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
import secrets
import subprocess
import sys
from tempfile import TemporaryDirectory
from uuid import UUID, uuid4

BACKEND = Path(__file__).resolve().parents[1]


def cleanup_user(engine, username: str, created_role_id: int | None = None) -> None:
    """Remove only a specifically named, verified synthetic smoke identity."""
    from sqlalchemy import text
    if re.fullmatch(r'leny_smoke_[0-9a-f]{12}', username) is None:
        raise RuntimeError('Cleanup requires the exact synthetic smoke username.')
    with engine.begin() as connection:
        identity = connection.execute(text('''
            SELECT c.id AS account_id,u.id AS user_id,u.nombres,u.apellido_paterno,u.correo,u.ci
            FROM cuentas c JOIN usuarios u ON u.id=c.usuario_id
            WHERE c.username=:name FOR UPDATE OF c,u
        '''), {'name': username}).one_or_none()
        if identity is None:
            print('No matching synthetic smoke identity remains.', flush=True)
            return
        suffix = username.removeprefix('leny_smoke_')
        email_token = identity.correo.removesuffix('@example.invalid')
        if (identity.nombres != 'QA LENY' or identity.apellido_paterno != 'SMOKE'
                or not identity.correo.endswith('@example.invalid')
                or re.fullmatch(r'[0-9a-f]{32}', email_token) is None
                or not email_token.startswith(suffix) or identity.ci != email_token[:25]):
            raise RuntimeError('Cleanup identity does not match the synthetic smoke signature.')
        user_id, account_id = identity.user_id, identity.account_id
        # Document smoke uses the same disposable person. Only its own library
        # objects may be removed; physical files live in the owned smoke temp.
        documents = connection.execute(text('SELECT id FROM leny.documentos WHERE created_by=:id'), {'id':user_id}).scalars().all()
        for document_id in documents:
            connection.execute(text('DELETE FROM leny.documento_versiones WHERE document_id=:id'), {'id':document_id})
            connection.execute(text('DELETE FROM leny.documentos WHERE id=:id'), {'id':document_id})
        connection.execute(text('DELETE FROM leny.documento_operaciones WHERE user_id=:id'), {'id':user_id})
        connection.execute(text('DELETE FROM leny.carpeta_roles_lectura WHERE folder_id IN (SELECT id FROM leny.carpetas WHERE created_by=:id)'), {'id':user_id})
        connection.execute(text('UPDATE leny.carpetas SET parent_id=NULL WHERE created_by=:id'), {'id':user_id})
        connection.execute(text('DELETE FROM leny.carpetas WHERE created_by=:id'), {'id':user_id})
        evidence = connection.execute(text('''
            SELECT
              (SELECT count(*) FROM leny.conversaciones WHERE user_id=:user) AS conversations,
              (SELECT count(*) FROM leny.mensajes m JOIN leny.conversaciones c ON c.id=m.conversation_id WHERE c.user_id=:user) AS messages,
              (SELECT count(*) FROM auditoria_sistema WHERE usu_id=:user AND aud_modulo='LENY') AS leny_audits,
              (SELECT count(*) FROM auditoria_sistema WHERE usu_id=:user AND aud_modulo='LENY'
                AND aud_submodulo IS DISTINCT FROM 'DOCUMENTOS'
                AND (aud_campo IS NOT NULL OR aud_valor_anterior IS NOT NULL OR aud_valor_nuevo IS NOT NULL
                     OR aud_descripcion IS DISTINCT FROM replace(aud_accion_funcional,'_',' '))) AS unexpected_audit_payloads,
              (SELECT count(*) FROM pg_locks WHERE locktype='advisory'
                AND database=(SELECT oid FROM pg_database WHERE datname=current_database())
                AND classid=:high AND objid=:low AND objsubid=1) AS generation_locks
        '''), {'user': user_id, 'high': 0x4C454E590001 >> 32, 'low': 0x4C454E590001 & 0xFFFFFFFF}).one()
        print('Synthetic smoke evidence: conversations={0}, messages={1}, leny_audits={2}, '
              'unexpected_audit_payloads={3}, generation_locks={4}'.format(*evidence), flush=True)
        connection.execute(text('DELETE FROM leny.conversaciones WHERE user_id=:id'), {'id': user_id})
        connection.execute(text('DELETE FROM leny.admissions WHERE user_id=:id'), {'id': user_id})
        connection.execute(text('DELETE FROM leny.rate_users WHERE user_id=:id'), {'id': user_id})
        connection.execute(text('UPDATE notificacion SET not_duplicada_de_id=NULL WHERE usu_id=:id'), {'id': user_id})
        connection.execute(text('DELETE FROM notificacion WHERE usu_id=:id'), {'id': user_id})
        connection.execute(text('DELETE FROM preferencia_notificacion WHERE usuario_id=:id'), {'id': user_id})
        connection.execute(text('DELETE FROM envio_notificacion_correo WHERE cuenta_id=:id'), {'id': account_id})
        connection.execute(text('DELETE FROM auditoria_sistema WHERE usu_id=:id'), {'id': user_id})
        connection.execute(text('DELETE FROM cuentas WHERE id=:id AND usuario_id=:user'), {'id': account_id, 'user': user_id})
        connection.execute(text('DELETE FROM usuarios WHERE id=:id'), {'id': user_id})
        if created_role_id is not None:
            connection.execute(text('DELETE FROM roles WHERE id=:id AND NOT EXISTS(SELECT 1 FROM cuentas WHERE rol_id=:id)'), {'id': created_role_id})
    print('LENY smoke synthetic identity and history removed.', flush=True)


def run_child() -> int:
    from run_notification_integration import validated_configuration
    manifest, urls = validated_configuration()
    UUID(manifest['instance_id'])
    if Path.cwd().resolve().is_relative_to(BACKEND.parent) or (Path.cwd() / '.env').exists():
        raise RuntimeError('Smoke must run from its owned temporary directory.')
    if os.environ.get('DATABASE_URL') != urls['TEST_DATABASE_URL'] or any(key.startswith('DB_') for key in os.environ):
        raise RuntimeError('Smoke application configuration is not isolated.')
    password = os.environ.pop('LENY_SMOKE_PASSWORD', '')
    cleanup_username = os.environ.pop('LENY_SMOKE_CLEANUP_USERNAME', '')
    if not cleanup_username and (len(password) < 12 or len(password.encode('utf-8')) > 72):
        raise RuntimeError('A synthetic password of 12 to 72 UTF-8 bytes is required.')

    import psycopg2
    from psycopg2.extensions import parse_dsn
    from sqlalchemy import create_engine, event, text
    from sqlalchemy.engine import Engine

    original_connect = psycopg2.connect

    def check_target(parameters):
        identity = (parameters.get('host'), str(parameters.get('port')),
                    parameters.get('dbname', parameters.get('database')), parameters.get('user'))
        if identity[:3] != ('127.0.0.1', '55432', 'bab_vdos_testing') or identity[3] not in {'bab_test_runner', 'bab_test_migrator'}:
            raise RuntimeError('Smoke blocked a PostgreSQL target outside the isolated test instance.')
        if any(key in parameters for key in ('service', 'servicefile', 'passfile', 'hostaddr')):
            raise RuntimeError('PostgreSQL connection indirection is forbidden.')

    def guarded_connect(dsn=None, *args, **kwargs):
        parameters = parse_dsn(dsn or '')
        parameters.update(kwargs)
        check_target(parameters)
        return original_connect(dsn, *args, **kwargs)

    def guard_engine(_dialect, _record, args, parameters):
        combined = parse_dsn(args[0]) if args else {}
        combined.update(parameters)
        check_target(combined)

    psycopg2.connect = guarded_connect
    event.listen(Engine, 'do_connect', guard_engine)
    for variable in ('TEST_MIGRATION_DATABASE_URL', 'TEST_DATABASE_URL'):
        verification_engine = create_engine(urls[variable], hide_parameters=True)
        try:
            with verification_engine.connect() as connection:
                expected_role = 'bab_test_migrator' if variable == 'TEST_MIGRATION_DATABASE_URL' else 'bab_test_runner'
                actual = connection.execute(text('SELECT current_database(),current_user,inet_server_port()')).one()
                if tuple(actual) != ('bab_vdos_testing', expected_role, 55432):
                    raise RuntimeError('Isolated test server identity mismatch.')
                if connection.execute(text('SELECT instance_id FROM testing_control.instance')).scalars().all() != [manifest['instance_id']]:
                    raise RuntimeError('Isolated instance badge mismatch.')
                if variable == 'TEST_MIGRATION_DATABASE_URL':
                    actual_directory = connection.execute(text('SHOW data_directory')).scalar_one()
                    if Path(actual_directory).resolve() != Path(manifest['data_directory']).resolve():
                        raise RuntimeError('Isolated PostgreSQL data directory mismatch.')
                if connection.execute(text('SELECT version_num FROM public.alembic_version')).scalar_one() != '20261019_0019':
                    raise RuntimeError('Run the reviewed isolated migration tests before smoke.')
                if connection.execute(text("SELECT to_regclass('leny.mensajes')")).scalar_one() is None:
                    raise RuntimeError('Reviewed LENY storage is absent.')
        finally:
            verification_engine.dispose()
    # The application runs with the DML-only identity; migration credentials are
    # required only for the preceding directory/badge verification.
    os.environ.pop('TEST_MIGRATION_DATABASE_URL', None)
    urls.pop('TEST_MIGRATION_DATABASE_URL', None)
    if cleanup_username:
        cleanup_engine = create_engine(urls['TEST_DATABASE_URL'], hide_parameters=True)
        try:
            cleanup_user(cleanup_engine, cleanup_username)
        finally:
            cleanup_engine.dispose()
        return 0

    # Install all side-effect guards before importing the application.
    import smtplib

    def forbidden(*_args, **_kwargs):
        raise RuntimeError('External mail and process operations are disabled during smoke.')

    smtplib.SMTP = forbidden
    smtplib.SMTP_SSL = forbidden

    def process_guard(event_name, _arguments):
        if event_name == 'subprocess.Popen' and os.environ.get('LENY_DOCUMENTS_ENABLED') == 'true':
            executable, args, cwd, environment = _arguments
            expected = [sys.executable, '-B', '-I', str(BACKEND/'scripts/validate_leny_document.py')]
            if (executable in (None, sys.executable) and args in (expected, subprocess.list2cmdline(expected))
                    and Path(cwd).resolve() == (Path(os.environ['LENY_DOCUMENTS_ROOT'])/'staging').resolve()
                    and not any(key.startswith(('DB_', 'DATABASE_', 'SMTP_', 'JWT_')) for key in environment)):
                return
        if event_name in {'subprocess.Popen', 'os.system', 'os.exec', 'os.posix_spawn'}:
            forbidden()
    sys.addaudithook(process_guard)

    from app.core.permissions import build_policy_lines
    from app.services import seed_service

    def verify_policy_only():
        actual = (BACKEND / 'app/security/policy.csv').read_text(encoding='utf-8')
        if actual != '\n'.join(build_policy_lines()) + '\n':
            raise RuntimeError('Policy drift; smoke will never rewrite policy.csv.')

    seed_service.sync_policy_file = verify_policy_only
    verify_policy_only()
    from app.core.security import hash_password
    password_hash = hash_password(password)
    password = ''
    token = uuid4().hex
    username = 'leny_smoke_' + token[:12]
    engine = create_engine(urls['TEST_DATABASE_URL'], hide_parameters=True)
    user_id = account_id = created_role_id = None
    try:
        with engine.begin() as connection:
            created_role_id = connection.execute(text("""
                INSERT INTO roles(codigo,nombre,activo) VALUES('ADMIN','ADMIN',true)
                ON CONFLICT(codigo) DO NOTHING RETURNING id
            """)).scalar_one_or_none()
            role = connection.execute(text("SELECT id,activo FROM roles WHERE codigo='ADMIN'")).one()
            if not role.activo:
                raise RuntimeError('The isolated ADMIN role is disabled; smoke will not alter it.')
            user_id = connection.execute(text("""
                INSERT INTO usuarios(nombres,apellido_paterno,ci,celular,correo,zona,activo)
                VALUES('QA LENY','SMOKE',:ci,'00000000',:mail,'TEST',true) RETURNING id
            """), {'ci': token[:25], 'mail': token + '@example.invalid'}).scalar_one()
            account_id = connection.execute(text("""
                INSERT INTO cuentas(usuario_id,rol_id,username,password_hash,must_change_password,is_active)
                VALUES(:user,:role,:name,:hash,false,true) RETURNING id
            """), {'user': user_id, 'role': role.id, 'name': username, 'hash': password_hash}).scalar_one()
        print('LENY smoke: http://127.0.0.1:8001 ; frontend http://127.0.0.1:5174', flush=True)
        print('Synthetic username: ' + username, flush=True)
        print('Stop gracefully with Ctrl+C to remove only this smoke identity and its history.', flush=True)
        import uvicorn
        from app.main import app
        stop_file = os.environ.get('LENY_SMOKE_STOP_FILE')
        server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=8001, log_level='warning', access_log=False))
        if stop_file:
            import threading
            import time
            expected_root = Path(os.environ['LOCALAPPDATA'])/'BAB_VDOS/postgresql-testing/runtime'
            candidate = Path(stop_file).absolute()
            if candidate.parent != expected_root or not re.fullmatch(r'leny-smoke-[a-f0-9]{32}\.stop', candidate.name) or candidate.exists():
                raise RuntimeError('Smoke stop marker must be a fresh isolated runtime path')
            def watch_shutdown():
                while not server.should_exit:
                    if candidate.exists():
                        server.should_exit = True
                        break
                    time.sleep(0.25)
            threading.Thread(target=watch_shutdown,daemon=True).start()
            print('Graceful stop marker: '+str(candidate),flush=True)
        server.run()
        return 0
    finally:
        try:
            if account_id is not None:
                cleanup_user(engine, username, created_role_id)
        finally:
            engine.dispose()


def safe_child() -> int:
    try:
        return run_child()
    except KeyboardInterrupt:
        return 130
    except Exception:
        # Never print SQL bind values, hashes, URLs, or plaintext credentials.
        print('LENY smoke startup/cleanup failed safely; inspect isolated test prerequisites.', file=sys.stderr)
        return 2


def main() -> int:
    from run_notification_integration import validated_configuration
    _manifest, urls = validated_configuration()
    password = os.environ.get('LENY_SMOKE_PASSWORD', '')
    cleanup_username = os.environ.get('LENY_SMOKE_CLEANUP_USERNAME', '')
    if cleanup_username and re.fullmatch(r'leny_smoke_[0-9a-f]{12}', cleanup_username) is None:
        raise RuntimeError('Only an exact synthetic smoke username is accepted.')
    if not password and not cleanup_username:
        raise RuntimeError('LENY_SMOKE_PASSWORD is required.')
    from run_base_tests import _child_environment
    with TemporaryDirectory(prefix='bab-vdos-leny-smoke-') as temporary:
        environment = _child_environment(temporary)
        environment.update(urls)
        environment.update({
            'DATABASE_URL': urls['TEST_DATABASE_URL'],
            'TEST_PG_MANIFEST': str(Path(os.environ['TEST_PG_MANIFEST']).resolve()),
            'LENY_SMOKE_PASSWORD': password, 'FRONTEND_URL': 'http://127.0.0.1:5174',
            'LENY_SMOKE_CLEANUP_USERNAME': cleanup_username,
            'LENY_SMOKE_STOP_FILE': os.environ.get('LENY_SMOKE_STOP_FILE',''),
            'JWT_SECRET_KEY': secrets.token_hex(32), 'JWT_REFRESH_SECRET_KEY': secrets.token_hex(32),
            'LENY_ENABLED': 'true', 'LENY_OLLAMA_URL': 'http://127.0.0.1:11434',
            'LENY_MODEL': 'qwen3.5:4b-q4_K_M',
        })
        if os.environ.get('LENY_DOCUMENTS_SMOKE') == '1':
            environment.update(LENY_DOCUMENTS_ENABLED='true', LENY_DOCUMENTS_ROOT=str(Path(temporary)/'documents'),
                               LENY_DOCUMENTS_MIN_FREE_BYTES='0')
        # Expose sibling launcher imports without making CWD or .env public.
        environment['PYTHONPATH'] = str(BACKEND) + os.pathsep + str(BACKEND / 'scripts')
        bootstrap = "import runpy,sys; m=runpy.run_path(sys.argv[1]); raise SystemExit(m['safe_child']())"
        child = subprocess.Popen([sys.executable, '-B', '-c', bootstrap, str(Path(__file__).resolve())],
                                 cwd=temporary, env=environment)
        try:
            return child.wait()
        except KeyboardInterrupt:
            # Console Ctrl+C reaches Uvicorn too. Allow its request cancellation
            # and the identity-scoped cleanup to finish before stopping PG.
            try:
                child.wait(timeout=20)
            except subprocess.TimeoutExpired:
                print('Smoke shutdown exceeded 20s; synthetic cleanup requires inspection.', file=sys.stderr)
                child.terminate()
                child.wait(timeout=5)
            return 130


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, OSError, RuntimeError):
        print('LENY smoke refused unsafe/unavailable configuration; no production fallback.', file=sys.stderr)
        raise SystemExit(2) from None
