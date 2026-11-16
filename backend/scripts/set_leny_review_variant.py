"""Controlled variant activation; changes only four LENY flags, then reloads.

Requires the existing generation lease. No DB writes, tools or model changes.
Configuration backups must already exist in the private review directory.
"""
import argparse
import os
from pathlib import Path
import sys
import subprocess
import json
import httpx
import time

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)
from app.core.config import Settings
from app.services.leny_coordination import PostgresCoordinator

VARIANTS = {
    'B0': (False, False, False, False),
    'A3': (True, False, False, False),
    'A1': (True, True, False, False),
    'A2': (True, False, True, False),
    'A4': (True, False, False, True),
    # Two real followup experiments repeated explained steps. Keep that
    # experimental retrieval hint disabled in the operational candidate.
    'combined': (True, True, True, False),
}
KEYS = ('LENY_RAG_LINKED_SUPPORT', 'LENY_RAG_SECTION_CONTEXT',
        'LENY_RAG_SOURCE_COVERAGE', 'LENY_RAG_FOLLOWUP_CONTEXT')


def application_pids():
    record = Path(os.environ['LOCALAPPDATA'])/'BAB_VDOS'/'leny-original-integration'/'backend-process.json'
    root = int(json.loads(record.read_text(encoding='utf-8'))['pid'])
    command = ('$todo=@('+str(root)+'); $found=@(); for($level=0;$level -lt 6 -and $todo.Count -gt 0;$level++) {'
               '$next=@(); foreach($parent in $todo) {'
               '$children=Get-CimInstance Win32_Process -Filter "ParentProcessId = $parent"; '
               'foreach($child in $children) { $next+= $child.ProcessId; '
               'if($child.CommandLine -match "spawn_main") {$found+=$child.ProcessId} }}; '
               '$todo=$next }; ConvertTo-Json -Compress -InputObject @($found)')
    result = subprocess.run(['powershell.exe', '-NoProfile', '-Command', command],
                            capture_output=True, text=True, check=True, timeout=10)
    data = json.loads(result.stdout) if result.stdout.strip() else []
    return set(data if isinstance(data, list) else [data])


def activate(name):
    settings = Settings(_env_file=BACKEND/'.env')
    if (settings.leny_num_ctx, settings.leny_num_predict, settings.leny_temperature,
            settings.leny_rag_dimension) != (4096, 768, 0, 1024):
        raise RuntimeError('Unexpected resource configuration')
    private = Path(os.environ['LOCALAPPDATA'])/'BAB_VDOS'/'leny-original-integration'/'backups'
    if not any(private.glob('*/manifest.json')):
        raise RuntimeError('Private rollback backup required')
    coordinator = PostgresCoordinator(settings.effective_database_url)
    lease = coordinator.acquire()
    try:
        path = BACKEND/'.env'
        lines = path.read_text(encoding='utf-8').splitlines()
        changes = dict(zip(KEYS, VARIANTS[name]))
        lines = [line for line in lines if line.partition('=')[0].strip() not in changes]
        lines.extend(key+'='+str(value).lower() for key, value in changes.items())
        lease.check()
        path.write_text('\n'.join(lines)+'\n', encoding='utf-8')
        # Existing Uvicorn --reload owns its children and graceful shutdown.
        entrypoint = BACKEND/'app/services/leny_rag_synthesis.py'
        stamp = max(time.time(), entrypoint.stat().st_mtime+2)
        os.utime(entrypoint, (stamp, stamp))
    finally:
        lease.close()
        coordinator.engine.dispose()
    # Windows console-less --reload cannot reliably deliver CTRL_C_EVENT.
    # Replace only the verified owned backend, with no in-flight generation.
    from restart_leny_review_backend import restart
    restart()
    print('Variante recargada:', name, 'proceso nuevo y salud200')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('variant', choices=VARIANTS)
    activate(parser.parse_args().variant)
