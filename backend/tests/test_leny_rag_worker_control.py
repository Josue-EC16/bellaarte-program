"""Regression: heartbeat and main worker cannot fail each other's metadata lease."""
import threading
import time
from contextlib import nullcontext
import hashlib
from io import BytesIO
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.services.leny_document_storage import DocumentError
from app.services.leny_rag_worker import RagWorker
from app.services.leny_rag_common import RagError


def controller():
    worker = RagWorker.__new__(RagWorker)
    worker.metadata_lock = threading.RLock()
    return worker


def test_heartbeat_and_main_mutations_are_serialized():
    worker = controller()
    resource = threading.Lock()
    barrier = threading.Barrier(3)
    completed, errors = [], []
    def mutate(name):
        barrier.wait()
        def operation():
            if not resource.acquire(blocking=False):
                raise AssertionError('Worker contended with its own heartbeat')
            try:
                time.sleep(0.02)
                completed.append(name)
            finally:
                resource.release()
        try:worker.write(operation)
        except Exception as error:errors.append(error)
    threads = [threading.Thread(target=mutate,args=(name,)) for name in ('heartbeat','checkpoint')]
    for thread in threads:thread.start()
    barrier.wait()
    for thread in threads:thread.join(timeout=2)
    assert not errors and sorted(completed)==['checkpoint','heartbeat']


@pytest.mark.parametrize('code',['DOCUMENT_BUSY','BACKUP_IN_PROGRESS'])
def test_short_external_library_mutation_is_retried(code,monkeypatch):
    worker = controller()
    monkeypatch.setattr('app.services.leny_rag_worker.time.sleep',lambda _:None)
    attempts=[]
    def operation():
        attempts.append(1)
        if len(attempts)<3:raise DocumentError(code,'Synthetic occupied gate.',429)
        return 'checkpoint committed'
    assert worker.write(operation)=='checkpoint committed'
    assert len(attempts)==3


def test_lost_lease_is_never_retried_as_library_contention():
    attempts=[]
    def operation():
        attempts.append(1)
        raise DocumentError('DOCUMENT_LOCK_LOST','Synthetic lost lease.',503)
    with pytest.raises(DocumentError):controller().write(operation)
    assert len(attempts)==1


def test_stop_marker_cancels_active_processing_before_more_work(tmp_path):
    worker = controller()
    worker.stop_file = tmp_path/'owned-stop'
    worker.stop_file.touch()
    worker.stop = threading.Event()
    with pytest.raises(DocumentError) as stopped:worker.check()
    assert stopped.value.code=='RAG_CANCELLED' and worker.stop.is_set()


def processing_worker(tmp_path, monkeypatch):
    """Exercise orchestration without constructing services or contacting providers."""
    worker = controller()
    worker.stop = threading.Event()
    worker.stop_file = tmp_path/'manual.stop'
    worker.shutdown_file = tmp_path/'backend.shutdown'
    worker.heartbeat_error = None
    worker.mutex = threading.Lock()
    worker.lease = Mock()
    worker.id = 'synthetic-worker'
    worker.claim_started = time.monotonic()
    worker.logger = logging.getLogger(__name__)
    worker.settings = SimpleNamespace(
        leny_rag_job_seconds=60, leny_rag_min_ram_bytes=1,
        leny_rag_min_resident_ram_bytes=1, leny_rag_min_free_bytes=1,
        leny_documents_max_file_bytes=1024, leny_rag_batch_size=1,
    )
    content = b'synthetic PDF bytes; extraction is replaced'
    worker.claim = dict(id='job', token='claim-token', indexation_id='index',
                        media_type='application/pdf', storage_key='synthetic',
                        size_bytes=len(content), sha256=hashlib.sha256(content).hexdigest())
    documents = SimpleNamespace(lock=lambda: nullcontext(),
        storage=SimpleNamespace(root=tmp_path, open=lambda _key: BytesIO(content)),
        engine=Mock())
    worker.service = SimpleNamespace(documents=documents, check=Mock(),
        progress=Mock(), fragments=Mock(), pending_fragments=Mock(return_value=[]),
        heartbeat=Mock(), defer=Mock(), fail=Mock(), finish=Mock(),
        require_enabled=Mock(), register=Mock(), stopped=Mock(), claim=Mock())
    provider = SimpleNamespace(owned_model=False,
        embed=AsyncMock(return_value=[[1.0]]), verify=AsyncMock(), release=AsyncMock())
    worker.provider_factory = lambda: provider
    ai_lease = Mock()
    worker.coordinator = SimpleNamespace(acquire=Mock(return_value=ai_lease), engine=Mock())
    monkeypatch.setattr('app.services.leny_rag_worker.available_ram', lambda: 1024)
    monkeypatch.setattr('app.services.leny_rag_worker.shutil.disk_usage',
                        lambda _root: SimpleNamespace(free=1024))
    monkeypatch.setattr('app.services.leny_rag_extraction.extract_document',
                        lambda *_args: {'units': [], 'coverage': {}})
    monkeypatch.setattr('app.services.leny_rag_chunking.fragment_units', lambda *_args: ['fragment'])
    return worker, provider, ai_lease


def test_private_shutdown_is_distinct_from_manual_cancellation(tmp_path):
    worker = controller()
    worker.stop = threading.Event()
    worker.stop_file = tmp_path/'manual.stop'
    worker.shutdown_file = tmp_path/'backend.shutdown'
    worker.shutdown_file.touch()
    with pytest.raises(RagError) as stopped:
        worker.check()
    assert stopped.value.code == 'RAG_WORKER_SHUTDOWN'
    assert worker.stop.is_set()
    assert not worker.stop_file.exists()


@pytest.mark.parametrize('marker,expected_method,code', [
    ('shutdown_file', 'defer', 'RAG_WORKER_SHUTDOWN'),
    ('stop_file', 'fail', 'RAG_CANCELLED'),
])
def test_shutdown_requeues_but_manual_stop_cancels_before_inference(
        tmp_path, monkeypatch, marker, expected_method, code):
    worker, provider, _ = processing_worker(tmp_path, monkeypatch)
    claim = worker.claim
    def interrupted_extraction(_copy, _directory, _settings, check, _progress):
        getattr(worker, marker).touch()
        check()
        raise AssertionError('Processing continued after stop')
    monkeypatch.setattr('app.services.leny_rag_extraction.extract_document', interrupted_extraction)

    worker.process(claim, tmp_path)

    getattr(worker.service, expected_method).assert_called_once_with(claim, code)
    getattr(worker.service, 'fail' if expected_method == 'defer' else 'defer').assert_not_called()
    worker.service.finish.assert_not_called()
    worker.coordinator.acquire.assert_not_called()
    provider.embed.assert_not_awaited()
    worker.service.heartbeat.assert_not_called()
    assert list(tmp_path.iterdir()) == [getattr(worker, marker)]


def test_shutdown_drains_confirmed_embedding_before_requeue_and_release(tmp_path, monkeypatch):
    worker, provider, ai_lease = processing_worker(tmp_path, monkeypatch)
    claim = worker.claim
    async def completed_embedding(_texts):
        worker.shutdown_file.touch()
        return [[1.0]]
    provider.embed.side_effect = completed_embedding

    worker.process(claim, tmp_path)

    worker.service.defer.assert_called_once_with(claim, 'RAG_WORKER_SHUTDOWN')
    worker.service.fail.assert_not_called()
    assert [call.kwargs for call in worker.service.heartbeat.call_args_list] == [
        {'provider_inflight': True}, {'provider_inflight': False},
    ]
    provider.release.assert_awaited_once()
    ai_lease.close.assert_called_once()
    worker.service.finish.assert_not_called()


def test_uncertain_embedding_preserves_quarantine_during_backend_shutdown(tmp_path, monkeypatch):
    worker, provider, ai_lease = processing_worker(tmp_path, monkeypatch)
    claim = worker.claim
    async def interrupted_embedding(_texts):
        worker.shutdown_file.touch()
        raise RagError('RAG_PROVIDER_TIMEOUT', uncertain=True)
    provider.embed.side_effect = interrupted_embedding

    worker.process(claim, tmp_path)

    worker.service.defer.assert_not_called()
    worker.service.fail.assert_called_once_with(claim, 'RAG_PROVIDER_TIMEOUT')
    worker.service.heartbeat.assert_called_with(worker.id, provider_inflight=True,
        unsafe_reason='RAG_INFERENCE_UNCERTAIN')
    assert not any(call.kwargs.get('provider_inflight') is False
                   for call in worker.service.heartbeat.call_args_list)
    provider.release.assert_not_awaited()
    ai_lease.close.assert_called_once()
    assert worker.stop.is_set()
    worker.service.finish.assert_not_called()


def test_shutdown_joins_heartbeat_before_stopped_metadata_and_lease_close(tmp_path, monkeypatch):
    worker, _, _ = processing_worker(tmp_path, monkeypatch)
    events = []
    class HeartbeatThread:
        def start(self):
            events.append('heartbeat-start')
        def join(self):
            # No timeout: closing the lease requires completion, not elapsed time.
            events.append('heartbeat-joined')
    monkeypatch.setattr('app.services.leny_rag_worker.threading.Thread',
                        lambda **_kwargs: HeartbeatThread())
    worker.acquire = Mock()
    worker.working_root = lambda: tmp_path
    worker.service.stopped.side_effect = lambda _identity: events.append('stopped-metadata')
    worker.lease.close.side_effect = lambda: events.append('lease-close')
    worker.service.documents.engine.dispose.side_effect = lambda: events.append('documents-dispose')
    worker.coordinator.engine.dispose.side_effect = lambda: events.append('coordinator-dispose')
    worker.shutdown_file.touch()

    worker.run(shutdown_file=worker.shutdown_file)

    assert events == ['heartbeat-start', 'heartbeat-joined', 'stopped-metadata',
                      'lease-close', 'documents-dispose', 'coordinator-dispose']
    worker.service.claim.assert_not_called()
