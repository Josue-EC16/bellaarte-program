param([switch]$Activate, [switch]$Disable)

$ErrorActionPreference = 'Stop'
$taskName = 'BAB_VDOS_USD_BOB_SYNC'
$backendPath = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$pythonPath = Join-Path $backendPath 'venv\Scripts\pythonw.exe'
$scriptPath = Join-Path $PSScriptRoot 'run_exchange_rate_sync.py'
if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) { throw 'Existing Windows venv pythonw is required.' }
if ($Activate -and $Disable) { throw 'Select activation or disable, never both.' }
$arguments = '-B "' + $scriptPath + '"'
$existing = Get-ScheduledTask -TaskName $taskName -TaskPath '\' -ErrorAction SilentlyContinue
if ($existing) {
    if ($existing.Actions.Count -ne 1 -or $existing.Actions[0].Execute -ne $pythonPath -or
        $existing.Actions[0].Arguments -ne $arguments -or $existing.Actions[0].WorkingDirectory -ne $backendPath) {
        throw 'Task identity mismatch: no existing task is changed.'
    }
}
if ($Disable) {
    if ($existing) { Disable-ScheduledTask -TaskName $taskName -TaskPath '\' | Out-Null }
    [ordered]@{task=$taskName; enabled=$false; changed=[bool]$existing} | ConvertTo-Json -Compress
    exit 0
}
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
if (-not $Activate) {
    [ordered]@{task=$taskName; existing=[bool]$existing; changed=$false; user=$identity;
        logon='InteractiveToken'; interval_seconds=60; executable=$pythonPath; working_directory=$backendPath} | ConvertTo-Json -Compress
    exit 0
}
$action = New-ScheduledTaskAction -Execute $pythonPath -Argument $arguments -WorkingDirectory $backendPath
# An omitted repetition duration means indefinite repetition. Date/05:00 and
# retry eligibility remain in the Python Bolivia calendar, not the Windows zone.
$periodic = New-ScheduledTaskTrigger -Once -At (Get-Date).AddSeconds(5) -RepetitionInterval (New-TimeSpan -Minutes 1)
$logon = New-ScheduledTaskTrigger -AtLogOn -User $identity
$principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -Hidden `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
$definition = New-ScheduledTask -Action $action -Trigger @($periodic, $logon) -Principal $principal -Settings $settings `
    -Description ('BAB_VDOS TC-02 USD/BOB; local session, no password; policy in Python; ' + $backendPath)
Register-ScheduledTask -TaskName $taskName -TaskPath '\' -InputObject $definition -Force | Out-Null
$actual = Get-ScheduledTask -TaskName $taskName -TaskPath '\'
if ($actual.Principal.LogonType -ne 'Interactive' -or $actual.Principal.RunLevel -ne 'Limited' -or
    $actual.Actions[0].Execute -ne $pythonPath -or $actual.Actions[0].Arguments -ne $arguments) {
    Disable-ScheduledTask -TaskName $taskName -TaskPath '\' | Out-Null
    throw 'Registered task differs from the approved least-privilege definition; disabled.'
}
[ordered]@{task=$taskName; enabled=$true; user=$identity; logon='InteractiveToken'; interval_seconds=60;
    multiple_instances='IgnoreNew'; run_level='Limited'; working_directory=$backendPath} | ConvertTo-Json -Compress
