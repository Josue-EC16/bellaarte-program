param(
    [Parameter(Mandatory=$true)][ValidateSet('legacy','rag4_v1')][string]$Profile,
    [ValidateSet('pilot','followup','diagnostic','quality','contracts','development','budget','retrieval','focused','stability','supervised')][string]$Mode='pilot',
    [ValidateSet('fixed','adaptive')][string]$EvidenceMode='fixed',
    [ValidateSet(2048,2304,2560)][int]$Budget=2048,
    [ValidateSet('semantic','hybrid')][string]$Ranking='semantic',
    [switch]$Neighbors,
    [ValidateSet(0.0,0.3)][double]$Temperature=0.3,
    [switch]$TokenProbe,
    [ValidateSet(0,900,1200)][int]$ProcedureStressBytes=0,
    [ValidateRange(1,84)][int]$CaseLimit=84,
    [Parameter(Mandatory=$true)][string]$Output,
    [string]$Checkpoint,
    [switch]$ExclusiveWindowConfirmed
)

$ErrorActionPreference = 'Stop'
if (-not $ExclusiveWindowConfirmed) { throw 'An explicitly authorized exclusive LENY window is required. No services or data changed.' }
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
$savedEnvironment = @{}
foreach ($entry in (Get-ChildItem Env: | Where-Object { $_.Name -like 'PG*' -or $_.Name -in @('TEST_DATABASE_URL','TEST_MIGRATION_DATABASE_URL','TEST_PG_MANIFEST') })) {
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
    if ($lines.Count -ne 3 -or $lines[0].Trim() -ne $manifest.instance_id -or [System.IO.Path]::GetFullPath($lines[1].Trim()) -ne $testData -or $lines[2].Trim() -ne '20261020_0021') {
        throw 'Existing test marker/data directory/revision0021 verification failed. No migration attempted.'
    }
    Remove-Item -LiteralPath Env:PGPASSWORD
    $env:TEST_PG_MANIFEST = $manifestPath
    $env:TEST_DATABASE_URL = 'postgresql+psycopg2://bab_test_runner:'+([uri]::EscapeDataString($runnerPassword))+'@127.0.0.1:55432/bab_vdos_testing'
    $env:TEST_MIGRATION_DATABASE_URL = 'postgresql+psycopg2://bab_test_migrator:'+([uri]::EscapeDataString($migrationPassword))+'@127.0.0.1:55432/bab_vdos_testing'
    $arguments = @('--profile',$Profile,'--mode',$Mode,'--evidence-mode',$EvidenceMode,'--budget',"$Budget",'--ranking',$Ranking,'--case-limit',"$CaseLimit",'--output',([System.IO.Path]::GetFullPath($Output)),'--exclusive-window-confirmed')
    $arguments += @('--temperature',$Temperature.ToString([System.Globalization.CultureInfo]::InvariantCulture))
    if ($Neighbors) { $arguments += '--neighbors' }
    if ($TokenProbe) { $arguments += '--token-probe' }
    if ($ProcedureStressBytes) { $arguments += @('--procedure-stress-bytes',"$ProcedureStressBytes") }
    if ($Checkpoint) { $arguments += @('--checkpoint',([System.IO.Path]::GetFullPath($Checkpoint))) }
    & $python -B (Join-Path $PSScriptRoot 'run_leny_rag_quality.py') @arguments
    $testExit = $LASTEXITCODE
} finally {
    foreach ($entry in (Get-ChildItem Env: | Where-Object { $_.Name -like 'PG*' -or $_.Name -in @('TEST_DATABASE_URL','TEST_MIGRATION_DATABASE_URL','TEST_PG_MANIFEST') })) {
        Remove-Item -LiteralPath ('Env:'+$entry.Name)
    }
    foreach ($name in $savedEnvironment.Keys) { [Environment]::SetEnvironmentVariable($name,$savedEnvironment[$name],'Process') }
    $migrationPassword = $null
    $runnerPassword = $null
    if ($startedHere) {
        & $pgControl -D $testData -w -t 30 -m fast stop
        if ($LASTEXITCODE -ne 0) { Write-Warning 'Only the owned test cluster failed to stop; inspect it separately.' }
    }
}
exit $testExit
