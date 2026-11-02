"""Authorized local SPEC-02 deployment; inspection only unless --apply.

Verifies a full private backup before extension SQL and additive0020. Does not
restore, downgrade, seed, alter roles or change any existing package version.
"""
from datetime import datetime,timezone
import argparse
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import re
import sys
from uuid import uuid4

BACKEND=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BACKEND))
from deploy_leny_storage import public_structure


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    from app.core.config import Settings,settings
    from sqlalchemy import create_engine,text
    from sqlalchemy.engine import make_url
    configured=Settings(_env_file=BACKEND/'.env')
    url=make_url(configured.effective_database_url)
    if (url.host not in {'127.0.0.1','localhost'} or (url.port or 5432)!=5432 or url.database!='bellaarte_db' or url.query):
        raise RuntimeError('Unexpected deployment target.')
    engine=create_engine(url,hide_parameters=True,connect_args={'connect_timeout':5,'options':'-c lock_timeout=5000 -c statement_timeout=30000'})
    try:
        with engine.connect() as db:
            if tuple(db.execute(text('SELECT current_database(),current_user,inet_server_port()')).one()) != ('bellaarte_db',url.username,5432):
                raise RuntimeError('Database identity mismatch.')
            revision=db.scalar(text('SELECT version_num FROM alembic_version'))
            if revision not in {'20261019_0019','20261019_0020'}:
                raise RuntimeError('Unreviewed starting revision.')
            print(json.dumps({'database':'bellaarte_db','port':5432,'revision':revision,'rag_enabled':configured.leny_rag_enabled}),flush=True)
            if not args.apply:return
            if revision!='20261019_0019' or configured.leny_rag_enabled:
                raise RuntimeError('Apply requires0019 with contextualization disabled.')
            if not db.scalar(text('SELECT pg_try_advisory_lock(83998045405465)')):
                raise RuntimeError('Another deployment is active.')
            before=public_structure(db)
            roles=list(db.execute(text('SELECT codigo FROM roles ORDER BY codigo')).scalars())
            if db.scalar(text("SELECT default_version FROM pg_available_extensions WHERE name='vector'"))!='0.8.7':
                raise RuntimeError('Reviewed pgvector native files unavailable.')
            from app.services.leny_rag_common import runtime_root,ocr_paths
            native=json.loads((runtime_root()/'runtime.json').read_text())
            if not all(native.get(k) for k in ('pgvector_isolated_verified','pgvector_backup_restore_verified','pgvector_shared_files')):
                raise RuntimeError('Isolated native evidence required.')
            if version('pgvector')!='0.5.1' or version('pypdfium2')!='5.14.0':
                raise RuntimeError('Dependency versions differ from approved manifest.')
            original=(BACKEND/'.env').read_bytes()
            from app.core.backup_runtime import backup_lock
            from scripts.backup_manager import generate_backup
            from app.services.leny_document_backup import verify_bundle
            settings.database_url=configured.effective_database_url
            if not settings.pg_dump_path:
                settings.pg_dump_path=r'C:\laragon\bin\postgresql\postgresql-17.9-1\bin\pg_dump.exe'
            with backup_lock({'operation':'LENY_RAG_DEPLOYMENT'}):
                backup=generate_backup()
                if not backup.success:raise RuntimeError('Complete private backup failed.')
                summary=verify_bundle(Path(backup.file_path))
                if summary['alembic_revision']!='20261019_0019':raise RuntimeError('Backup revision mismatch.')
                report={'time_utc':datetime.now(timezone.utc).isoformat(),'database':'bellaarte_db','port':5432,
                        'revision_before':revision,'revision_after':None,'backup_bytes':backup.file_size_bytes,
                        'backup_sha256':backup.sha256_hash,'backup_verified':True,'backup_originals':summary['original_count'],
                        'state':'backup_verified','business_restore_executed':False}
                report_path=Path(backup.file_path).parent/('deployment-0020-'+uuid4().hex+'.json')
                def record():report_path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
                record()
                db.rollback()
                with db.begin():
                    existing=db.execute(text("SELECT e.extversion,n.nspname FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace WHERE e.extname='vector'")).one_or_none()
                    if existing is None:db.execute(text("CREATE EXTENSION vector WITH SCHEMA leny VERSION '0.8.7'"))
                    elif tuple(existing)!=('0.8.7','leny'):raise RuntimeError('Unexpected extension identity.')
                from alembic import command
                from alembic.config import Config
                configuration=Config(str(BACKEND/'alembic.ini'));configuration.set_main_option('script_location',str(BACKEND/'alembic'))
                previous=os.environ.get('PGOPTIONS')
                try:
                    os.environ['PGOPTIONS']='-c lock_timeout=5000 -c statement_timeout=30000'
                    command.upgrade(configuration,'20261019_0020')
                finally:
                    if previous is None:os.environ.pop('PGOPTIONS',None)
                    else:os.environ['PGOPTIONS']=previous
                if db.scalar(text('SELECT version_num FROM alembic_version'))!='20261019_0020' or public_structure(db)!=before:
                    raise RuntimeError('Post-deployment schema mismatch; no automatic rollback.')
                if list(db.execute(text('SELECT codigo FROM roles ORDER BY codigo')).scalars())!=roles:
                    raise RuntimeError('Role definitions changed; inspect.')
                for table in ('rag_trabajos','rag_indexaciones','rag_fragmentos','rag_embeddings','rag_workers'):
                    for permission in ('SELECT','INSERT','UPDATE','DELETE'):
                        if not db.scalar(text('SELECT has_table_privilege(:table,:permission)'),{'table':'leny.'+table,'permission':permission}):
                            raise RuntimeError('Runtime DML grant missing.')
                report.update(revision_after='20261019_0020',public_structure_unchanged=True,role_codes_unchanged=True,
                              runtime_permissions_verified=True,pgvector_version='0.8.7',extension_schema='leny',state='schema_verified')
                record()
                if (BACKEND/'.env').read_bytes()!=original:raise RuntimeError('Configuration changed concurrently; feature remains disabled.')
                content=original.decode('utf-8');newline='\r\n' if '\r\n' in content else '\n'
                tess,data=ocr_paths(configured)
                for key,value in {'LENY_RAG_ENABLED':'true','LENY_RAG_MODEL':configured.leny_rag_model,
                                  'LENY_RAG_MODEL_DIGEST':configured.leny_rag_model_digest,
                                  'LENY_RAG_TESSERACT_PATH':tess.as_posix(),'LENY_RAG_TESSDATA_PATH':data.as_posix()}.items():
                    expression=re.compile('^'+key+r'\s*=.*$',re.MULTILINE|re.IGNORECASE)
                    content=expression.sub(key+'='+value,content) if expression.search(content) else content.rstrip('\r\n')+newline+key+'='+value+newline
                with (BACKEND/'.env').open('wb') as handle:
                    handle.write(content.encode());handle.flush();os.fsync(handle.fileno())
                assert Settings(_env_file=BACKEND/'.env').leny_rag_enabled
                report.update(state='enabled_reload_and_worker_required',rag_enabled_in_env=True)
                record()
                public={**report,'isolated_native_verified':True,'manual_selector_validated_by_owner':True,
                        'worker_startup':'manual','embedding_execution':'CPU','model':configured.leny_rag_model,'dimension':1024}
                (BACKEND.parent/'documentacion/evidencias/leny_rag02_business_deployment.json').write_text(json.dumps(public,indent=2)+'\n',encoding='utf-8')
                print(json.dumps({'revision':'20261019_0020','public_structure_unchanged':True,'roles_unchanged':True,'enabled':True,'backup_verified':True}))
                print('Private deployment report: '+str(report_path))
    finally:engine.dispose()


if __name__=='__main__':
    try:main()
    except Exception as error:
        print('RAG deployment stopped: '+(str(error) if type(error)is RuntimeError else type(error).__name__),file=sys.stderr)
        raise SystemExit(1) from None
