$ErrorActionPreference = 'Stop'
$repositoryRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$testRoot = [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'BAB_VDOS\postgresql-testing'))
$manifestPath = Join-Path $testRoot 'manifest.json'
$testData = Join-Path $testRoot 'data'
$pgControl = 'C:\laragon\bin\postgresql\postgresql-17.9-1\bin\pg_ctl.exe'
$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ([IO.Path]::GetFullPath($manifest.data_directory) -ne $testData -or $manifest.port -ne 55432 -or $manifest.host -ne '127.0.0.1' -or $manifest.database -ne 'bab_vdos_testing') { throw 'Isolated manifest identity mismatch.' }
function Read-ProtectedPassword([string]$value) {
    $secure=ConvertTo-SecureString -String $value
    $pointer=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer) }
}
$names=@('TEST_DATABASE_URL','TEST_MIGRATION_DATABASE_URL','TEST_ADMIN_DATABASE_URL','TEST_PG_MANIFEST')
$saved=@{}
foreach ($name in $names) { $saved[$name]=[Environment]::GetEnvironmentVariable($name,'Process') }
$startedHere=$false
$result=1
try {
    $credentials=Get-Content -LiteralPath (Join-Path $testRoot 'credentials.dpapi.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $runner=Read-ProtectedPassword $credentials.runner
    $migrator=Read-ProtectedPassword $credentials.migrator
    $admin=Read-ProtectedPassword $credentials.admin
    & $pgControl -D $testData status 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        $occupied=@([Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners() | Where-Object Port -EQ 55432)
        if ($occupied.Count -gt 0) { throw 'Test port occupied by an unverified process.' }
        & $pgControl -D $testData -l (Join-Path $testRoot 'logs\postgresql.log') -w -t 30 start
        if ($LASTEXITCODE -ne 0) { throw 'Isolated server failed to start.' }
        $startedHere=$true
    }
    $env:TEST_PG_MANIFEST=$manifestPath
    $env:TEST_DATABASE_URL="postgresql+psycopg2://bab_test_runner:$runner@127.0.0.1:55432/bab_vdos_testing"
    $env:TEST_MIGRATION_DATABASE_URL="postgresql+psycopg2://bab_test_migrator:$migrator@127.0.0.1:55432/bab_vdos_testing"
    $env:TEST_ADMIN_DATABASE_URL="postgresql+psycopg2://bab_test_admin:$admin@127.0.0.1:55432/bab_vdos_testing"
    & (Join-Path $repositoryRoot 'backend\venv\Scripts\python.exe') -B (Join-Path $PSScriptRoot 'check_leny_documents_recovery.py')
    $result=$LASTEXITCODE
} finally {
    foreach ($name in $names) { [Environment]::SetEnvironmentVariable($name,$saved[$name],'Process') }
    $runner=$migrator=$admin=$null
    if ($startedHere) { & $pgControl -D $testData -w -t 30 -m fast stop }
}
exit $result
