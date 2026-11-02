"""Private pilot backup and recovery rehearsal. No migration or business DML.

Requires a separately verified test cluster and its admin URL in the process
environment. Restores only into a freshly created random DB on 127.0.0.1:55432.
Never runs the application, seeds, workers or document recovery against business.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4
import zipfile

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))
TABLES = ('documentos','documento_versiones','documento_roles_lectura','carpetas',
          'carpeta_roles_lectura','rag_indexaciones','rag_fragmentos','rag_embeddings')


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024**2), b''):
            value.update(chunk)
    return value.hexdigest()


def fingerprints(db):
    from sqlalchemy import text
    # Only counts/hashes leave PostgreSQL; no document text, vectors or titles.
    return {name:dict(db.execute(text(
        'SELECT count(*) AS count, md5(coalesce(string_agg(row_digest,\'\' ORDER BY row_digest),\'\')) AS fingerprint '
        'FROM (SELECT md5(to_jsonb(t)::text) AS row_digest FROM leny.'+name+' t) h')).mappings().one())
        for name in TABLES}


def source_paths():
    paths = []
    for directory in ('backend/app','backend/scripts','backend/alembic','frontend/src'):
        paths.extend(p for p in (ROOT/directory).rglob('*') if p.is_file()
                     and p.suffix in {'.py','.ps1','.js','.jsx','.css','.csv','.conf','.mako'})
    paths.extend(ROOT/name for name in ('backend/main.py','backend/requirements.txt',
        'backend/requirements-leny-documents.txt','backend/requirements-leny-rag.txt',
        'backend/alembic.ini','frontend/package.json','frontend/pnpm-lock.yaml','frontend/vite.config.js'))
    return sorted({p for p in paths if p.is_file()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private-dir', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--prepare-backup', required=True, action='store_true')
    args = parser.parse_args()
    output = args.output.resolve()
    if (output.parent != (ROOT/'documentacion/evidencias').resolve() or output.suffix != '.json'
            or not output.name.startswith('leny_rag04_pilot_recovery') or output.exists()):
        raise ValueError('A new pilot recovery evidence filename is required')
    os.chdir(BACKEND)
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import NullPool
    from app.core.config import settings
    from app.core.backup_runtime import backup_lock
    from app.services.leny_document_storage import DocumentStorage, protect_directory, _check_path
    from app.services.leny_document_backup import build_bundle, freeze_library, verify_bundle, restore_bundle_files
    from scripts.backup_manager import _generate_database_backup, resolve_pg_dump_path

    private = args.private_dir.resolve()
    base = (Path(os.environ['LOCALAPPDATA'])/'BAB_VDOS/leny-pilot').resolve()
    if not private.is_relative_to(base) or private == base or private.exists():
        raise ValueError('A new dedicated private pilot directory is required')
    _check_path(private)
    url = make_url(settings.effective_database_url)
    if (url.host not in ('localhost','127.0.0.1') or url.port != 5432 or url.database != 'bellaarte_db'
            or settings.leny_rag_profile != 'legacy'):
        raise ValueError('Usual database/profile identity mismatch')
    admin_url = make_url(os.environ['TEST_ADMIN_DATABASE_URL'])
    if (admin_url.host != '127.0.0.1' or admin_url.port != 55432
            or admin_url.username != 'bab_test_admin' or admin_url.database != 'bab_vdos_testing'):
        raise ValueError('Isolated admin identity mismatch')
    cluster_manifest = json.loads(Path(os.environ['TEST_PG_MANIFEST']).read_text('utf-8-sig'))
    if cluster_manifest['port'] != 55432 or cluster_manifest['host'] != '127.0.0.1':
        raise ValueError('Test manifest mismatch')
    storage = DocumentStorage(settings)
    _check_path(storage.root)
    if not (storage.root/'.leny-private-root').is_file():
        raise ValueError('Existing private document library required')
    # Never mutate or initialize the usual library here.
    private.mkdir(parents=True, exist_ok=False)
    protect_directory(private)
    source_inventory = {p.relative_to(ROOT).as_posix():digest(p) for p in source_paths()}
    code_zip = private/'pilot-code.zip'
    with zipfile.ZipFile(code_zip,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for name in source_inventory:
            archive.write(ROOT/name,name)
    (private/'code-inventory.json').write_text(json.dumps(source_inventory,indent=2)+'\n',encoding='utf-8')
    # Use the reviewed helper to stage env bytes, never replace the actual env.
    from scripts.leny_rag_pilot_profile import render_environment, validate_staged_settings, sha
    old = (BACKEND/'.env').read_bytes()
    staged = render_environment(old)
    (private/'env.before').write_bytes(old)
    (private/'env.pilot').write_bytes(staged)
    changes = validate_staged_settings(private/'env.before',private/'env.pilot')
    (private/'profile-change.json').write_text(json.dumps(dict(
        pilot='LENY RAG V1 - Piloto supervisado',state='prepared_not_activated',
        created_utc=datetime.now(timezone.utc).isoformat(),before_sha256=sha(old),
        proposed_sha256=sha(staged),changes=changes),indent=2)+'\n',encoding='utf-8')

    business = create_engine(url,poolclass=NullPool,hide_parameters=True,
        connect_args={'options':'-c default_transaction_read_only=on -c statement_timeout=20000'})
    sessions = sessionmaker(business)
    control = create_engine(admin_url,poolclass=NullPool,hide_parameters=True,isolation_level='AUTOCOMMIT')
    name = 'bab_leny_pilot_restore_'+uuid4().hex
    created = False
    raw = storage.root/'backups'/('.pilot-'+uuid4().hex+'.dump')
    bundle = storage.root/'backups'/('pilot-'+uuid4().hex+'.zip')
    proof = dict(backup_verified=False,isolated_restore_verified=False,
                 business_profile='legacy',business_configuration_modified=False,
                 migrations_executed=False,private_package=str(private),
                 code_sha256=digest(code_zip),source_files_sha256=source_inventory)
    try:
        with control.connect() as db:
            if (str(db.scalar(text('SELECT instance_id FROM testing_control.instance'))) != cluster_manifest['instance_id']
                    or Path(db.scalar(text('SHOW data_directory'))).resolve() != Path(cluster_manifest['data_directory']).resolve()):
                raise ValueError('Isolated cluster marker/directory mismatch')
        with backup_lock({'origin':'LENY supervised pilot preparation'}):
            with freeze_library(settings) as lease:
                with business.connect() as db:
                    before = fingerprints(db)
                    if db.scalar(text('SELECT version_num FROM alembic_version')) != '20261020_0021':
                        raise ValueError('Usual revision mismatch')
                lease.check()
                result = _generate_database_backup(private_path=raw)
                if not result.success:
                    raise RuntimeError('Full private pg_dump failed; details withheld')
                lease.check()
                build_bundle(raw,bundle,sessions,storage)
                verified = verify_bundle(bundle)
                lease.check()
                with business.connect() as db:
                    if fingerprints(db) != before:
                        raise ValueError('Library changed during backup')
        raw.unlink()  # Only our own intermediate dump, now included in verified bundle.
        proof.update(backup_verified=True,backup_path=str(bundle),backup_sha256=digest(bundle),
                     backup_bytes=bundle.stat().st_size,revision=verified['alembic_revision'],
                     original_count=verified['original_count'],preview_count=verified['preview_count'],
                     data_fingerprints=before)
        restored_root = private/'restored-library'
        restore_bundle_files(bundle,restored_root)
        with control.connect() as db:
            db.execute(text(f'CREATE DATABASE "{name}" TEMPLATE template0'))
            created = True
            db.execute(text(f'REVOKE CONNECT ON DATABASE "{name}" FROM PUBLIC'))
        pg = Path(resolve_pg_dump_path()).parent/'pg_restore.exe'
        environment = {k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','PATH','TEMP','TMP'}}
        environment['PGPASSWORD'] = admin_url.password
        restored = subprocess.run([str(pg),'-h','127.0.0.1','-p','55432','-U','bab_test_admin',
            '-d',name,'--no-owner','--no-privileges','--exit-on-error',str(restored_root/'database.dump')],
            env=environment,capture_output=True,timeout=120)
        if restored.returncode:
            raise RuntimeError('Isolated pg_restore failed; details withheld')
        replica = create_engine(admin_url.set(database=name),poolclass=NullPool,hide_parameters=True,
            connect_args={'options':'-c default_transaction_read_only=on'})
        try:
            with replica.connect() as db:
                if fingerprints(db) != before or db.scalar(text('SELECT version_num FROM alembic_version')) != proof['revision']:
                    raise ValueError('Restored metadata differs')
                vector = tuple(db.execute(text("SELECT e.extversion,n.nspname FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace WHERE e.extname='vector'")).one())
                if vector != ('0.8.7','leny'):
                    raise ValueError('Restored pgvector differs')
                for row in db.execute(text('SELECT storage_key,sha256,size_bytes FROM leny.documento_versiones')):
                    file = restored_root/row.storage_key
                    if digest(file) != row.sha256 or file.stat().st_size != row.size_bytes:
                        raise ValueError('Restored original differs')
                proof.update(isolated_restore_verified=True,restored_vector_extension=list(vector))
        finally:
            replica.dispose()
        with business.connect() as db:
            proof['business_library_unchanged'] = fingerprints(db) == before
        proof['env_unchanged'] = digest(BACKEND/'.env') == sha(old)
        proof['source_freeze_verified'] = all(digest(ROOT/p)==h for p,h in source_inventory.items())
        if not all(proof[k] for k in ('business_library_unchanged','env_unchanged','source_freeze_verified')):
            raise ValueError('State changed during pilot preparation')
    finally:
        if created:
            # The only DROP target is the DB created by this invocation, never business/testing.
            if not name.startswith('bab_leny_pilot_restore_') or len(name) != 55:
                raise ValueError('Recovery cleanup identity mismatch')
            with control.connect() as db:
                db.execute(text(f'DROP DATABASE "{name}"'))
            proof['isolated_database_removed'] = True
        business.dispose(); control.dispose()
        proof['created_utc'] = datetime.now(timezone.utc).isoformat()
        (private/'recovery-proof.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    # Public report excludes private paths, code ZIP, configs, manifest text and credentials.
    public = {k:v for k,v in proof.items() if k not in ('private_package','backup_path','source_files_sha256')}
    public.update(state='prepared_not_activated',private_package_id=private.name,
                  backup_location='existing private document backup directory; details in protected recovery-proof.json')
    if output.exists():
        raise ValueError('Preserve existing recovery evidence; do not overwrite')
    output.write_text(json.dumps(public,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(public))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        import traceback
        frames = [{'file':Path(frame.filename).name,'line':frame.lineno,'function':frame.name}
                  for frame in traceback.extract_tb(error.__traceback__)]
        print(json.dumps({'operation_failed':type(error).__name__,'details_withheld':True,
                          'frames_without_values':frames}),file=sys.stderr)
        raise SystemExit(1)
