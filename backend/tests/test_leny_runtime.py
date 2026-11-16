"""Owned/borrowed lifecycle behavior; all HTTP/process/DB boundaries simulated."""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from app.core.config import Settings
from app.services.leny_runtime import LenyRuntime, valid_shutdown_file


def config(**changes):
    return Settings(_env_file=None,environment='development',
        database_url='postgresql://synthetic:unit-only@127.0.0.1:1/not_a_database',
        leny_enabled=True,leny_rag_enabled=True,leny_documents_enabled=True,**changes)


class Lease:
    def __init__(self,available=True):self.available,self.closed=available,False
    def acquire(self):return self.available
    def close(self):self.closed=True


def runtime(tmp_path,monkeypatch,*,existing_ollama=True,existing_worker=False,lease=None,**settings):
    owned,events=[],[]
    lease=lease or Lease()
    def factory(command,**options):
        class Child:
            def __init__(self):self.closed=False;self.ended=False
            def poll(self):
                if '--shutdown-file' in command and Path(command[-1]).exists():
                    events.append('worker_finished')
                    self.ended=True
                return 0 if self.ended or self.closed else None
            def close(self):
                events.append('worker_closed' if '--shutdown-file' in command else 'ollama_closed')
                self.closed=True
        item=Child();owned.append((item,command,options));return item
    def http(request):
        assert request.method=='GET' and request.url.path=='/api/tags'
        online=existing_ollama or any('serve' in args and not process.closed for process,args,_ in owned)
        return httpx.Response(200,json={'models':[]}) if online else httpx.Response(503)
    service=LenyRuntime(config(**settings),root=tmp_path,process_factory=factory,
        transport=httpx.MockTransport(http))
    def prepare():service.lease=lease
    monkeypatch.setattr(service,'_prepare',prepare)
    monkeypatch.setattr(service,'_worker_exists',lambda:existing_worker)
    monkeypatch.setattr(service,'_ollama_executable',lambda:str(tmp_path/'ollama.exe'))
    return service,owned,events,lease


def test_existing_ollama_is_borrowed_and_only_our_worker_is_stopped(tmp_path,monkeypatch):
    service,owned,events,lease=runtime(tmp_path,monkeypatch)
    async def scenario():
        await service.start()
        assert service.ollama is None and service.worker is not None
        await service.close(); await service.close()
    asyncio.run(scenario())
    assert len(owned)==1 and owned[0][0].closed and lease.closed
    assert events==['worker_finished','worker_finished','worker_closed']
    assert not service.worker_stop.exists()


def test_owned_ollama_closes_only_after_the_worker_finishes(tmp_path,monkeypatch):
    service,owned,events,lease=runtime(tmp_path,monkeypatch,existing_ollama=False)
    async def scenario():
        await service.start()
        assert len(owned)==2 and service.ollama is not None
        await service.close()
    asyncio.run(scenario())
    assert all(process.closed for process,_,_ in owned) and lease.closed
    assert events.index('worker_finished')<events.index('worker_closed')<events.index('ollama_closed')


def test_existing_manual_worker_is_not_duplicated_or_signalled(tmp_path,monkeypatch):
    service,owned,events,lease=runtime(tmp_path,monkeypatch,existing_worker=True)
    global_stop=tmp_path/'worker.stop';global_stop.write_text('manual operator control')
    async def scenario():
        await service.start();await service.close()
    asyncio.run(scenario())
    assert not owned and not events and lease.closed
    assert global_stop.read_text()=='manual operator control'


def test_competing_backend_waits_for_lease_before_starting_any_child(tmp_path,monkeypatch):
    lease=Lease(False)
    service,owned,_,_=runtime(tmp_path,monkeypatch,lease=lease,existing_ollama=False)
    async def scenario():
        await service.start()
        assert not owned
        lease.available=True
        await service._tick()
        assert len(owned)==2
        await service.close()
    asyncio.run(scenario())


def test_partial_start_failure_releases_only_owned_server_and_lease(tmp_path,monkeypatch):
    service,owned,events,lease=runtime(tmp_path,monkeypatch,existing_ollama=False)
    def failing_worker_probe():raise RuntimeError('unit synthetic DB unavailable')
    monkeypatch.setattr(service,'_worker_exists',failing_worker_probe)
    asyncio.run(service.start())
    assert len(owned)==1 and owned[0][0].closed and lease.closed
    assert events==['ollama_closed']


@pytest.mark.parametrize('settings',[{'environment':'test'},{'leny_runtime_autostart':False},{'leny_enabled':False}])
def test_no_services_are_started_when_disabled_or_in_test_environment(tmp_path,monkeypatch,settings):
    # Build config separately because the helper's defaults intentionally enable development.
    service,owned,_,_=runtime(tmp_path,monkeypatch)
    for key,value in settings.items():setattr(service.config,key,value)
    monkeypatch.setattr(service,'_prepare',lambda:pytest.fail('runtime unexpectedly prepared'))
    asyncio.run(service.start())
    asyncio.run(service.close())
    assert not owned


def test_marker_failure_still_closes_worker_before_owned_ollama(tmp_path,monkeypatch):
    service,owned,events,lease=runtime(tmp_path,monkeypatch,existing_ollama=False)
    async def scenario():
        await service.start()
        monkeypatch.setattr('app.services.leny_runtime._check_path',lambda _:(_ for _ in ()).throw(OSError('synthetic')))
        with pytest.raises(OSError):await service.close()
    asyncio.run(scenario())
    assert all(p.closed for p,_,_ in owned) and lease.closed
    assert events==['worker_closed','ollama_closed']


def test_missing_ollama_executable_degrades_safely_without_spawning(tmp_path,monkeypatch):
    service,owned,_,lease=runtime(tmp_path,monkeypatch,existing_ollama=False)
    monkeypatch.setattr(service,'_ollama_executable',lambda:(_ for _ in ()).throw(RuntimeError('missing')))
    asyncio.run(service.start())
    assert not owned and lease.closed


def test_ollama_child_never_receives_db_smtp_jwt_or_model_requests(tmp_path,monkeypatch):
    monkeypatch.setenv('DB_PASS','synthetic-private-value')
    monkeypatch.setenv('SMTP_PASSWORD','synthetic-private-value')
    monkeypatch.setenv('JWT_SECRET_KEY','synthetic-private-value')
    monkeypatch.setenv('OLLAMA_HOST','0.0.0.0:5555')
    service,_,_,_=runtime(tmp_path,monkeypatch)
    env=service._environment()
    assert env['OLLAMA_HOST']=='127.0.0.1:11434'
    assert not any(key.startswith(('DB_','SMTP_','JWT_','DATABASE_')) for key in env)
    worker_env=service._environment(worker=True)
    assert worker_env['DATABASE_URL']==service.config.effective_database_url
    assert worker_env['LENY_RUNTIME_AUTOSTART']=='false'
    assert 'SMTP_PASSWORD' not in worker_env and 'JWT_SECRET_KEY' not in worker_env


def test_dead_owned_worker_is_replaced_without_touching_external_processes(tmp_path,monkeypatch):
    service,owned,_,_=runtime(tmp_path,monkeypatch)
    async def scenario():
        await service.start()
        old=service.worker;old.ended=True
        await service._tick()
        assert old.closed and service.worker is not old and len(owned)==2
        await service.close()
    asyncio.run(scenario())


def test_shutdown_path_cannot_point_to_global_or_foreign_files(monkeypatch,tmp_path):
    monkeypatch.setattr('app.services.leny_runtime.backend_runtime_root',lambda:tmp_path)
    assert valid_shutdown_file(tmp_path/('worker-'+'a'*32+'.stop'))
    assert not valid_shutdown_file(tmp_path/'worker.stop')
    assert not valid_shutdown_file(tmp_path.parent/('worker-'+'a'*32+'.stop'))
    assert not valid_shutdown_file(tmp_path/'worker-not-a-uuid.stop')


@pytest.mark.parametrize('fail_startup',[False,True])
def test_fastapi_lifespan_closes_owned_runtime_on_normal_exit_and_startup_failure(monkeypatch,fail_startup):
    from app import main
    events=[]
    class Runtime:
        def __init__(self,*_):pass
        async def start(self):events.append('runtime_start')
        async def close(self):events.append('runtime_close')
    @asynccontextmanager
    async def erp(_):
        events.append('erp_start')
        if fail_startup:raise RuntimeError('synthetic startup failure')
        try:yield
        finally:events.append('erp_close')
    monkeypatch.setattr('app.services.leny_runtime.LenyRuntime',Runtime)
    monkeypatch.setattr(main,'erp_lifespan',erp)
    app=SimpleNamespace(state=SimpleNamespace())
    async def scenario():
        async with main.app_lifespan(app):events.append('serving')
    if fail_startup:
        with pytest.raises(RuntimeError):asyncio.run(scenario())
        assert events==['runtime_start','erp_start','runtime_close']
    else:
        asyncio.run(scenario())
        assert events==['runtime_start','erp_start','serving','erp_close','runtime_close']


def test_fastapi_lifespan_cleanup_survives_cancellation(monkeypatch):
    from app import main
    closed=[]
    class Runtime:
        def __init__(self,*_):pass
        async def start(self):pass
        async def close(self):
            await asyncio.sleep(0)
            closed.append(True)
    @asynccontextmanager
    async def erp(_):yield
    monkeypatch.setattr('app.services.leny_runtime.LenyRuntime',Runtime)
    monkeypatch.setattr(main,'erp_lifespan',erp)
    async def scenario():
        async with main.app_lifespan(SimpleNamespace(state=SimpleNamespace())):
            raise asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):asyncio.run(scenario())
    assert closed==[True]
