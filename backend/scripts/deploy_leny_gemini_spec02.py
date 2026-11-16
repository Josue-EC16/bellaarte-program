"""Apply owner-authorized 0024 after idle checks and verified private backup.

Keeps the old non-reloading backend running: added defaults are backward
compatible. Reload is a separate final operation once the candidate is tested.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

BACKEND=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BACKEND))


def fingerprints(db):
    from sqlalchemy import text
    names=db.execute(text("SELECT schemaname,tablename FROM pg_tables WHERE schemaname='public' "
        "AND tablename NOT IN ('alembic_version','sesion_cuenta','auth_login_bucket') "
        "OR schemaname='leny' AND tablename IN ('conversaciones','mensajes','documentos','documento_versiones',"
        "'documento_roles_lectura','carpeta_roles_lectura','rag_indexaciones','rag_fragmentos','rag_embeddings') ORDER BY 1,2")).all()
    result={};q=db.dialect.identifier_preparer.quote
    for schema,table in names:
        value="to_jsonb(t)-'llm_provider'-'llm_model'" if (schema,table)==('leny','conversaciones') else 'to_jsonb(t)'
        row=db.execute(text(f"SELECT count(*),md5(coalesce(string_agg(h,'' ORDER BY h),'')) FROM (SELECT md5(({value})::text) h FROM {q(schema)}.{q(table)} t) h")).one()
        result[schema+'.'+table]=list(row)
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    os.chdir(BACKEND)
    from app.core.config import Settings
    from sqlalchemy import create_engine,text
    from sqlalchemy.engine import make_url
    from sqlalchemy.orm import sessionmaker
    from app.services.leny_coordination import PostgresCoordinator
    from app.core.backup_runtime import backup_lock
    from app.services.leny_document_storage import DocumentStorage,protect_directory
    from app.services.leny_document_backup import freeze_library,build_bundle,verify_bundle
    c=Settings(_env_file=BACKEND/'.env');url=make_url(c.effective_database_url)
    assert url.host in ('127.0.0.1','localhost') and (url.port or 5432)==5432 and url.database=='bellaarte_db'
    engine=create_engine(url,hide_parameters=True)
    with engine.connect() as db:
        revision=db.scalar(text('SELECT version_num FROM alembic_version'))
    print('Target bellaarte_db:5432; revision',revision,flush=True)
    if not args.apply:return
    assert revision=='20261104_0023'
    coordinator=PostgresCoordinator(c.effective_database_url);lease=coordinator.acquire()
    private=Path(os.environ['LOCALAPPDATA'])/'BAB_VDOS/leny-gemini-spec02'
    protect_directory(private)
    report={'revision_before':revision,'revision_after':None,'business_restore_executed':False}
    def record(): (private/'deployment.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    record()
    try:
        with backup_lock({'operation':'LENY_GEMINI_0024'}):
            with engine.connect() as db:
                assert not db.scalar(text("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid() AND backend_type='client backend' AND state='active'"))
                assert not db.scalar(text("SELECT count(*) FROM leny.rag_trabajos WHERE status IN ('queued','running')"))
                before=fingerprints(db)
            storage=DocumentStorage(c);storage.initialize()
            destination=storage.root/'backups';destination.mkdir(parents=True,exist_ok=True);protect_directory(destination)
            dump=destination/('leny-gemini-before-0024-'+uuid4().hex+'.dump');bundle=dump.with_suffix('.zip')
            binaries=Path(r'C:\laragon\bin\postgresql\postgresql-17.9-1\bin')
            env={k:v for k,v in os.environ.items() if not k.upper().startswith('PG')}
            env.update(PGPASSWORD=url.password or '',PGCONNECT_TIMEOUT='5')
            with freeze_library(c):
                with (private/'backup-errors.log').open('wb') as errors:
                    subprocess.run([str(binaries/'pg_dump.exe'),'-h',url.host,'-p','5432','-U',url.username,'-d','bellaarte_db','-Fc','-f',str(dump)],env=env,stderr=errors,stdout=subprocess.DEVNULL,check=True,timeout=180)
                    subprocess.run([str(binaries/'pg_restore.exe'),'--list',str(dump)],stderr=errors,stdout=subprocess.DEVNULL,check=True,timeout=60)
                    subprocess.run([str(binaries/'pg_restore.exe'),'--file',os.devnull,str(dump)],stderr=errors,stdout=subprocess.DEVNULL,check=True,timeout=180)
                build_bundle(dump,bundle,sessionmaker(engine),storage)
                assert verify_bundle(bundle)['alembic_revision']==revision
            report.update(backup_path=str(bundle),backup_sha256=hashlib.sha256(bundle.read_bytes()).hexdigest(),backup_bytes=bundle.stat().st_size,backup_verified=True)
            record()
            from alembic import command
            from alembic.config import Config
            configuration=Config(str(BACKEND/'alembic.ini'));configuration.set_main_option('script_location',str(BACKEND/'alembic'))
            previous=os.environ.get('PGOPTIONS')
            try:
                os.environ['PGOPTIONS']='-c lock_timeout=5000 -c statement_timeout=30000'
                command.upgrade(configuration,'20261105_0024')
            finally:
                if previous is None:os.environ.pop('PGOPTIONS',None)
                else:os.environ['PGOPTIONS']=previous
            with engine.connect() as db:
                report['revision_after']=db.scalar(text('SELECT version_num FROM alembic_version'))
                after=fingerprints(db)
                report['tables_changed']=[k for k in before if before[k]!=after.get(k)]
            record()
            assert report['revision_after']=='20261105_0024' and not report['tables_changed']
            print('0024 applied; private backup verified; original row fingerprints unchanged',flush=True)
    finally:
        lease.close();coordinator.engine.dispose();engine.dispose()


if __name__=='__main__':main()
