"""Bundle integrity tests use synthetic bytes and fake metadata, never a DB."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
import warnings
import zipfile

import pytest

from app.services.leny_document_backup import build_bundle, freeze_library, restore_bundle_files, verify_bundle
from app.services.leny_document_storage import DocumentError, DocumentStorage


class FakeSession:
    def __init__(self, versions):
        self.versions = versions

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        pass

    def execute(self, _statement):
        return SimpleNamespace(scalar_one=lambda: '20261019_0019')

    def scalars(self, _statement):
        return self.versions


@pytest.fixture
def bundle_fixture(tmp_path):
    storage = DocumentStorage(SimpleNamespace(leny_documents_root=str(tmp_path / 'private-library')))
    storage.initialize()
    original = b'QA ORIGINAL SYNTHETIC PDF'
    key = f'versions/{uuid4().hex}.blob'
    storage.path(key).write_bytes(original)
    version = SimpleNamespace(id=uuid4(), document_id=uuid4(), storage_key=key,
                              sha256=hashlib.sha256(original).hexdigest(), size_bytes=len(original),
                              preview_key=None, preview_size_bytes=0)
    dump = storage.root / 'backups' / 'synthetic.dump'
    dump.write_bytes(b'PGDMP SYNTHETIC TEST BYTES')
    destination = storage.root / 'backups' / 'complete.zip'
    return SimpleNamespace(storage=storage, version=version, original=original, dump=dump,
                           destination=destination, factory=lambda: FakeSession([version]))


def test_bundle_contains_verified_originals_and_no_private_paths(bundle_fixture):
    item = bundle_fixture
    manifest = build_bundle(item.dump, item.destination, item.factory, item.storage)
    summary = verify_bundle(item.destination)
    assert summary['verified'] is True and summary['original_count'] == 1
    assert manifest['originals'][0]['storage_key'] == item.version.storage_key
    assert manifest['previews_regenerable'] is True
    assert str(item.storage.root) not in json.dumps(manifest)
    with zipfile.ZipFile(item.destination) as archive:
        assert set(archive.namelist()) == {'database.dump', 'manifest.json', 'originals/' + item.version.storage_key}
        assert archive.read('originals/' + item.version.storage_key) == item.original


def test_original_checksum_mismatch_never_publishes_zip(bundle_fixture):
    item = bundle_fixture
    item.storage.path(item.version.storage_key).write_bytes(b'CORRUPTED')
    with pytest.raises(DocumentError) as failed:
        build_bundle(item.dump, item.destination, item.factory, item.storage)
    assert failed.value.code == 'DOCUMENT_BACKUP_INTEGRITY'
    assert not item.destination.exists()
    assert not list(item.destination.parent.glob('.bundle-*.tmp'))


def test_previews_are_verified_and_restored_with_originals(bundle_fixture, tmp_path):
    item = bundle_fixture
    preview = b'{"paragraphs":["QA SYNTHETIC PREVIEW"]}'
    item.version.preview_key = f'previews/{uuid4().hex}.json'
    item.version.preview_size_bytes = len(preview)
    item.storage.path(item.version.preview_key).write_bytes(preview)
    manifest = build_bundle(item.dump, item.destination, item.factory, item.storage)
    assert manifest['previews'][0]['archive_name'] == 'previews/' + item.version.preview_key
    assert verify_bundle(item.destination)['preview_count'] == 1
    target = tmp_path / 'preview-restored-library'
    restore_bundle_files(item.destination, target)
    assert (target / item.version.preview_key).read_bytes() == preview


def test_existing_bundle_is_never_overwritten(bundle_fixture):
    item = bundle_fixture
    item.destination.write_bytes(b'EXISTING BACKUP')
    with pytest.raises(DocumentError):
        build_bundle(item.dump, item.destination, item.factory, item.storage)
    assert item.destination.read_bytes() == b'EXISTING BACKUP'


@pytest.mark.parametrize('attack', ['traversal', 'duplicate', 'unreferenced', 'symlink', 'manifest_hash', 'missing', 'json_duplicate', 'unsupported_schema'])
def test_archive_tampering_is_rejected(bundle_fixture, attack):
    item = bundle_fixture
    build_bundle(item.dump, item.destination, item.factory, item.storage)
    corrupted = item.destination.with_name('corrupted.zip')
    with zipfile.ZipFile(item.destination) as source, zipfile.ZipFile(corrupted, 'w') as target:
        for entry in source.infolist():
            if attack == 'missing' and entry.filename == 'database.dump':
                continue
            data = source.read(entry.filename)
            if entry.filename == 'manifest.json' and attack in {'manifest_hash', 'json_duplicate', 'unsupported_schema'}:
                manifest = json.loads(data)
                if attack == 'manifest_hash':
                    manifest['database']['sha256'] = '0' * 64
                elif attack == 'unsupported_schema':
                    manifest['schema_version'] = 2
                data = json.dumps(manifest).encode()
                if attack == 'json_duplicate':
                    data = data.replace(b'{', b'{"schema_version":1,', 1)
            if attack == 'symlink' and entry.filename == 'database.dump':
                entry.external_attr = (0o120777 << 16)
            target.writestr(entry, data)
        if attack == 'traversal':
            target.writestr('../outside', b'ATTACK')
        elif attack == 'unreferenced':
            target.writestr('originals/versions/' + uuid4().hex + '.blob', b'ATTACK')
        elif attack == 'duplicate':
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', UserWarning)
                target.writestr('database.dump', b'DUPLICATE')
    with pytest.raises(DocumentError) as failed:
        verify_bundle(corrupted)
    assert failed.value.code == 'DOCUMENT_BACKUP_INVALID'


def test_archive_limits_and_legacy_dump_fail_safely(bundle_fixture):
    item = bundle_fixture
    build_bundle(item.dump, item.destination, item.factory, item.storage)
    with pytest.raises(DocumentError):
        verify_bundle(item.destination, max_uncompressed_bytes=1)
    with pytest.raises(DocumentError) as legacy:
        verify_bundle(item.dump)
    assert legacy.value.code == 'DOCUMENT_BACKUP_INVALID'


def test_restore_files_requires_new_private_root_and_never_runs_database_restore(bundle_fixture, tmp_path):
    item = bundle_fixture
    build_bundle(item.dump, item.destination, item.factory, item.storage)
    target = tmp_path / 'isolated-restored-library'
    summary = restore_bundle_files(item.destination, target)
    assert summary['files_restored'] is True and summary['database_restored'] is False
    assert (target / item.version.storage_key).read_bytes() == item.original
    assert (target / 'database.dump').read_bytes() == item.dump.read_bytes()
    assert not (target / '.restore-incomplete').exists()
    with pytest.raises(DocumentError) as repeated:
        restore_bundle_files(item.destination, target)
    assert repeated.value.code == 'DOCUMENT_RESTORE_TARGET_EXISTS'


def test_restore_rejects_invalid_bundle_before_creating_target(bundle_fixture, tmp_path):
    target = tmp_path / 'must-not-be-created'
    with pytest.raises(DocumentError):
        restore_bundle_files(bundle_fixture.dump, target)
    assert not target.exists()


def test_freeze_releases_physical_connection_on_caller_error(monkeypatch):
    from app.services import leny_document_backup as implementation
    events = []
    class Connection:
        def execution_options(self, **_kwargs):
            return self
        def scalar(self, *_args):
            events.append('acquire')
            return True
        def execute(self, *_args):
            events.append('unlock')
        def invalidate(self):
            events.append('invalidate')
        def close(self):
            events.append('close')
    class Engine:
        def connect(self):
            return Connection()
        def dispose(self):
            events.append('dispose')
    monkeypatch.setattr(implementation, 'create_engine', lambda *_args, **_kwargs: Engine())
    with pytest.raises(RuntimeError):
        with freeze_library(SimpleNamespace(effective_database_url='synthetic-not-used')):
            raise RuntimeError('SIMULATED CALLER FAILURE')
    # Both acquisition gate and session lease are released; physical disposal
    # happens even when the protected caller raises before producing an artifact.
    assert events[-3:] == ['invalidate', 'close', 'dispose']
    assert events.count('unlock') == 2
    assert events.count('close') == 1
