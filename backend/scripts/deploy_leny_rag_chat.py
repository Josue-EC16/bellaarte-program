"""Inspect SPEC03; --apply requires separate explicit business deployment approval.

No automatic restore/downgrade, role changes, model download or worker shutdown.
Stop the manual worker before applying. Default invocation is read-only.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from uuid import uuid4

BACKEND=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BACKEND))


def validate_activation_proof(config):
    evidence=BACKEND.parent/'documentacion/evidencias/leny_rag03_validation.json'
    proof=json.loads(evidence.read_text(encoding='utf-8'))
    if proof.get('activation_ready') is not True:
        raise RuntimeError('Final isolated validation and resource profile remain pending; activation withheld.')
    if proof.get('validated_keep_alive')!=config.leny_keep_alive:
        raise RuntimeError('Validated model residency differs from deployment configuration.')
    report_path=BACKEND.parent/'documentacion/evidencias/leny_rag03_sequential_check.json'
    if proof.get('artifact_sha256',{}).get(report_path.name)!=hashlib.sha256(report_path.read_bytes()).hexdigest():
        raise RuntimeError('Real-provider resource evidence changed after validation.')
    measured=json.loads(report_path.read_text(encoding='utf-8'))
    profile=measured.get('profile',{})
    required=('admin_publication_and_caja_real_chat','real_backup_restore_vectors_and_originals',
              'known_document_injection_not_obeyed','general_unavailable_and_no_evidence','cpu_embeddings_1024')
    if (measured.get('results',{}).get('real_formats')!=4 or
            any(measured['results'].get(key) is not True for key in required) or
            profile.get('keep_alive')!=config.leny_keep_alive or
            profile.get('cold_ram_floor_bytes',0)<getattr(config,'leny_rag_min_ram_bytes',2*1024**3) or
            profile.get('resident_ram_floor_bytes',0)<getattr(config,'leny_rag_min_resident_ram_bytes',1024**3)):
        raise RuntimeError('Complete real-provider evidence with matching memory guards is required.')
    for relative in ('backend/app/services/leny_service.py','backend/app/services/leny_rag_retrieval.py',
                     'backend/app/services/leny_inference_state.py','backend/alembic/versions/20261020_0021_leny_publication_sources.py'):
        actual=hashlib.sha256((BACKEND.parent/relative).read_bytes()).hexdigest()
        if proof.get('source_sha256',{}).get(relative)!=actual:
            raise RuntimeError('Final validation does not match the current implementation.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--keep-alive',choices=['0'],help='Explicitly adopt the isolated-tested sequential residency profile with activation; no forced model unload.')
    arguments=parser.parse_args()
    # Shared services load .env relative to cwd, as with the normal backend.
    # Resolve it before their first import, including backup configuration.
    os.chdir(BACKEND)
    from sqlalchemy import create_engine,text
    from sqlalchemy.engine import make_url
    from app.core.config import Settings,settings
    from deploy_leny_storage import public_structure
    from app.services.leny_coordination import PostgresLease
    config=Settings(_env_file=BACKEND/'.env')
    url=make_url(config.effective_database_url)
    if (url.host not in {'localhost','127.0.0.1'} or (url.port or 5432)!=5432 or url.database!='bellaarte_db' or url.query):
        raise RuntimeError('Unexpected deployment target.')
    engine=create_engine(url,hide_parameters=True,connect_args={'connect_timeout':5,'options':'-c lock_timeout=5000 -c statement_timeout=30000'})
    generation=None
    try:
        with engine.connect() as db:
            if tuple(db.execute(text('SELECT current_database(),current_user,inet_server_port()')).one())!=('bellaarte_db',url.username,5432):
                raise RuntimeError('Database identity mismatch.')
            revision=db.scalar(text('SELECT version_num FROM alembic_version'))
            if revision not in {'20261019_0020','20261020_0021'}:raise RuntimeError('Unexpected schema revision.')
            print(json.dumps({'database':'bellaarte_db','port':5432,'revision':revision,'rag_chat_enabled':config.leny_rag_chat_enabled}))
            if not arguments.apply:return
            if revision!='20261019_0020' or config.leny_rag_chat_enabled or not config.leny_documents_enabled or not config.leny_rag_enabled:
                raise RuntimeError('Apply requires0020 with library/contextualization enabled and RAG chat disabled.')
            target=config.model_copy(update={'leny_keep_alive':arguments.keep_alive}) if arguments.keep_alive is not None else config
            validate_activation_proof(target)
            evidence=BACKEND.parent/'documentacion/evidencias/leny_rag03_real_check.json'
            proof=json.loads(evidence.read_text(encoding='utf-8'))
            if not proof.get('results',{}).get('admin_publication_and_caja_real_chat') or not proof['results'].get('real_backup_restore_vectors_and_originals'):
                raise RuntimeError('Isolated real-provider and recovery evidence required.')
            if not db.scalar(text('SELECT pg_try_advisory_lock(83998045405465)')):raise RuntimeError('Another deployment is active.')
            if not db.scalar(text('SELECT pg_try_advisory_lock(:key)'),{'key':0x4C454E590201}):
                raise RuntimeError('Stop the owned manual contextualization worker first.')
            generation=PostgresLease(engine)
            before=public_structure(db)
            roles=list(db.execute(text('SELECT codigo FROM roles ORDER BY codigo')).scalars())
            original=(BACKEND/'.env').read_bytes()
            from app.core.backup_runtime import backup_lock
            from scripts.backup_manager import generate_backup
            from app.services.leny_document_backup import verify_bundle
            settings.database_url=config.effective_database_url
            if not settings.pg_dump_path:settings.pg_dump_path=r'C:\laragon\bin\postgresql\postgresql-17.9-1\bin\pg_dump.exe'
            with backup_lock({'operation':'LENY_RAG_CHAT_DEPLOYMENT'}):
                backup=generate_backup()
                if not backup.success:raise RuntimeError('Complete private backup failed.')
                summary=verify_bundle(Path(backup.file_path))
                if summary['alembic_revision']!='20261019_0020':raise RuntimeError('Backup revision mismatch.')
                report=dict(time_utc=datetime.now(timezone.utc).isoformat(),revision_before=revision,
                    revision_after=None,backup_verified=True,backup_bytes=backup.file_size_bytes,
                    backup_sha256=backup.sha256_hash,state='backup_verified',business_restore_executed=False,
                    keep_alive_before=config.leny_keep_alive,keep_alive_after=target.leny_keep_alive)
                private=Path(backup.file_path).parent/('deployment-0021-'+uuid4().hex+'.json')
                def record():private.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
                record();db.rollback()
                from alembic import command
                from alembic.config import Config
                alembic=Config(str(BACKEND/'alembic.ini'));alembic.set_main_option('script_location',str(BACKEND/'alembic'))
                prior=os.environ.get('PGOPTIONS')
                try:
                    os.environ['PGOPTIONS']='-c lock_timeout=5000 -c statement_timeout=30000'
                    command.upgrade(alembic,'20261020_0021')
                finally:
                    if prior is None:os.environ.pop('PGOPTIONS',None)
                    else:os.environ['PGOPTIONS']=prior
                if public_structure(db)!=before or list(db.execute(text('SELECT codigo FROM roles ORDER BY codigo')).scalars())!=roles:
                    raise RuntimeError('Unexpected public/role change; inspect without automatic rollback.')
                for table in ('rag_fuentes_mensaje','inferencia_estado'):
                    if not db.scalar(text("SELECT has_table_privilege(:table,'SELECT,INSERT,UPDATE,DELETE')"),{'table':'leny.'+table}):
                        raise RuntimeError('Runtime grant missing.')
                if db.scalar(text('SELECT state FROM leny.inferencia_estado WHERE id=1'))!='idle':raise RuntimeError('Inference state is not idle.')
                report.update(revision_after='20261020_0021',public_structure_unchanged=True,role_codes_unchanged=True,state='schema_verified')
                record()
                if (BACKEND/'.env').read_bytes()!=original:raise RuntimeError('Configuration changed concurrently; activation withheld.')
                value=original.decode('utf-8');newline='\r\n' if '\r\n' in value else '\n'
                changes={'LENY_RAG_CHAT_ENABLED':'true'}
                if arguments.keep_alive is not None:changes['LENY_KEEP_ALIVE']=target.leny_keep_alive
                for key,setting in changes.items():
                    expression=re.compile('^'+key+r'\s*=.*$',re.M|re.I)
                    value=expression.sub(key+'='+setting,value) if expression.search(value) else value.rstrip('\r\n')+newline+key+'='+setting+newline
                with (BACKEND/'.env').open('wb') as handle:handle.write(value.encode());handle.flush();os.fsync(handle.fileno())
                verified=Settings(_env_file=BACKEND/'.env')
                if not verified.leny_rag_chat_enabled or verified.leny_keep_alive!=target.leny_keep_alive:
                    raise RuntimeError('Configuration verification failed; inspect before restarting.')
                report.update(state='enabled_reload_and_business_verification_required',rag_chat_enabled=True)
                record()
                (BACKEND.parent/'documentacion/evidencias/leny_rag03_business_deployment.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
                print(json.dumps({'applied':'20261020_0021','backup_verified':True,'reload_required':True,'business_conversation_verified':False}))
    finally:
        if generation:generation.close()
        engine.dispose()


if __name__=='__main__':
    try:main()
    except Exception as error:
        print('RAG03 deployment stopped: '+(str(error) if type(error) is RuntimeError else getattr(error,'code',type(error).__name__)),file=sys.stderr)
        raise SystemExit(1) from None
