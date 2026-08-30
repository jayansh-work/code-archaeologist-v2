# Code Archaeologist — stop the demo processes this repo started.
#
#   powershell -ExecutionPolicy Bypass -File scripts\stop-demo.ps1
#
# Only PIDs recorded by scripts\demo.ps1 are considered, and each one is
# re-validated against its recorded start time before being stopped. Unrelated
# Node or Python processes are never touched.

$ErrorActionPreference = "Stop"

. "$PSScriptRoot\_common.ps1"

$Root = Get-CaRoot
$StateDir = Get-CaDemoStateDir -Root $Root
$PidFile = Join-Path $StateDir "pids.json"

if (-not (Test-Path $PidFile)) {
    Write-Host "No recorded demo processes ($PidFile is missing)." -ForegroundColor Yellow
    Write-Host "Nothing was stopped. Close demo windows manually if they are still open."
    exit 0
}

try {
    $records = @(Get-Content $PidFile -Raw | ConvertFrom-Json)
} catch {
    Write-Host "Could not read $PidFile. Delete it and close demo windows manually." -ForegroundColor Red
    exit 1
}

Write-CaHeading "Stopping recorded demo processes"

$stopped = 0
foreach ($record in $records) {
    $label = "$($record.Role) PID $($record.Pid)"
    $process = Get-Process -Id $record.Pid -ErrorAction SilentlyContinue
    if (-not $process) {
        Write-CaResult $label "PASS" "Already gone"
        continue
    }
    # Guard against a recycled PID now belonging to something unrelated.
    $recordedStart = [datetime]::Parse($record.StartTime)
    if ([math]::Abs(($process.StartTime - $recordedStart).TotalSeconds) -gt 5) {
        Write-CaResult $label "WARN" "PID reused by '$($process.ProcessName)'. Left running."
        continue
    }
    try {
        Stop-Process -Id $record.Pid -ErrorAction Stop
        Write-CaResult $label "PASS" "Stopped '$($process.ProcessName)'"
        $stopped++
    } catch {
        Write-CaResult $label "FAIL" $_.Exception.Message
    }
}

Remove-Item $PidFile -Force -ErrorAction SilentlyContinue

Start-Sleep -Milliseconds 900
Write-CaHeading "Ports"
foreach ($entry in @(@{ Port = 8000; Role = "API" }, @{ Port = 3000; Role = "Web" })) {
    $owners = @(Get-CaPortOwner -Port $entry.Port)
    if ($owners.Count -eq 0) {
        Write-CaResult "Port $($entry.Port) ($($entry.Role))" "PASS" "Free"
    } else {
        $detail = ($owners | ForEach-Object { "$($_.Name) PID $($_.Pid)" }) -join ", "
        Write-CaResult "Port $($entry.Port) ($($entry.Role))" "WARN" "Still held by $detail"
    }
}

Write-Host ""
Write-Host "Stopped $stopped recorded process(es)." -ForegroundColor Green
