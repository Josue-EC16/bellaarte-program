param([ValidateSet('Check','Serve')][string]$Action='Check',[switch]$Chat,[switch]$UiOnly,[switch]$ReleaseTestModel)
if($UiOnly -and (-not $Chat -or $Action -ne 'Serve')){throw 'UiOnly requires -Chat -Action Serve.'}
$ErrorActionPreference='Stop'
$repo=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$root=[IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'BAB_VDOS\postgresql-testing'))
$data=Join-Path $root 'data'
$manifestPath=Join-Path $root 'manifest.json'
$manifest=Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ([IO.Path]::GetFullPath($manifest.data_directory) -ne $data -or $manifest.port -ne 55432 -or $manifest.database -ne 'bab_vdos_testing') { throw 'Isolated identity rejected.' }
function Read-Secret([string]$value) {
    $secure=ConvertTo-SecureString -String $value
    $pointer=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer) }
}
$names=@('TEST_DATABASE_URL','TEST_MIGRATION_DATABASE_URL','TEST_ADMIN_DATABASE_URL','TEST_PG_MANIFEST','LENY_RAG_CHECK_ACTION','LENY_RAG_CHAT_CHECK','LENY_RAG_CHECK_PASSWORD','LENY_RAG_UI_ONLY','LENY_RAG_RELEASE_TEST_MODEL')
$saved=@{}
foreach($name in $names) { $saved[$name]=[Environment]::GetEnvironmentVariable($name,'Process') }
$pg='C:\laragon\bin\postgresql\postgresql-17.9-1\bin\pg_ctl.exe'
$started=$false
$result=1
try {
    $env:LENY_RAG_CHAT_CHECK=if($Chat){'true'}else{'false'}
    $env:LENY_RAG_UI_ONLY=if($UiOnly){'true'}else{'false'}
    $env:LENY_RAG_RELEASE_TEST_MODEL=if($ReleaseTestModel){'true'}else{'false'}
    if($Action -eq 'Serve'){$env:LENY_RAG_CHECK_PASSWORD=[guid]::NewGuid().ToString('N')+'Aa9!'}
    $secrets=Get-Content -LiteralPath (Join-Path $root 'credentials.dpapi.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $runner=Read-Secret $secrets.runner
    $migrator=Read-Secret $secrets.migrator
    $admin=Read-Secret $secrets.admin
    & $pg -D $data status 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        if (@([Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners() | Where-Object Port -EQ 55432).Count -gt 0) { throw 'Isolated port occupied.' }
        & $pg -D $data -l (Join-Path $root 'logs\postgresql.log') -w -t 30 start
        if ($LASTEXITCODE -ne 0) { throw 'Cannot start isolated PostgreSQL.' }
        $started=$true
    }
    $env:TEST_PG_MANIFEST=$manifestPath
    $env:TEST_DATABASE_URL="postgresql+psycopg2://bab_test_runner:$runner@127.0.0.1:55432/bab_vdos_testing"
    $env:TEST_MIGRATION_DATABASE_URL="postgresql+psycopg2://bab_test_migrator:$migrator@127.0.0.1:55432/bab_vdos_testing"
    $env:TEST_ADMIN_DATABASE_URL="postgresql+psycopg2://bab_test_admin:$admin@127.0.0.1:55432/bab_vdos_testing"
    $env:LENY_RAG_CHECK_ACTION=$Action
    & (Join-Path $repo 'backend\venv\Scripts\python.exe') -B (Join-Path $PSScriptRoot 'check_leny_rag.py')
    $result=$LASTEXITCODE
} finally {
    foreach($name in $names) { [Environment]::SetEnvironmentVariable($name,$saved[$name],'Process') }
    $runner=$migrator=$admin=$null
    if ($started) { & $pg -D $data -w -t 30 -m fast stop }
}
exit $result
