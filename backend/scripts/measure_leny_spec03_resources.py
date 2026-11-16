"""Three idle/ambient resource samples, not inference peak attribution."""
import ctypes
from ctypes import wintypes
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import subprocess
import time


class Memory(ctypes.Structure):
    _fields_=[('length',wintypes.DWORD),('load',wintypes.DWORD),
        *[(name,ctypes.c_ulonglong) for name in ('total','available','page_total','page_available','virtual_total','virtual_available','extended')]]


def sample():
    memory=Memory();memory.length=ctypes.sizeof(memory)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):raise RuntimeError('Memory unavailable')
    result=dict(at=datetime.now(timezone.utc).isoformat(),total_ram_bytes=memory.total,available_ram_bytes=memory.available)
    command="Get-Process | Where-Object {$_.ProcessName -match '^(python|uvicorn|ollama.*)$'} | Select-Object ProcessName,Id,WorkingSet64 | ConvertTo-Json -Compress"
    processes=subprocess.run(['powershell.exe','-NoProfile','-Command',command],capture_output=True,text=True,timeout=10,check=True)
    result['process_working_sets']=json.loads(processes.stdout) if processes.stdout.strip() else []
    nvidia=shutil.which('nvidia-smi')
    if nvidia:
        gpu=subprocess.run([nvidia,'--query-gpu=memory.used,memory.total','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=10)
        if gpu.returncode==0:
            result['gpu_global_mib']=[dict(zip(('used','total'),map(int,line.split(',')))) for line in gpu.stdout.strip().splitlines()]
    return result


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--continuity',action='store_true')
    args=parser.parse_args()
    samples=[]
    for index in range(3):
        samples.append(sample())
        if index<2:time.sleep(1)
    filename='leny_spec031_resources.json' if args.continuity else 'leny_spec03_resources.json'
    target=Path(__file__).resolve().parents[2]/'documentacion/evidencias'/filename
    target.write_text(json.dumps(dict(scope='ambient_snapshots_not_inference_peaks',samples=samples,
        cold_warm_comparison_available=False,attributable_inference_memory=None),indent=2),encoding='utf-8')
    print('Ambient resource snapshots:',len(samples),'No inference or service changes.')
