"""Restart only the identified original Uvicorn tree while LENY is idle."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import httpx
from sqlalchemy import text

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)
from app.core.config import Settings
from app.services.leny_coordination import PostgresCoordinator
from run_leny_authenticated_review import ROOT, prepare, save


def restart():
    prepare()
    settings = Settings(_env_file=BACKEND/'.env')
    command = ('Get-CimInstance Win32_Process | Where-Object {$_.Name -eq "uvicorn.exe"} | '
               'Select-Object ProcessId,ExecutablePath,CommandLine | ConvertTo-Json -Compress')
    result = subprocess.run(['powershell.exe', '-NoProfile', '-Command', command],
                            capture_output=True, text=True, check=True, timeout=15)
    processes = json.loads(result.stdout) if result.stdout.strip() else []
    processes = processes if isinstance(processes, list) else [processes]
    matching = [p for p in processes if Path(p['ExecutablePath']).resolve() ==
                (BACKEND/'venv/Scripts/uvicorn.exe').resolve() and 'main:app --reload' in p['CommandLine']]
    if len(matching) != 1:
        record = ROOT/'backend-process.json'
        owned_pid = int(json.loads(record.read_text(encoding='utf-8'))['pid'])
        command = 'Get-CimInstance Win32_Process -Filter "ProcessId = '+str(owned_pid)+'" | Select-Object ProcessId,ExecutablePath,CommandLine | ConvertTo-Json -Compress'
        result = subprocess.run(['powershell.exe', '-NoProfile', '-Command', command],
                                capture_output=True, text=True, check=True, timeout=15)
        process = json.loads(result.stdout)
        if (not process or 'uvicorn' not in process['CommandLine'] or 'main:app' not in process['CommandLine']
                or str(BACKEND).lower() not in process['CommandLine'].lower()):
            raise RuntimeError('Owned original backend identity mismatch; no process stopped')
        matching = [process]
    coordinator = PostgresCoordinator(settings.effective_database_url)
    lease = coordinator.acquire()
    try:
        with coordinator.engine.connect() as db:
            if db.scalar(text("SELECT EXISTS(SELECT 1 FROM leny.rag_trabajos WHERE status IN ('queued','running'))")):
                raise RuntimeError('Document processing active; no process stopped')
            if db.scalar(text("SELECT EXISTS(SELECT 1 FROM pg_stat_activity WHERE datname=current_database() "
                              "AND pid<>pg_backend_pid() AND state IN ('active','idle in transaction') "
                              "AND backend_type='client backend')")):
                raise RuntimeError('Other database operation active; no process stopped')
        lease.check()
        old_pid = int(matching[0]['ProcessId'])
        subprocess.run(['taskkill.exe', '/PID', str(old_pid), '/T', '/F'],
                       check=True, capture_output=True, timeout=15)
        environment = dict(os.environ, WATCHFILES_FORCE_POLLING='true', PYTHONDONTWRITEBYTECODE='1',
                           PYTHONPATH=str(BACKEND), DATABASE_URL=settings.effective_database_url)
        for key in list(environment):
            if key.startswith('TEST_'):
                environment.pop(key)
        stamp = time.strftime('%Y%m%d-%H%M%S')
        with (ROOT/('backend-'+stamp+'.out.log')).open('wb') as stdout, (ROOT/('backend-'+stamp+'.err.log')).open('wb') as stderr:
            child = subprocess.Popen([sys.executable, '-B', '-m', 'uvicorn', 'main:app', '--host', '127.0.0.1',
                '--port', '8000'], cwd=BACKEND, env=environment,
                stdout=stdout, stderr=stderr, creationflags=subprocess.CREATE_NO_WINDOW)
        save(ROOT/'backend-process.json', {'pid': child.pid, 'previous_pid': old_pid, 'started': time.time(),
                                          'repository': str(BACKEND.parent), 'polling_reload': False})
    finally:
        lease.close()
        coordinator.engine.dispose()
    deadline = time.monotonic()+45
    while time.monotonic() < deadline:
        try:
            if httpx.get('http://127.0.0.1:8000/health', trust_env=False, timeout=2).status_code == 200:
                print('Backend original reiniciado; salud200; PID supervisor', child.pid)
                return
        except httpx.HTTPError:
            pass
        time.sleep(1)
    raise RuntimeError('Backend health not confirmed; inspect private runtime logs')


if __name__ == '__main__':
    restart()
