"""Native Windows lifecycle smoke: synthetic children only; no ERP DB or LLM.

Run separately from run_base_tests, whose policy forbids starting processes.
Creates only its own temporary files/children and never stops an existing app.
"""
from __future__ import annotations

import argparse
import asyncio
import ctypes
from ctypes import wintypes as w
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import socket
import sys
from tempfile import TemporaryDirectory
import time

BACKEND=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BACKEND))
from app.services.leny_runtime_process import WindowsChild,RuntimeLease


def wait_until(predicate):
    deadline=time.monotonic()+10
    while time.monotonic()<deadline:
        if predicate():return
        time.sleep(.05)
    raise RuntimeError('NATIVE_CHECK_TIMEOUT')


def process_handle(pid):
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];kernel.OpenProcess.restype=w.HANDLE
    kernel.WaitForSingleObject.argtypes=[w.HANDLE,w.DWORD]
    kernel.CloseHandle.argtypes=[w.HANDLE]
    handle=kernel.OpenProcess(0x100000,False,pid)
    if not handle:raise RuntimeError('NATIVE_CHILD_HANDLE_UNAVAILABLE')
    return kernel,handle


async def check_owned_ollama(root):
    """Installed engine on a disposable loopback port/model directory; no model load."""
    from app.core.config import Settings
    from app.services.leny_runtime import LenyRuntime
    with socket.socket() as reservation:
        reservation.bind(('127.0.0.1',0))
        port=reservation.getsockname()[1]
    models=root/'empty-models';models.mkdir()
    previous=os.environ.get('OLLAMA_MODELS')
    os.environ['OLLAMA_MODELS']=str(models)
    config=Settings(_env_file=None,environment='development',
        database_url='postgresql://synthetic:unit-only@127.0.0.1:1/not_a_database',
        leny_rag_enabled=False,leny_documents_enabled=False,leny_ollama_url='http://127.0.0.1:'+str(port))
    service=LenyRuntime(config,root=root/'owned-runtime')
    try:
        await service.start()
        assert service.owner and service.ollama is not None and await service._healthy()
        import httpx
        async with httpx.AsyncClient(trust_env=False,timeout=5) as client:
            assert (await client.get(config.leny_ollama_url+'/api/tags')).json()['models']==[]
            assert (await client.get(config.leny_ollama_url+'/api/ps')).json()['models']==[]
        child=service.ollama
        await service.close()
        assert child.poll() is not None and not await service._healthy()
        return True
    finally:
        await service.close()
        if previous is None:os.environ.pop('OLLAMA_MODELS',None)
        else:os.environ['OLLAMA_MODELS']=previous


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--owned-ollama',action='store_true',help='Also test installed Ollama on a disposable port without models')
    args=parser.parse_args()
    if args.output.exists():raise ValueError('Preserve existing evidence')
    if os.name!='nt':raise RuntimeError('Windows required')
    env={k:v for k,v in os.environ.items() if k.upper() in
         {'SYSTEMROOT','WINDIR','SYSTEMDRIVE','PATH','USERPROFILE','LOCALAPPDATA','TEMP','TMP'}}
    env.update(PYTHONPATH=str(BACKEND),PYTHONDONTWRITEBYTECODE='1',LENY_SYNTHETIC_UNICODE='niña')
    results={}
    with TemporaryDirectory(prefix='bab-leny-native-') as temporary:
        root=Path(temporary)
        a,b=RuntimeLease(root/'runtime.lock'),RuntimeLease(root/'runtime.lock')
        try:
            assert a.acquire() and not b.acquire()
            a.close()
            assert b.acquire()
            results['exclusive_lease_releases_without_deleting_lock_file']=True
        finally:a.close();b.close()
        signal=root/'proceso con espacios.json'
        program="""import os,sys,subprocess,time,json,pathlib
child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
pathlib.Path(sys.argv[1]).write_text(json.dumps({'child':child.pid,'value':os.environ['LENY_SYNTHETIC_UNICODE']}),encoding='utf-8')
time.sleep(60)
"""
        process=WindowsChild([sys.executable,'-B','-c',program,str(signal)],cwd=root,env=env)
        kernel=handle=None
        try:
            wait_until(signal.is_file)
            data=json.loads(signal.read_text('utf-8'))
            assert data['value']=='niña' and process.poll() is None
            kernel,handle=process_handle(data['child'])
            process.close();process.close()
            assert kernel.WaitForSingleObject(handle,5000)==0 and process.poll() is not None
            results['suspended_start_unicode_paths_environment_venv_and_descendant_cleanup']=True
        finally:
            process.close()
            if handle:kernel.CloseHandle(handle)
        signal=root/'owned-child.json'
        controller="""import sys,pathlib,time,json
from app.services.leny_runtime_process import WindowsChild
p=WindowsChild([sys.executable,'-c','import time;time.sleep(60)'],cwd=pathlib.Path(sys.argv[1]).parent,env=dict(__import__('os').environ))
pathlib.Path(sys.argv[1]).write_text(json.dumps({'pid':p.pid}),encoding='utf-8')
time.sleep(60)
"""
        parent=subprocess.Popen([getattr(sys,'_base_executable',sys.executable),'-B','-c',controller,str(signal)],
            cwd=root,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
        kernel=handle=None
        try:
            wait_until(signal.is_file)
            kernel,handle=process_handle(json.loads(signal.read_text())['pid'])
            parent.terminate();parent.wait(timeout=5)
            assert kernel.WaitForSingleObject(handle,5000)==0
            results['kill_on_close_removes_owned_child_when_parent_dies']=True
        finally:
            if parent.poll() is None:parent.terminate();parent.wait(timeout=5)
            if handle:kernel.CloseHandle(handle)
        if args.owned_ollama:
            results['installed_ollama_owned_start_and_stop_empty_models']=asyncio.run(check_owned_ollama(root))
    report=dict(scope='native_windows_synthetic_children_only',created_utc=datetime.now(timezone.utc).isoformat(),
        results=results,database_accessed=False,ollama_invoked=args.owned_ollama,models_invoked=False,foreign_processes_stopped=False)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':
    try:main()
    except Exception as error:
        print(json.dumps({'failed':type(error).__name__,'details_withheld':True}),file=sys.stderr)
        raise SystemExit(1)
