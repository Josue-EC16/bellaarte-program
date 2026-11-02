"""Own local LENY services for one FastAPI lifespan; borrow existing services.

No model preload, downloads, shell, migration, force-clear of inference state,
or stop-by-name. A private OS lease coordinates reload/multiple API processes.
"""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from app.services.leny_document_storage import _check_path, document_root, protect_directory
from app.services.leny_runtime_process import RuntimeLease, WindowsChild

BACKEND=Path(__file__).resolve().parents[2]
logger=logging.getLogger(__name__)


def backend_runtime_root():
    return Path(os.environ['LOCALAPPDATA'])/'BAB_VDOS/leny-backend-runtime'


def valid_shutdown_file(path):
    import re
    path=Path(path).absolute()
    _check_path(path)
    return (path.parent==backend_runtime_root().absolute()
            and re.fullmatch(r'worker-[a-f0-9]{32}\.stop',path.name) is not None)


class LenyRuntime:
    def __init__(self, config, *, process_factory=WindowsChild,
                 lease_factory=RuntimeLease, transport=None, root=None):
        self.config = config
        self.process_factory, self.lease_factory = process_factory, lease_factory
        self.transport, self.root = transport, Path(root) if root else backend_runtime_root()
        self.worker_stop=self.root/('worker-'+uuid4().hex+'.stop')
        self.lease=None
        self.owner=False
        self.ollama=self.worker=None
        self.monitor=None
        self.stopping=False
        self.last_status=None

    def _status(self, code):
        if code!=self.last_status:
            logger.info(code)
            self.last_status=code

    def _prepare(self):
        # Same fixed local/private-root policy as the existing document runtime.
        document_root(SimpleNamespace(leny_documents_root=str(self.root)))
        _check_path(self.root)
        marker=self.root/'.leny-backend-runtime'
        if self.root.exists() and not marker.exists() and any(self.root.iterdir()):
            raise RuntimeError('LENY_RUNTIME_PRIVATE_ROOT_REQUIRED')
        self.root.mkdir(parents=True,exist_ok=True)
        protect_directory(self.root)
        marker.touch(exist_ok=True)
        self.lease=self.lease_factory(self.root/'backend.lock')

    def _environment(self, *, worker=False):
        allowed={'SYSTEMROOT','WINDIR','SYSTEMDRIVE','PATH','PATHEXT','COMSPEC','USERPROFILE',
                 'LOCALAPPDATA','APPDATA','PROGRAMFILES','PROGRAMFILES(X86)','TEMP','TMP',
                 'CUDA_VISIBLE_DEVICES','HIP_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES'}
        env={key:value for key,value in os.environ.items() if key.upper() in allowed
             or (not worker and key.upper().startswith('OLLAMA_'))}
        if worker:
            # Own worker uses the same effective LENY/DB configuration, not stale
            # terminal defaults. No secret is passed in an argument or a log.
            for name in type(self.config).model_fields:
                if name.startswith('leny_') or name in ('environment','backup_dir','backup_timezone'):
                    value=getattr(self.config,name)
                    if value is not None:
                        env[name.upper()]=str(value).lower() if isinstance(value,bool) else str(value)
            env['DATABASE_URL']=self.config.effective_database_url
            env['LENY_RUNTIME_AUTOSTART']='false'
            env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',PYTHONUTF8='1')
        else:
            parsed=urlsplit(self.config.leny_ollama_url)
            host=parsed.hostname
            if host not in {'127.0.0.1','localhost','::1'} or parsed.scheme!='http':
                raise RuntimeError('LENY_RUNTIME_LOOPBACK_REQUIRED')
            env['OLLAMA_HOST']=('['+host+']' if ':' in host else host)+':'+str(parsed.port or 80)
        return env

    async def _healthy(self):
        try:
            async with httpx.AsyncClient(base_url=self.config.leny_ollama_url,trust_env=False,
                    follow_redirects=False,transport=self.transport,timeout=1.5) as client:
                response=await client.get('/api/tags')
                return response.status_code==200 and isinstance(response.json().get('models'),list)
        except (httpx.HTTPError,ValueError,AttributeError,TypeError):
            return False

    def _ollama_executable(self):
        value=self.config.leny_ollama_executable or shutil.which('ollama')
        if not value:
            value=str(Path(os.environ['LOCALAPPDATA'])/'Programs/Ollama/ollama.exe')
        path=Path(value).resolve()
        _check_path(path)
        if not path.is_file() or path.suffix.lower()!='.exe':
            raise RuntimeError('LENY_RUNTIME_OLLAMA_NOT_INSTALLED')
        return str(path)

    async def _ensure_ollama(self):
        if self.ollama is not None and self.ollama.poll() is not None:
            await asyncio.to_thread(self.ollama.close)
            self.ollama=None
        if await self._healthy():
            self._status('LENY_RUNTIME_OLLAMA_OWNED' if self.ollama else 'LENY_RUNTIME_OLLAMA_EXTERNAL')
            return True
        if self.ollama is not None:
            return False
        executable=self._ollama_executable()
        self.ollama=self.process_factory([executable,'serve'],cwd=Path(executable).parent,env=self._environment())
        deadline=asyncio.get_running_loop().time()+self.config.leny_runtime_startup_seconds
        while not self.stopping and self.ollama.poll() is None:
            if await self._healthy():
                # Closing only this Job cannot affect a server that won a port race.
                if self.ollama.poll() is None:
                    self._status('LENY_RUNTIME_OLLAMA_OWNED')
                    return True
                break
            if asyncio.get_running_loop().time()>=deadline:
                break
            await asyncio.sleep(.2)
        await asyncio.to_thread(self.ollama.close)
        self.ollama=None
        self._status('LENY_RUNTIME_OLLAMA_UNAVAILABLE')
        return False

    def _worker_exists(self):
        # Consult the actual singleton lock, not a stale heartbeat; no content read.
        key=0x4C454E590201
        engine=create_engine(self.config.effective_database_url,poolclass=NullPool,hide_parameters=True,
            connect_args={'connect_timeout':3,'options':'-c default_transaction_read_only=on -c statement_timeout=2000',
                          'keepalives':1,'keepalives_idle':5,'keepalives_interval':2,'keepalives_count':2})
        try:
            with engine.connect() as db:
                return bool(db.scalar(text("SELECT EXISTS(SELECT 1 FROM pg_locks WHERE locktype='advisory' "
                    'AND database=(SELECT oid FROM pg_database WHERE datname=current_database()) '
                    'AND classid=:high AND objid=:low AND granted)'),{'high':key>>32,'low':key&0xffffffff}))
        finally:
            engine.dispose()

    async def _ensure_worker(self):
        if not (self.config.leny_rag_enabled and self.config.leny_documents_enabled):
            return
        if self.worker is not None:
            if self.worker.poll() is None:
                return
            await asyncio.to_thread(self.worker.close)
            self.worker=None
            self._status('LENY_RUNTIME_WORKER_EXITED_RETRYING')
        if await asyncio.to_thread(self._worker_exists):
            self._status('LENY_RUNTIME_WORKER_EXTERNAL')
            return
        self.worker=self.process_factory([sys.executable,'-B',str(BACKEND/'scripts/run_leny_rag_worker.py'),
            '--shutdown-file',str(self.worker_stop)],cwd=BACKEND,env=self._environment(worker=True))
        self._status('LENY_RUNTIME_WORKER_STARTED')

    async def _tick(self):
        if not self.owner:
            self.owner=self.lease.acquire()
            if not self.owner:
                self._status('LENY_RUNTIME_ANOTHER_BACKEND_OWNER')
                return
        if await self._ensure_ollama():
            await self._ensure_worker()

    async def _watch(self):
        while not self.stopping:
            await asyncio.sleep(5)
            try:
                await self._tick()
            except asyncio.CancelledError:
                raise
            except Exception:
                self._status('LENY_RUNTIME_RETRY_DEFERRED')

    async def start(self):
        if not self.config.leny_enabled or not self.config.leny_runtime_autostart or self.config.environment=='test':
            return
        try:
            self._prepare()
            await self._tick()
            self.monitor=asyncio.create_task(self._watch(),name='leny-owned-runtime')
        except asyncio.CancelledError:
            raise
        except Exception:
            # AI startup must not take the ERP down or print credentials/paths.
            logger.warning('LENY_RUNTIME_START_DEFERRED')
            await self.close()

    async def close(self):
        if self.stopping:
            return
        self.stopping=True
        try:
            if self.monitor:
                self.monitor.cancel()
                await asyncio.gather(self.monitor,return_exceptions=True)
            if self.worker is not None:
                # Private per-owner marker; never touch the standalone worker.stop.
                try:
                    _check_path(self.worker_stop)
                    self.worker_stop.touch(exist_ok=True)
                    deadline=asyncio.get_running_loop().time()+self.config.leny_runtime_shutdown_seconds
                    while self.worker.poll() is None and asyncio.get_running_loop().time()<deadline:
                        await asyncio.sleep(.1)
                    if self.worker.poll() is None:
                        logger.warning('LENY_RUNTIME_WORKER_FORCED_STOP_QUARANTINE_PRESERVED')
                finally:
                    await asyncio.to_thread(self.worker.close)
                    self.worker=None
        finally:
            try:
                if self.ollama is not None:
                    await asyncio.to_thread(self.ollama.close)
                    self.ollama=None
            finally:
                try:
                    if self.owner:
                        self.worker_stop.unlink(missing_ok=True)
                finally:
                    if self.lease:
                        self.lease.close()
                    self.owner=False
