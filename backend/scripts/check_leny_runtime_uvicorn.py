"""Check two graceful Uvicorn lifespans against the configured ERP without inference."""
import json, os, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path

BACKEND=Path(__file__).resolve().parents[1]
OUTPUT=BACKEND.parent/'documentacion/evidencias/leny_runtime_uvicorn_20261102.json'
if OUTPUT.exists():raise SystemExit('Preserve existing evidence')
program="""import asyncio,sys,uvicorn
from pathlib import Path
async def main():
 server=uvicorn.Server(uvicorn.Config('main:app',host='127.0.0.1',port=18080,log_level='warning'))
 async def stop():
  while not Path(sys.argv[1]).exists(): await asyncio.sleep(.1)
  server.should_exit=True
 await asyncio.gather(server.serve(),stop())
asyncio.run(main())
"""
def status():
 result=subprocess.run([sys.executable,'-B',str(BACKEND/'scripts/run_leny_rag_worker.py'),'--status'],cwd=BACKEND,
                       capture_output=True,text=True,timeout=15)
 if result.returncode:raise RuntimeError('Worker status unavailable')
 return json.loads(result.stdout)['worker_available']
def wait_for(predicate,seconds=30):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  try:
   if predicate():return
  except (OSError,ValueError):pass
  time.sleep(.3)
 raise RuntimeError('Lifecycle check timed out')
def health():
 with urllib.request.urlopen('http://127.0.0.1:18080/health',timeout=2) as result:return result.status==200
def ollama():
 with urllib.request.urlopen('http://127.0.0.1:11434/api/tags',timeout=2) as result:return result.status==200
assert ollama() and not status(), 'Requires available preexisting Ollama and no external worker'
results=[]
with tempfile.TemporaryDirectory(prefix='bab-leny-lifespan-') as temp:
 for iteration in range(2):
  marker=Path(temp)/('stop-'+str(iteration))
  proc=subprocess.Popen([sys.executable,'-B','-c',program,str(marker)],cwd=BACKEND,
    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
  try:
   wait_for(health);wait_for(status)
   marker.touch()
   proc.wait(timeout=35)
   if proc.returncode:raise RuntimeError('Backend exited unexpectedly')
   wait_for(lambda:not status())
   assert ollama()
   results.append({'worker_started':True,'worker_stopped':True,'external_ollama_preserved':True})
  finally:
   if proc.poll() is None:
    marker.touch()
    try:proc.wait(timeout=35)
    except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=10)
OUTPUT.write_text(json.dumps({'cycles':results,'actual_uvicorn_reload_flag_tested':False,
 'database':'configured ERP','port':18080,'models_invoked':False},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'cycles':results,'actual_uvicorn_reload_flag_tested':False,'models_invoked':False}))
