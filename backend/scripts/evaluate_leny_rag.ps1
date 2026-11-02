# Native Windows wrapper. No service startup, migration, inference or DB access.
$ErrorActionPreference = 'Stop'
$ragBackend = Split-Path -Parent $PSScriptRoot
$ragPython = Join-Path $ragBackend 'venv\Scripts\python.exe'
$ragScript = Join-Path $PSScriptRoot 'evaluate_leny_rag.py'
& $ragPython -B $ragScript @args
exit $LASTEXITCODE
