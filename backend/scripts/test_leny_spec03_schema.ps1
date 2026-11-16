param([switch]$ScopeTests,[switch]$ContinuityTests)
$ErrorActionPreference = 'Stop'
$repositoryRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$testRoot = [System.IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'BAB_VDOS\postgresql-testing'))
$testData = Join-Path $testRoot 'data'
$manifestPath = Join-Path $testRoot 'manifest.json'
$credentialsPath = Join-Path $testRoot 'credentials.dpapi.json'
$pgBinaryRoot = 'C:\laragon\bin\postgresql\postgresql-17.9-1\bin'
$pgControl = Join-Path $pgBinaryRoot 'pg_ctl.exe'
$psql = Join-Path $pgBinaryRoot 'psql.exe'
$python = Join-Path $repositoryRoot 'backend\venv\Scripts\python.exe'
foreach ($path in @($manifestPath,$credentialsPath,$pgControl,$psql,$python,(Join-Path $testData 'PG_VERSION'))) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw 'Existing isolated test cluster and installed binaries required. Nothing will be provisioned.' }
}
$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ([System.IO.Path]::GetFullPath($manifest.data_directory) -ne $testData -or $manifest.host -ne '127.0.0.1' -or $manifest.port -ne 55432 -or $manifest.database -ne 'bab_vdos_testing') {
    throw 'Isolated test manifest identity mismatch.'
}
if ($manifest.instance_id -notmatch '^[a-fA-F0-9-]{36}$') { throw 'Invalid isolated instance marker.' }
$credentials = Get-Content -LiteralPath $credentialsPath -Raw -Encoding UTF8 | ConvertFrom-Json
function Unprotect-TestPassword([string]$Value) {
    $secure = ConvertTo-SecureString -String $Value
    $pointer = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try { return [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer) }
    finally { [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer) }
}
$privateSubdirectory = if ($ContinuityTests) { 'BAB_VDOS\leny-spec031' } else { 'BAB_VDOS\leny-spec03' }
$privateRoot = [System.IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA $privateSubdirectory))
$checkpointPointer = Join-Path $privateRoot 'active.txt'
if (-not (Test-Path -LiteralPath $checkpointPointer -PathType Leaf)) { throw 'Private SPEC03 checkpoint pointer required.' }
$checkpoint = [System.IO.Path]::GetFullPath((Get-Content -LiteralPath $checkpointPointer -Raw -Encoding UTF8).Trim())
if (-not $checkpoint.StartsWith($privateRoot+[System.IO.Path]::DirectorySeparatorChar,[System.StringComparison]::OrdinalIgnoreCase) -or -not (Test-Path -LiteralPath $checkpoint -PathType Container)) { throw 'Checkpoint must be an existing directory inside private SPEC03 storage.' }
$savedEnvironment = @{}
foreach ($entry in (Get-ChildItem Env: | Where-Object { $_.Name -like 'PG*' -or $_.Name -in @('TEST_DATABASE_URL','TEST_MIGRATION_DATABASE_URL','TEST_PG_MANIFEST','ENVIRONMENT','LENY_RUNTIME_AUTOSTART','DATABASE_URL') })) {
    $savedEnvironment[$entry.Name] = $entry.Value
    Remove-Item -LiteralPath ('Env:'+$entry.Name)
}
$startedHere = $false
$testExit = 2
try {
    & $pgControl -D $testData status 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        $occupied = @([System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners() | Where-Object Port -EQ 55432)
        if ($occupied.Count -gt 0) { throw 'Port 55432 is occupied by another process. Refusing to start.' }
        & $pgControl -D $testData -l (Join-Path $testRoot 'logs\postgresql.log') -w -t 30 start
        if ($LASTEXITCODE -ne 0) { throw 'Isolated test cluster failed to start.' }
        $startedHere = $true
    }
    $migrationPassword = Unprotect-TestPassword $credentials.migrator
    $runnerPassword = Unprotect-TestPassword $credentials.runner
    $env:PGPASSWORD = $migrationPassword
    $identity = & $psql -X -q -t -A -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U bab_test_migrator -d bab_vdos_testing -c "SELECT instance_id FROM testing_control.instance; SHOW data_directory; SELECT version_num FROM alembic_version;"
    if ($LASTEXITCODE -ne 0) { throw 'Could not verify existing test database identity.' }
    $lines = @($identity | Where-Object { $_.Trim() -ne '' })
    if ($lines.Count -ne 3 -or $lines[0].Trim() -ne $manifest.instance_id -or [System.IO.Path]::GetFullPath($lines[1].Trim()) -ne $testData -or $lines[2].Trim() -notin @('20261020_0021','20261104_0023')) {
        Write-Output ('Observed isolated revision: '+$lines[2].Trim()); throw 'Isolated identity/revision mismatch; no migration attempted.'
    }
    Remove-Item -LiteralPath Env:PGPASSWORD
    $env:TEST_PG_MANIFEST = $manifestPath
    $env:TEST_DATABASE_URL = 'postgresql+psycopg2://bab_test_runner:'+([uri]::EscapeDataString($runnerPassword))+'@127.0.0.1:55432/bab_vdos_testing'
    $env:TEST_MIGRATION_DATABASE_URL = 'postgresql+psycopg2://bab_test_migrator:'+([uri]::EscapeDataString($migrationPassword))+'@127.0.0.1:55432/bab_vdos_testing'
    $env:ENVIRONMENT = 'test'
    $env:LENY_RUNTIME_AUTOSTART = 'false'
    $env:DATABASE_URL = $env:TEST_DATABASE_URL
    if ($ScopeTests -or $ContinuityTests) {
        $testArguments = @((Join-Path $checkpoint 'sql-scope.xml'))
        if ($ContinuityTests) { $testArguments += 'continuity' }
        & $python -B (Join-Path $PSScriptRoot 'test_leny_spec03_sql.py') @testArguments
    } else {
        & $python -B (Join-Path $PSScriptRoot 'test_leny_spec03_schema.py') (Join-Path $checkpoint 'schema0025.json')
    }
    $testExit = $LASTEXITCODE
} finally {
    Remove-Item -LiteralPath Env:PGPASSWORD -ErrorAction SilentlyContinue
    if ($startedHere) { & $pgControl -D $testData -w -t 30 -m fast stop }
    foreach ($name in @('TEST_DATABASE_URL','TEST_MIGRATION_DATABASE_URL','TEST_PG_MANIFEST','ENVIRONMENT','LENY_RUNTIME_AUTOSTART','DATABASE_URL')) {
        Remove-Item -LiteralPath ('Env:'+$name) -ErrorAction SilentlyContinue
    }
    foreach ($name in $savedEnvironment.Keys) { Set-Item -LiteralPath ('Env:'+$name) -Value $savedEnvironment[$name] }
    $migrationPassword = $null
    $runnerPassword = $null
}
exit $testExit
