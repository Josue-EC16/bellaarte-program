"""Real original/DB backup roundtrip, only on the separately identified test cluster.

Launch with check_leny_documents_recovery.ps1. No business .env is ever read.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from uuid import uuid4
import zipfile

BACKEND = Path(__file__).resolve().parents[1]
PG_BIN = Path('C:/laragon/bin/postgresql/postgresql-17.9-1/bin')


def child():
    from run_notification_integration import validated_configuration
    manifest, urls = validated_configuration()
    from sqlalchemy import create_engine, event, text
    from sqlalchemy.engine import Engine, make_url
    import psycopg2
    from psycopg2.extensions import parse_dsn
    admin_url = make_url(os.environ.pop('TEST_ADMIN_DATABASE_URL'))
    if (admin_url.host, admin_url.port, admin_url.database, admin_url.username) != ('127.0.0.1',55432,'bab_vdos_testing','bab_test_admin') or admin_url.query:
        raise RuntimeError('Isolated admin identity rejected')
    restored_name = 'bab_doc_restore_' + uuid4().hex[:16]
    restore_url = admin_url.set(database=restored_name)
    original_connect = psycopg2.connect

    def guard(parameters):
        database = parameters.get('dbname', parameters.get('database'))
        if (parameters.get('host'),str(parameters.get('port'))) != ('127.0.0.1','55432') or database not in {'bab_vdos_testing', restored_name}:
            raise RuntimeError('Recovery test blocked an unapproved database')
        if parameters.get('user') not in {'bab_test_runner','bab_test_migrator','bab_test_admin'}:
            raise RuntimeError('Recovery test blocked an unapproved role')

    def connect(dsn=None,*args,**kwargs):
        parameters=parse_dsn(dsn or ''); parameters.update(kwargs); guard(parameters)
        return original_connect(dsn,*args,**kwargs)
    psycopg2.connect = connect
    def engine_guard(_dialect,_record,args,kwargs):
        parameters=parse_dsn(args[0]) if args else {}; parameters.update(kwargs); guard(parameters)
    event.listen(Engine,'do_connect',engine_guard)
    import smtplib
    smtplib.SMTP = smtplib.SMTP_SSL = lambda *_a,**_k: (_ for _ in ()).throw(RuntimeError('No mail in recovery'))
    control = create_engine(admin_url, isolation_level='AUTOCOMMIT', hide_parameters=True)
    with control.connect() as db:
        if tuple(db.execute(text('SELECT current_database(),current_user,inet_server_port()')).one()) != ('bab_vdos_testing','bab_test_admin',55432):
            raise RuntimeError('Recovery source identity mismatch')
        if db.scalar(text('SELECT instance_id FROM testing_control.instance')) != manifest['instance_id'] or Path(db.scalar(text('SHOW data_directory'))).resolve() != Path(manifest['data_directory']).resolve():
            raise RuntimeError('Recovery source badge mismatch')
        if db.scalar(text('SELECT version_num FROM alembic_version')) != '20261019_0019':
            raise RuntimeError('Isolated migration0019 required')
    from app.core.config import settings
    settings.database_url = urls['TEST_DATABASE_URL']
    settings.leny_documents_enabled = True
    settings.leny_documents_root = str(Path.cwd()/'private-library')
    settings.leny_documents_min_free_bytes = 0
    settings.pg_dump_path = str(PG_BIN/'pg_dump.exe')
    from app.core.database import SessionLocal, engine
    from app.core.backup_runtime import backup_lock
    from app.services.leny_document_service import DocumentService
    from app.services.leny_document_backup import verify_bundle,restore_bundle_files
    from app.services.leny_store import LenyActor
    from app.schemas.leny_documents import FolderCreate,DocumentUpload,DocumentChange
    from scripts.backup_manager import generate_backup
    from pypdf import PdfWriter
    import pyvips
    service = DocumentService(settings,SessionLocal)
    created_database = False
    user_id = account_id = None
    role_id = None
    created_role = False
    report = {'scope':'real parsers + PostgreSQL55432 + pg_dump/pg_restore + new private restore root', 'results':{}}
    try:
        with engine.begin() as db:
            role_id=db.scalar(text("INSERT INTO roles(codigo,nombre,activo) VALUES('ADMIN','QA RECOVERY ADMIN',true) ON CONFLICT(codigo) DO NOTHING RETURNING id"))
            created_role = role_id is not None
            role_id = role_id or db.scalar(text("SELECT id FROM roles WHERE codigo='ADMIN'"))
            token=uuid4().hex
            user_id=db.scalar(text("INSERT INTO usuarios(nombres,apellido_paterno,ci,celular,correo,zona,activo) VALUES('QA DOCUMENT','RECOVERY',:ci,'00000000',:mail,'TEST',true) RETURNING id"), {'ci':token[:25],'mail':token+'@example.invalid'})
            account_id=db.scalar(text("INSERT INTO cuentas(usuario_id,rol_id,username,password_hash,must_change_password,is_active) VALUES(:user,:role,:name,'NOT_A_LOGIN_HASH',false,true) RETURNING id"),{'user':user_id,'role':role_id,'name':'doc_recovery_'+token[:12]})
        actor=LenyActor(account_id,user_id,str(uuid4()))
        originals=[]
        with service.lock():
            folder=service.save_folder(actor,FolderCreate(name='QA RECOVERY '+token,role_codes=['ADMIN']))['items']
            folder_id=next(row['id'] for row in folder if row['name']=='QA RECOVERY '+token)
            pdf=io.BytesIO(); writer=PdfWriter(); writer.add_blank_page(width=100,height=100); writer.write(pdf)
            docx=io.BytesIO()
            with zipfile.ZipFile(docx,'w') as archive:
                archive.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
                archive.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
                archive.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Procedimiento sintético de inventario</w:t></w:r></w:p></w:body></w:document>')
            image=pyvips.Image.black(16,16)
            fixtures=[('manual.pdf',pdf.getvalue()),('manual.docx',docx.getvalue()),('imagen.jpg',image.jpegsave_buffer()),('imagen.png',image.pngsave_buffer())]
            for name,content in fixtures:
                data=DocumentUpload(request_id=uuid4(),sha256=hashlib.sha256(content).hexdigest(),folder_id=folder_id,title='QA '+name)
                stage,_=service.begin_upload(actor,data);service.storage.path(stage).write_bytes(content)
                detail=service.complete_upload(actor,data.request_id,stage,name,Path(name).suffix)
                originals.append(detail)
            service.trash(actor,originals[0]['id'],originals[0]['revision'])
        report['results']['four_formats_real_validation']=True
        with backup_lock({'origin':'QA DOCUMENT ISOLATED'}):
            result=generate_backup()
        if not result.success:
            raise RuntimeError(result.error)
        summary=verify_bundle(result.file_path)
        if summary['original_count'] != 4 or summary['preview_count'] != 3:
            raise RuntimeError('Unexpected bundle content count')
        report['results']['bundle_originals_and_previews_verified']=True
        restored_root=Path.cwd()/'restored-private-library'
        restore_bundle_files(result.file_path,restored_root)
        with control.connect() as db:
            # Fresh random name only: no DROP/overwrite of any existing database.
            db.execute(text(f'CREATE DATABASE "{restored_name}" TEMPLATE template0'))
            created_database=True
        environment={key:value for key,value in os.environ.items() if key.upper() in {'SYSTEMROOT','WINDIR','SYSTEMDRIVE','PATH','TEMP','TMP'}}
        environment['PGPASSWORD']=admin_url.password
        restored=subprocess.run([str(PG_BIN/'pg_restore.exe'),'-h','127.0.0.1','-p','55432','-U','bab_test_admin','-d',restored_name,
                                 '--no-owner','--no-privileges','--exit-on-error',str(restored_root/'database.dump')],env=environment,capture_output=True,timeout=90)
        if restored.returncode:
            raise RuntimeError('Isolated pg_restore failed; details withheld')
        restored_engine=create_engine(restore_url,hide_parameters=True)
        try:
            with restored_engine.connect() as db:
                versions=db.execute(text('SELECT storage_key,sha256,size_bytes,preview_key,preview_size_bytes FROM leny.documento_versiones')).all()
                if len(versions)!=4 or db.scalar(text("SELECT count(*) FROM leny.documentos WHERE state='trash'"))!=1:
                    raise RuntimeError('Restored metadata count mismatch')
                for key,digest,size,preview_key,preview_size in versions:
                    content=(restored_root/key).read_bytes()
                    if hashlib.sha256(content).hexdigest()!=digest or len(content)!=size:
                        raise RuntimeError('Restored original mismatch')
                    if preview_key and (restored_root/preview_key).stat().st_size!=preview_size:
                        raise RuntimeError('Restored preview mismatch')
                if db.scalar(text('SELECT version_num FROM alembic_version'))!='20261019_0019':
                    raise RuntimeError('Restored schema mismatch')
            report['results']['real_pg_restore_metadata_files_and_trash_match']=True
        finally:
            restored_engine.dispose()
        # Fail-closed: a modified archive cannot be accepted for restoration.
        broken=Path.cwd()/'corrupt.zip'; broken.write_bytes(Path(result.file_path).read_bytes()[:100])
        try:
            verify_bundle(broken)
            raise RuntimeError('Corrupt bundle unexpectedly verified')
        except Exception as error:
            from app.services.leny_document_storage import DocumentError
            if not isinstance(error,DocumentError):raise
        report['results']['corrupt_bundle_rejected']=True
        report_path=BACKEND.parent/'documentacion/evidencias/leny_rag01_recovery.json'
        report_path.write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(report))
        return 0
    finally:
        if created_database:
            with control.connect() as db:
                db.execute(text(f'DROP DATABASE "{restored_name}"'))
        if user_id:
            with engine.begin() as db:
                db.execute(text('DELETE FROM leny.documento_versiones WHERE document_id IN (SELECT id FROM leny.documentos WHERE created_by=:id)'),{'id':user_id})
                db.execute(text('DELETE FROM leny.documentos WHERE created_by=:id'),{'id':user_id})
                db.execute(text('DELETE FROM leny.documento_operaciones WHERE user_id=:id'),{'id':user_id})
                db.execute(text('DELETE FROM leny.carpetas WHERE created_by=:id'),{'id':user_id})
                db.execute(text('DELETE FROM auditoria_sistema WHERE usu_id=:id'),{'id':user_id})
                db.execute(text('DELETE FROM cuentas WHERE id=:id'),{'id':account_id})
                db.execute(text('DELETE FROM usuarios WHERE id=:id'),{'id':user_id})
                if created_role:db.execute(text('DELETE FROM roles WHERE id=:id'),{'id':role_id})
        service.engine.dispose();engine.dispose();control.dispose()


def main():
    from run_base_tests import _child_environment
    with TemporaryDirectory(prefix='bab-document-recovery-') as temporary:
        environment=_child_environment(temporary)
        for key in ('TEST_DATABASE_URL','TEST_MIGRATION_DATABASE_URL','TEST_ADMIN_DATABASE_URL','TEST_PG_MANIFEST'):
            environment[key]=os.environ[key]
        environment['DATABASE_URL']=environment['TEST_DATABASE_URL']
        environment['PYTHONPATH']=str(BACKEND)+os.pathsep+str(BACKEND/'scripts')
        bootstrap="import runpy,sys; m=runpy.run_path(sys.argv[1]); raise SystemExit(m['child']())"
        result=subprocess.run([sys.executable,'-B','-c',bootstrap,str(Path(__file__).resolve())],cwd=temporary,env=environment)
        return result.returncode


if __name__=='__main__':
    try:
        raise SystemExit(main())
    except Exception:
        print('Isolated document recovery failed safely; inspect synthetic test setup.',file=sys.stderr)
        raise SystemExit(1)
