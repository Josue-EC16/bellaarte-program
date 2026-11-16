param([ValidateSet('Start','Stop','Status')][string]$Action='Status')
$ErrorActionPreference='Stop'
$repoRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$backend=Join-Path $repoRoot 'backend'
$python=Join-Path $backend 'venv\Scripts\python.exe'
$runtime=[IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'BAB_VDOS\leny-rag-runtime'))
$stopFile=Join-Path $runtime 'worker.stop'
if (-not (Test-Path -LiteralPath (Join-Path $runtime '.leny-rag-runtime'))) { throw 'Prepare the owned private runtime first.' }
if ($Action -eq 'Stop') {
    [IO.File]::WriteAllText($stopFile,'stop')
    Write-Output 'Stop requested; current checkpoints and validated indices are preserved.'
    exit 0
}
if ($Action -eq 'Start') {
    if (Test-Path -LiteralPath $stopFile) { Remove-Item -LiteralPath $stopFile }
    # Duplicate starts are rejected by the worker PostgreSQL advisory lease.
    $arguments=@('-B',(Join-Path $PSScriptRoot 'run_leny_rag_worker.py'),'--stop-file',$stopFile)
    Start-Process -FilePath $python -ArgumentList $arguments -WorkingDirectory $backend -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtime 'worker-output.log') -RedirectStandardError (Join-Path $runtime 'worker-errors.log') | Out-Null
    Write-Output 'Worker launch requested. Use -Action Status to verify heartbeat.'
    exit 0
}
Push-Location -LiteralPath $backend
try { & $python -B (Join-Path $PSScriptRoot 'run_leny_rag_worker.py') --status }
finally { Pop-Location }
