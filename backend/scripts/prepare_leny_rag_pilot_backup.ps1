param([Parameter(Mandatory=$true)][string]$PrivateDirectory,
      [Parameter(Mandatory=$true)][string]$Output)
$ErrorActionPreference='Stop'
$repositoryRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$testRoot=[IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'BAB_VDOS\postgresql-testing'))
$testData=Join-Path $testRoot 'data'
$manifestPath=Join-Path $testRoot 'manifest.json'
$pgControl='C:\laragon\bin\postgresql\postgresql-17.9-1\bin\pg_ctl.exe'
$manifest=Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ([IO.Path]::GetFullPath($manifest.data_directory) -ne $testData -or $manifest.port -ne 55432 -or $manifest.host -ne '127.0.0.1' -or $manifest.database -ne 'bab_vdos_testing') { throw 'Isolated test identity mismatch.' }
$names=@('TEST_ADMIN_DATABASE_URL','TEST_PG_MANIFEST')
$saved=@{}
foreach($name in $names){$saved[$name]=[Environment]::GetEnvironmentVariable($name,'Process')}
$startedHere=$false
$result=1
try {
    & $pgControl -D $testData status 2>$null | Out-Null
    if($LASTEXITCODE -ne 0){
        $occupied=@([Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners() | Where-Object Port -EQ 55432)
        if($occupied.Count -gt 0){throw 'Test port occupied; no process stopped.'}
        & $pgControl -D $testData -l (Join-Path $testRoot 'logs\postgresql.log') -w -t 30 start
        if($LASTEXITCODE -ne 0){throw 'Isolated cluster failed to start.'}
        $startedHere=$true
    }
    $credentials=Get-Content -LiteralPath (Join-Path $testRoot 'credentials.dpapi.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $secure=ConvertTo-SecureString -String $credentials.admin
    $pointer=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try{$admin=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)}
    finally{[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)}
    $env:TEST_ADMIN_DATABASE_URL='postgresql+psycopg2://bab_test_admin:'+([uri]::EscapeDataString($admin))+'@127.0.0.1:55432/bab_vdos_testing'
    $env:TEST_PG_MANIFEST=$manifestPath
    & (Join-Path $repositoryRoot 'backend\venv\Scripts\python.exe') -B (Join-Path $PSScriptRoot 'prepare_leny_rag_pilot_backup.py') --prepare-backup --private-dir $PrivateDirectory --output ([IO.Path]::GetFullPath($Output))
    $result=$LASTEXITCODE
} finally {
    foreach($name in $names){[Environment]::SetEnvironmentVariable($name,$saved[$name],'Process')}
    $admin=$credentials=$secure=$null
    if($startedHere){
        & $pgControl -D $testData -w -t 30 -m fast stop
        if($LASTEXITCODE -ne 0){Write-Warning 'Owned test cluster requires separate inspection.'}
    }
}
exit $result
