param([switch]$Provision, [switch]$RunTests, [string]$PythonExecutable)

$ErrorActionPreference = 'Stop'
$repositoryRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$testRoot = [System.IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'BAB_VDOS\postgresql-testing'))
$testData = Join-Path $testRoot 'data'
$manifestPath = Join-Path $testRoot 'manifest.json'
$credentialsPath = Join-Path $testRoot 'credentials.dpapi.json'
$pgBinaryRoot = 'C:\laragon\bin\postgresql\postgresql-17.9-1\bin'
$pgControl = Join-Path $pgBinaryRoot 'pg_ctl.exe'
$psql = Join-Path $pgBinaryRoot 'psql.exe'
$python = if ($PythonExecutable) { (Resolve-Path -LiteralPath $PythonExecutable).Path } else { Join-Path $repositoryRoot 'backend\venv\Scripts\python.exe' }

if (-not $Provision -and -not $RunTests) {
    [pscustomobject]@{ Action='Proposal only; nothing created or started'; DataDirectory=$testData; Host='127.0.0.1'; Port=55432; Database='bab_vdos_testing'; Roles=@('bab_test_admin','bab_test_migrator','bab_test_runner') } | ConvertTo-Json
    exit 0
}

function New-TestPassword {
    $bytes = New-Object byte[] 32
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generator.GetBytes($bytes) } finally { $generator.Dispose() }
    return [System.BitConverter]::ToString($bytes).Replace('-', '').ToLowerInvariant()
}

function Protect-TestPassword([string]$Value) {
    return (ConvertTo-SecureString -String $Value -AsPlainText -Force | ConvertFrom-SecureString)
}

function Unprotect-TestPassword([string]$Value) {
    $secure = ConvertTo-SecureString -String $Value
    $pointer = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try { return [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer) }
    finally { [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer) }
}

function Invoke-TestSql([string]$Database, [string]$Statement) {
    $Statement | & $psql -X -q -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U bab_test_admin -d $Database
    if ($LASTEXITCODE -ne 0) { throw 'A statement against the exclusive test cluster failed.' }
}

foreach ($binary in @($pgControl, $psql, (Join-Path $pgBinaryRoot 'initdb.exe'), $python)) {
    if (-not (Test-Path -LiteralPath $binary -PathType Leaf)) { throw 'Required installed binary not found. No installation will be attempted.' }
}
if ($Provision -and (Test-Path -LiteralPath $testRoot)) { throw 'Testing root already exists. Refusing to overwrite or delete any existing files.' }
$oldTestUrl = $env:TEST_DATABASE_URL
$oldMigrationUrl = $env:TEST_MIGRATION_DATABASE_URL
$oldManifest = $env:TEST_PG_MANIFEST
$savedPostgresEnvironment = @{}
foreach ($entry in (Get-ChildItem Env: | Where-Object { $_.Name -like 'PG*' })) {
    $savedPostgresEnvironment[$entry.Name] = $entry.Value
    Remove-Item -LiteralPath ('Env:' + $entry.Name)
}
$startedHere = $false
$testExit = 0
try {
    if ($Provision) {
        $occupied = @([System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners() | Where-Object Port -EQ 55432)
        if ($occupied.Count -gt 0) { throw 'Port 55432 is occupied. No server will be touched.' }
        New-Item -ItemType Directory -Path $testRoot | Out-Null
        New-Item -ItemType Directory -Path (Join-Path $testRoot 'logs'), (Join-Path $testRoot 'runtime') | Out-Null
        $adminPassword = New-TestPassword
        $migrationPassword = New-TestPassword
        $runnerPassword = New-TestPassword
        $passwordFile = Join-Path $testRoot 'runtime\initdb-password.txt'
        try {
            [System.IO.File]::WriteAllText($passwordFile, $adminPassword, [System.Text.Encoding]::ASCII)
            & (Join-Path $pgBinaryRoot 'initdb.exe') -D $testData -U bab_test_admin --auth=scram-sha-256 --encoding=UTF8 --locale=C --pwfile=$passwordFile
            if ($LASTEXITCODE -ne 0) { throw 'Exclusive test cluster initialization failed.' }
        } finally {
            if (Test-Path -LiteralPath $passwordFile) { Remove-Item -LiteralPath $passwordFile -Force }
        }
        @"

# BAB_VDOS isolated testing only
listen_addresses = '127.0.0.1'
port = 55432
timezone = 'America/La_Paz'
log_timezone = 'America/La_Paz'
password_encryption = 'scram-sha-256'
"@ | Add-Content -LiteralPath (Join-Path $testData 'postgresql.conf') -Encoding UTF8
        $credentials = @{ admin=(Protect-TestPassword $adminPassword); migrator=(Protect-TestPassword $migrationPassword); runner=(Protect-TestPassword $runnerPassword) }
        $credentials | ConvertTo-Json | Set-Content -LiteralPath $credentialsPath -Encoding UTF8
        $manifest = @{ data_directory=$testData; host='127.0.0.1'; port=55432; database='bab_vdos_testing'; test_role='bab_test_runner'; migration_role='bab_test_migrator'; instance_id=([guid]::NewGuid().ToString()) }
        $manifest | ConvertTo-Json | Set-Content -LiteralPath $manifestPath -Encoding UTF8
    } else {
        if (-not (Test-Path -LiteralPath $manifestPath) -or -not (Test-Path -LiteralPath $credentialsPath)) { throw 'Owned testing manifest and protected credentials are required.' }
        $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ([System.IO.Path]::GetFullPath($manifest.data_directory) -ne $testData -or $manifest.port -ne 55432 -or $manifest.host -ne '127.0.0.1' -or $manifest.database -ne 'bab_vdos_testing') { throw 'Testing manifest identity mismatch.' }
        $credentials = Get-Content -LiteralPath $credentialsPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $adminPassword = Unprotect-TestPassword $credentials.admin
        $migrationPassword = Unprotect-TestPassword $credentials.migrator
        $runnerPassword = Unprotect-TestPassword $credentials.runner
    }

    & $pgControl -D $testData status 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        $occupied = @([System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners() | Where-Object Port -EQ 55432)
        if ($occupied.Count -gt 0) { throw 'Port 55432 is occupied by another process. Refusing to start.' }
        & $pgControl -D $testData -l (Join-Path $testRoot 'logs\postgresql.log') -w -t 30 start
        if ($LASTEXITCODE -ne 0) { throw 'Exclusive test cluster start failed.' }
        $startedHere = $true
    }
    $env:PGPASSWORD = $adminPassword
    if ($Provision) {
        Invoke-TestSql 'postgres' @"
CREATE ROLE bab_test_migrator LOGIN PASSWORD '$migrationPassword' NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE ROLE bab_test_runner LOGIN PASSWORD '$runnerPassword' NOSUPERUSER NOCREATEDB NOCREATEROLE;
GRANT pg_read_all_settings TO bab_test_migrator;
CREATE DATABASE bab_vdos_testing OWNER bab_test_migrator TEMPLATE template0 ENCODING 'UTF8';
REVOKE CONNECT ON DATABASE postgres FROM PUBLIC;
REVOKE CONNECT ON DATABASE template1 FROM PUBLIC;
REVOKE ALL ON DATABASE bab_vdos_testing FROM PUBLIC;
GRANT CONNECT, TEMPORARY ON DATABASE bab_vdos_testing TO bab_test_runner;
"@
        Invoke-TestSql 'bab_vdos_testing' @"
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE SCHEMA testing_control AUTHORIZATION bab_test_admin;
CREATE TABLE testing_control.instance(instance_id text PRIMARY KEY);
INSERT INTO testing_control.instance VALUES ('$($manifest.instance_id)');
GRANT USAGE ON SCHEMA testing_control TO bab_test_runner, bab_test_migrator;
GRANT SELECT ON testing_control.instance TO bab_test_runner, bab_test_migrator;
"@
    }
    if ($RunTests) {
        $env:TEST_PG_MANIFEST = $manifestPath
        $env:TEST_DATABASE_URL = "postgresql+psycopg2://bab_test_runner:$runnerPassword@127.0.0.1:55432/bab_vdos_testing"
        $env:TEST_MIGRATION_DATABASE_URL = "postgresql+psycopg2://bab_test_migrator:$migrationPassword@127.0.0.1:55432/bab_vdos_testing"
        & $python -B (Join-Path $PSScriptRoot 'run_notification_integration.py')
        $testExit = $LASTEXITCODE
    }
} finally {
    foreach ($entry in (Get-ChildItem Env: | Where-Object { $_.Name -like 'PG*' })) {
        Remove-Item -LiteralPath ('Env:' + $entry.Name)
    }
    foreach ($name in $savedPostgresEnvironment.Keys) {
        [System.Environment]::SetEnvironmentVariable($name, $savedPostgresEnvironment[$name], 'Process')
    }
    $env:TEST_DATABASE_URL = $oldTestUrl
    $env:TEST_MIGRATION_DATABASE_URL = $oldMigrationUrl
    $env:TEST_PG_MANIFEST = $oldManifest
    if ($startedHere) {
        & $pgControl -D $testData -w -t 30 -m fast stop
        if ($LASTEXITCODE -ne 0) { Write-Warning 'Testing PostgreSQL did not stop; inspect only its own cluster.' }
    }
}
exit $testExit
