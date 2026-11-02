"""Versioned, verified private DB/original bundles; never restores a database."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time
from types import SimpleNamespace
from uuid import UUID, uuid4
import zipfile

from sqlalchemy import create_engine, select, text
from sqlalchemy.pool import NullPool

from app.models.leny_documents import LenyDocumentVersion
from app.services.leny_document_storage import DocumentError, DocumentStorage, _check_path

LIBRARY_LOCK = 0x4C454E590101
MAX_MANIFEST_BYTES = 20 * 1024**2
MAX_ORIGINALS = 100_000
MAX_UNCOMPRESSED_BYTES = 10 * 1024**3
STORAGE_KEY = re.compile(r'versions/[a-f0-9]{32}\.blob')
PREVIEW_KEY = re.compile(r'previews/[a-f0-9]{32}\.(?:png|jpg|json)')
SHA256 = re.compile(r'[a-f0-9]{64}')


def _invalid():
    return DocumentError('DOCUMENT_BACKUP_INVALID', 'El paquete documental no es válido o no coincide con su manifiesto.', 422)


@contextmanager
def freeze_library(settings):
    """Caller already holds the ERP backup lock; wait only for in-flight writes."""
    # Offline ZIP verification must not import application configuration/DB.
    from app.services.leny_document_service import CURRENT_LEASE, LibraryLease, TRANSACTION_GATE
    engine = create_engine(settings.effective_database_url, poolclass=NullPool, connect_args={
        'connect_timeout': 5, 'options': '-c statement_timeout=5000',
        'keepalives': 1, 'keepalives_idle': 5, 'keepalives_interval': 2, 'keepalives_count': 2,
    })
    connection = None
    held = False
    try:
        connection = engine.connect().execution_options(isolation_level='AUTOCOMMIT')
        deadline = time.monotonic() + 240
        while True:
            gate = connection.scalar(text('SELECT pg_try_advisory_lock(:key)'), {'key':TRANSACTION_GATE})
            if gate:
                try:
                    held = connection.scalar(text('SELECT pg_try_advisory_lock(:key)'), {'key':LIBRARY_LOCK})
                finally:
                    connection.execute(text('SELECT pg_advisory_unlock(:key)'), {'key':TRANSACTION_GATE})
                if held:
                    break
            if time.monotonic() >= deadline:
                raise DocumentError('DOCUMENT_BACKUP_BUSY', 'La biblioteca no pudo detener sus operaciones para el respaldo.', 503)
            time.sleep(0.25)
        token = CURRENT_LEASE.set(LibraryLease(connection))
        try:
            yield CURRENT_LEASE.get()
        finally:
            CURRENT_LEASE.reset(token)
    finally:
        try:
            if connection is not None:
                try:
                    if held:
                        connection.execute(text('SELECT pg_advisory_unlock(:key)'), {'key': LIBRARY_LOCK})
                finally:
                    # Never recycle a physical session that may retain an advisory lock.
                    try:
                        connection.invalidate()
                    finally:
                        connection.close()
        finally:
            engine.dispose()


def _copy_hash(source, destination):
    digest, count = hashlib.sha256(), 0
    while True:
        chunk = source.read(1024 * 1024)
        if not chunk:
            return digest.hexdigest(), count
        destination.write(chunk)
        digest.update(chunk)
        count += len(chunk)


class _Sink:
    @staticmethod
    def write(_data):
        pass


def build_bundle(dump_path, destination_zip, session_factory, storage):
    """The caller MUST hold freeze_library across pg_dump and this function."""
    dump_path, destination = Path(dump_path).absolute(), Path(destination_zip).absolute()
    _check_path(dump_path)
    _check_path(destination)
    if (not dump_path.resolve().is_relative_to(storage.root.resolve())
            or not destination.resolve().is_relative_to((storage.root / 'backups').resolve())
            or destination.suffix.lower() != '.zip' or destination.exists()):
        raise DocumentError('DOCUMENT_BACKUP_DESTINATION', 'El respaldo requiere un destino privado nuevo.', 409)
    destination.parent.mkdir(parents=True, exist_ok=True)
    _check_path(destination.parent)
    temporary = destination.with_name('.bundle-' + uuid4().hex + '.tmp')
    try:
        with session_factory() as db:
            revision = db.execute(text('SELECT version_num FROM alembic_version')).scalar_one()
            versions = list(db.scalars(select(LenyDocumentVersion).order_by(LenyDocumentVersion.id)))
            rag = None
            if revision >= '20261019_0020':
                extension = db.execute(text("SELECT e.extversion,n.nspname FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace WHERE e.extname='vector'")).one_or_none()
                if extension is None or tuple(extension) != ('0.8.7','leny'):
                    raise DocumentError('DOCUMENT_BACKUP_INTEGRITY', 'La extensión vectorial no coincide con el esquema respaldado.', 503)
                configurations = [dict(model=row.model, model_digest=row.model_digest, dimension=row.dimension,
                                       pipeline_version=row.pipeline_version, chunking_version=row.chunking_version,
                                       ocr_version=row.ocr_version, config=row.config) for row in db.execute(text(
                    'SELECT DISTINCT model,model_digest,dimension,pipeline_version,chunking_version,ocr_version,config FROM leny.rag_indexaciones LIMIT 101'))]
                if len(configurations) > 100:
                    raise DocumentError('DOCUMENT_BACKUP_LIMIT', 'Demasiadas configuraciones de indexación para este respaldo.', 409)
                counts = {name:db.execute(text('SELECT count(*) FROM leny.'+name)).scalar_one() for name in
                          ('rag_trabajos','rag_indexaciones','rag_fragmentos','rag_embeddings')}
                rag = dict(pgvector_version=extension[0], extension_schema=extension[1], counts=counts,
                           configurations=configurations, restore_reconciliation_required=True)
        if len(versions) > MAX_ORIGINALS:
            raise DocumentError('DOCUMENT_BACKUP_LIMIT', 'El respaldo supera el límite documental configurado.', 409)
        if (not 0 < dump_path.stat().st_size <= MAX_UNCOMPRESSED_BYTES
                or dump_path.stat().st_size + sum(v.size_bytes + getattr(v, 'preview_size_bytes', 0) for v in versions) + MAX_MANIFEST_BYTES > MAX_UNCOMPRESSED_BYTES):
            raise DocumentError('DOCUMENT_BACKUP_LIMIT', 'El respaldo supera el tamaño máximo permitido.', 409)
        manifest = {'schema_version': 1, 'alembic_revision': revision, 'database': {},
                    'originals': [], 'previews': [], 'previews_regenerable': True}
        if rag is not None:
            manifest.update(schema_version=2, contextualization=rag)
        with temporary.open('xb') as output:
            with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
                with dump_path.open('rb') as source, archive.open('database.dump', 'w', force_zip64=True) as target:
                    digest, size = _copy_hash(source, target)
                manifest['database'] = {'archive_name': 'database.dump', 'sha256': digest, 'size_bytes': size}
                for version in versions:
                    if not STORAGE_KEY.fullmatch(version.storage_key):
                        raise _invalid()
                    archive_name = 'originals/' + version.storage_key
                    with storage.open(version.storage_key) as source, archive.open(archive_name, 'w', force_zip64=True) as target:
                        digest, size = _copy_hash(source, target)
                    if digest != version.sha256 or size != version.size_bytes:
                        raise DocumentError('DOCUMENT_BACKUP_INTEGRITY', 'Un original no supera la comprobación de integridad.', 503)
                    manifest['originals'].append(dict(archive_name=archive_name,
                        version_id=str(version.id), document_id=str(version.document_id),
                        storage_key=version.storage_key, sha256=digest, size_bytes=size))
                    if getattr(version, 'preview_key', None):
                        if not PREVIEW_KEY.fullmatch(version.preview_key):
                            raise _invalid()
                        preview_name = 'previews/' + version.preview_key
                        with storage.open(version.preview_key) as source, archive.open(preview_name, 'w', force_zip64=True) as target:
                            digest, size = _copy_hash(source, target)
                        if size != version.preview_size_bytes:
                            raise DocumentError('DOCUMENT_BACKUP_INTEGRITY', 'Una vista previa no supera la comprobación de integridad.', 503)
                        manifest['previews'].append(dict(archive_name=preview_name, version_id=str(version.id),
                            storage_key=version.preview_key, sha256=digest, size_bytes=size))
                encoded = json.dumps(manifest, sort_keys=True, ensure_ascii=True).encode('utf-8')
                if len(encoded) > MAX_MANIFEST_BYTES:
                    raise DocumentError('DOCUMENT_BACKUP_LIMIT', 'El manifiesto supera el límite documental.', 409)
                archive.writestr('manifest.json', encoded)
            output.flush()
            os.fsync(output.fileno())
        verify_bundle(temporary)
        # Windows rename refuses an existing destination: backup artifacts are immutable.
        os.rename(temporary, destination)
        return manifest
    finally:
        temporary.unlink(missing_ok=True)


def _json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def _size(value, maximum):
    return type(value) is int and 0 < value <= maximum


def _uuid(value):
    return isinstance(value, str) and str(UUID(value)) == value


def _verify_open_archive(archive, max_uncompressed_bytes):
    infos = archive.infolist()
    names = [entry.filename for entry in infos]
    if (len(names) > MAX_ORIGINALS * 2 + 2 or len(names) != len(set(names))
            or 'manifest.json' not in names or 'database.dump' not in names):
        raise _invalid()
    if sum(entry.file_size for entry in infos) > max_uncompressed_bytes:
        raise _invalid()
    for entry in infos:
        mode = (entry.external_attr >> 16) & 0o170000
        if (entry.is_dir() or entry.flag_bits & 1 or entry.compress_type != zipfile.ZIP_STORED
                or mode not in (0, stat.S_IFREG)
                or (entry.filename not in ('manifest.json', 'database.dump')
                    and not re.fullmatch(r'(?:originals/versions/[a-f0-9]{32}\.blob|previews/previews/[a-f0-9]{32}\.(?:png|jpg|json))', entry.filename))):
            raise _invalid()
    if archive.getinfo('manifest.json').file_size > MAX_MANIFEST_BYTES:
        raise _invalid()
    manifest = json.loads(archive.read('manifest.json'), object_pairs_hook=_json_object)
    base_keys = {'schema_version', 'alembic_revision', 'database', 'originals', 'previews', 'previews_regenerable'}
    if (not isinstance(manifest, dict)
            or set(manifest) not in (base_keys, base_keys | {'contextualization'})
            or type(manifest['schema_version']) is not int or manifest['schema_version'] not in (1,2)
            or (manifest['schema_version'] == 2) != ('contextualization' in manifest)
            or manifest['previews_regenerable'] is not True
            or not isinstance(manifest['alembic_revision'], str)
            or not re.fullmatch(r'[A-Za-z0-9_]{1,32}', manifest['alembic_revision'])
            or not isinstance(manifest['originals'], list) or len(manifest['originals']) > MAX_ORIGINALS
            or not isinstance(manifest['previews'], list) or len(manifest['previews']) > MAX_ORIGINALS):
        raise _invalid()
    if manifest['schema_version'] == 2:
        rag = manifest['contextualization']
        if (not isinstance(rag, dict) or set(rag) != {'pgvector_version','extension_schema','counts','configurations','restore_reconciliation_required'}
                or rag['pgvector_version'] != '0.8.7' or rag['extension_schema'] != 'leny'
                or rag['restore_reconciliation_required'] is not True or not isinstance(rag['counts'],dict)
                or set(rag['counts']) != {'rag_trabajos','rag_indexaciones','rag_fragmentos','rag_embeddings'}
                or any(type(v) is not int or v < 0 for v in rag['counts'].values())
                or not isinstance(rag['configurations'],list) or len(rag['configurations']) > 100):
            raise _invalid()
        for config in rag['configurations']:
            if (not isinstance(config,dict) or set(config) != {'model','model_digest','dimension','pipeline_version','chunking_version','ocr_version','config'}
                    or config['model'] != 'qwen3-embedding:0.6b' or config['dimension'] != 1024
                    or not isinstance(config['model_digest'],str) or not SHA256.fullmatch(config['model_digest'])
                    or any(not isinstance(config[key],str) or not 1 <= len(config[key]) <= 64 for key in ('pipeline_version','chunking_version','ocr_version'))
                    or not isinstance(config['config'],dict)):
                raise _invalid()
    database = manifest['database']
    if (not isinstance(database, dict) or set(database) != {'archive_name', 'sha256', 'size_bytes'}
            or database['archive_name'] != 'database.dump'):
        raise _invalid()
    expected = {'manifest.json', 'database.dump'}
    version_ids = set()
    for item in manifest['originals']:
        if (not isinstance(item, dict)
                or set(item) != {'archive_name', 'version_id', 'document_id', 'storage_key', 'sha256', 'size_bytes'}
                or not isinstance(item['storage_key'], str) or not STORAGE_KEY.fullmatch(item['storage_key'])
                or item['archive_name'] != 'originals/' + item['storage_key']
                or not _uuid(item['version_id']) or not _uuid(item['document_id'])
                or item['version_id'] in version_ids or item['archive_name'] in expected
                or not _size(item['size_bytes'], 10 * 1024**2)):
            raise _invalid()
        expected.add(item['archive_name'])
        version_ids.add(item['version_id'])
    preview_ids = set()
    for item in manifest['previews']:
        if (not isinstance(item, dict)
                or set(item) != {'archive_name', 'version_id', 'storage_key', 'sha256', 'size_bytes'}
                or not isinstance(item['storage_key'], str) or not PREVIEW_KEY.fullmatch(item['storage_key'])
                or item['archive_name'] != 'previews/' + item['storage_key']
                or item['version_id'] not in version_ids or item['version_id'] in preview_ids
                or item['archive_name'] in expected or not _size(item['size_bytes'], 16 * 1024**2)):
            raise _invalid()
        expected.add(item['archive_name'])
        preview_ids.add(item['version_id'])
    if set(names) != expected:
        raise _invalid()
    for item in [database, *manifest['originals'], *manifest['previews']]:
        if (not isinstance(item['sha256'], str) or not SHA256.fullmatch(item['sha256'])
                or not _size(item['size_bytes'], max_uncompressed_bytes)
                or archive.getinfo(item['archive_name']).file_size != item['size_bytes']):
            raise _invalid()
        with archive.open(item['archive_name']) as source:
            digest, size = _copy_hash(source, _Sink())
        if digest != item['sha256'] or size != item['size_bytes']:
            raise _invalid()
    summary = {'verified': True, 'schema_version': manifest['schema_version'], 'alembic_revision': manifest['alembic_revision'],
               'original_count': len(manifest['originals']),
               'preview_count': len(manifest['previews']),
               'original_bytes': sum(item['size_bytes'] for item in manifest['originals']),
               'preview_bytes': sum(item['size_bytes'] for item in manifest['previews']),
               'database_bytes': database['size_bytes']}
    if manifest['schema_version'] == 2:
        summary['contextualization'] = manifest['contextualization']
    return manifest, summary


def verify_bundle(zip_path, *, max_uncompressed_bytes=MAX_UNCOMPRESSED_BYTES):
    try:
        with zipfile.ZipFile(zip_path, 'r') as archive:
            return _verify_open_archive(archive, max_uncompressed_bytes)[1]
    except DocumentError:
        raise
    except (OSError, ValueError, KeyError, TypeError, RecursionError, EOFError, zipfile.BadZipFile, NotImplementedError):
        raise _invalid() from None


def restore_bundle_files(zip_path, target, *, max_uncompressed_bytes=MAX_UNCOMPRESSED_BYTES):
    """Restore only files into a NEW private root; never invoke pg_restore."""
    target = Path(target).absolute()
    _check_path(target)
    if target.exists():
        raise DocumentError('DOCUMENT_RESTORE_TARGET_EXISTS', 'La restauración requiere un directorio nuevo y aislado.', 409)
    storage = DocumentStorage(SimpleNamespace(leny_documents_root=str(target)))
    try:
        with zipfile.ZipFile(zip_path, 'r') as archive:
            manifest, summary = _verify_open_archive(archive, max_uncompressed_bytes)
            storage.initialize()
            marker = storage.root / '.restore-incomplete'
            marker.touch(exist_ok=False)
            for item in [manifest['database'], *manifest['originals'], *manifest['previews']]:
                destination = storage.root / 'database.dump' if item['archive_name'] == 'database.dump' else storage.path(item['storage_key'])
                with destination.open('xb') as output, archive.open(item['archive_name']) as source:
                    digest, size = _copy_hash(source, output)
                    output.flush()
                    os.fsync(output.fileno())
                if digest != item['sha256'] or size != item['size_bytes']:
                    raise _invalid()
            marker.unlink()
            return {**summary, 'files_restored': True, 'database_restored': False}
    except DocumentError:
        raise
    except (OSError, ValueError, KeyError, TypeError, RecursionError, EOFError, zipfile.BadZipFile, NotImplementedError):
        raise _invalid() from None
