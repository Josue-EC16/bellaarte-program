param([string]$Password = $env:LENY_SMOKE_PASSWORD, [string]$CleanupUsername, [switch]$Documents)

$ErrorActionPreference = 'Stop'
if ($CleanupUsername) {
    if ($CleanupUsername -cnotmatch '^leny_smoke_[0-9a-f]{12}$') { throw 'Cleanup requires an exact synthetic smoke username.' }
} else {
    if ([string]::IsNullOrEmpty($Password)) { throw 'Supply LENY_SMOKE_PASSWORD through the process environment.' }
    if ($Password.Length -lt 12 -or [Text.Encoding]::UTF8.GetByteCount($Password) -gt 72) { throw 'Synthetic password must be 12 to 72 UTF-8 bytes.' }
}
$repositoryRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$testRoot = [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'BAB_VDOS\postgresql-testing'))
$testData = Join-Path $testRoot 'data'
$manifestPath = Join-Path $testRoot 'manifest.json'
$credentialsPath = Join-Path $testRoot 'credentials.dpapi.json'
$pgControl = 'C:\laragon\bin\postgresql\postgresql-17.9-1\bin\pg_ctl.exe'
$python = Join-Path $repositoryRoot 'backend\venv\Scripts\python.exe'
foreach ($path in @($manifestPath, $credentialsPath, $pgControl, $python)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw 'Existing isolated test infrastructure is required; no provisioning is supported.' }
}
$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ([IO.Path]::GetFullPath($manifest.data_directory) -ne $testData -or $manifest.host -ne '127.0.0.1' -or $manifest.port -ne 55432 -or $manifest.database -ne 'bab_vdos_testing' -or $manifest.test_role -ne 'bab_test_runner' -or $manifest.migration_role -ne 'bab_test_migrator') {
    throw 'Existing isolated test manifest identity mismatch.'
}
[void][guid]::Parse($manifest.instance_id)
Write-Host 'LENY smoke: isolated manifest verified.'

function Unprotect-SmokePassword([string]$Value) {
    $secure = ConvertTo-SecureString -String $Value
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer) }
}

function Invoke-SmokePgControl([string]$Arguments, [int]$TimeoutMs = 45000) {
    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $pgControl
    $startInfo.Arguments = $Arguments
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $startInfo
    try {
        [void]$process.Start()
        $outputRead = $process.StandardOutput.ReadToEndAsync()
        $errorRead = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit($TimeoutMs)) {
            $process.Kill()
            throw 'Isolated PostgreSQL control exceeded its deadline.'
        }
        return $process.ExitCode
    } finally { $process.Dispose() }
}

$savedEnvironment = @{}
foreach ($entry in (Get-ChildItem Env: | Where-Object { $_.Name -like 'PG*' -or $_.Name -in @('TEST_DATABASE_URL','TEST_MIGRATION_DATABASE_URL','TEST_PG_MANIFEST','LENY_SMOKE_PASSWORD','LENY_SMOKE_CLEANUP_USERNAME') })) {
    $savedEnvironment[$entry.Name] = $entry.Value
}
$startedHere = $false
$smokeExit = 2
try {
    foreach ($entry in (Get-ChildItem Env: | Where-Object { $_.Name -like 'PG*' })) { Remove-Item -LiteralPath ('Env:' + $entry.Name) }
    $credentials = Get-Content -LiteralPath $credentialsPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $runnerPassword = Unprotect-SmokePassword $credentials.runner
    $migrationPassword = Unprotect-SmokePassword $credentials.migrator
    Write-Host 'LENY smoke: checking isolated PostgreSQL availability.'
    # Use a bounded, hidden native process. A redirected native invocation can
    # retain inherited console pipe handles in PowerShell hosts used by agents.
    $statusExit = Invoke-SmokePgControl ('-D "' + $testData + '" status') 5000
    if ($statusExit -ne 0) {
        $occupied = @([Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners() | Where-Object Port -EQ 55432)
        if ($occupied.Count -gt 0) { throw 'Test port belongs to another process; refusing to start.' }
        # A separate hidden console prevents the foreground smoke Ctrl+C from
        # reaching PostgreSQL before the application can clean its own identity.
        $testLog = Join-Path $testRoot 'logs\postgresql.log'
        $startExit = Invoke-SmokePgControl ('-D "' + $testData + '" -l "' + $testLog + '" -w -t 30 start')
        if ($startExit -ne 0) { throw 'Existing isolated PostgreSQL failed to start.' }
        $startedHere = $true
    }
    $env:TEST_PG_MANIFEST = $manifestPath
    $env:TEST_DATABASE_URL = "postgresql+psycopg2://bab_test_runner:$runnerPassword@127.0.0.1:55432/bab_vdos_testing"
    $env:TEST_MIGRATION_DATABASE_URL = "postgresql+psycopg2://bab_test_migrator:$migrationPassword@127.0.0.1:55432/bab_vdos_testing"
    $env:LENY_SMOKE_PASSWORD = $Password
    $env:LENY_SMOKE_CLEANUP_USERNAME = $CleanupUsername
    $oldDocumentSmoke = $env:LENY_DOCUMENTS_SMOKE
    if ($Documents) { $env:LENY_DOCUMENTS_SMOKE = '1' }
    & $python -B (Join-Path $PSScriptRoot 'run_leny_smoke.py')
    $smokeExit = $LASTEXITCODE
} finally {
    $env:LENY_DOCUMENTS_SMOKE = $oldDocumentSmoke
    foreach ($entry in (Get-ChildItem Env: | Where-Object { $_.Name -like 'PG*' -or $_.Name -in @('TEST_DATABASE_URL','TEST_MIGRATION_DATABASE_URL','TEST_PG_MANIFEST','LENY_SMOKE_PASSWORD','LENY_SMOKE_CLEANUP_USERNAME') })) {
        Remove-Item -LiteralPath ('Env:' + $entry.Name)
    }
    foreach ($name in $savedEnvironment.Keys) { [Environment]::SetEnvironmentVariable($name, $savedEnvironment[$name], 'Process') }
    $runnerPassword = $migrationPassword = $Password = $null
    if ($startedHere) {
        $stopExit = Invoke-SmokePgControl ('-D "' + $testData + '" -w -t 30 -m fast stop')
        if ($stopExit -ne 0) { Write-Warning 'Inspect only the isolated test PostgreSQL shutdown.' }
    }
}
exit $smokeExit
