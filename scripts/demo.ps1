# Code Archaeologist — start the demo in production mode (Windows PowerShell)
#
#   powershell -ExecutionPolicy Bypass -File scripts\demo.ps1
#
# Backend runs without --reload and the frontend serves the existing production
# build, so nothing recompiles or reloads while a judge is clicking.
#
# This script never kills a process it did not start. It records only its own
# PIDs in tmp\demo so scripts\stop-demo.ps1 can shut them down again.

$ErrorActionPreference = "Stop"

. "$PSScriptRoot\_common.ps1"

$Root = Get-CaRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$StateDir = Get-CaDemoStateDir -Root $Root
$PidFile = Join-Path $StateDir "pids.json"

function Assert-PortFree([int]$Port, [string]$Role) {
    $owners = @(Get-CaPortOwner -Port $Port)
    if ($owners.Count -eq 0) {
        return
    }
    Write-Host ""
    Write-Host "Port $Port ($Role) is already in use:" -ForegroundColor Red
    foreach ($owner in $owners) {
        Write-Host "  PID $($owner.Pid)  $($owner.Name)  $($owner.Path)" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "This script will not terminate a process it did not start." -ForegroundColor Red
    Write-Host "If it is a previous demo run:  powershell -ExecutionPolicy Bypass -File scripts\stop-demo.ps1"
    Write-Host "If it is your own dev server:  close that terminal window."
    Write-Host "Then run scripts\demo.ps1 again."
    exit 1
}

Write-Host "Starting Code Archaeologist in demo (production) mode" -ForegroundColor White
Write-Host "Repository: $Root"

if (-not (Test-Path (Join-Path $Frontend ".next\BUILD_ID"))) {
    Write-Host ""
    Write-Host "No production build found." -ForegroundColor Red
    Write-Host "Run this first: powershell -ExecutionPolicy Bypass -File scripts\prepare-demo.ps1" -ForegroundColor Red
    exit 1
}

Write-CaHeading "Port checks"
Assert-PortFree -Port 8000 -Role "API"
Assert-PortFree -Port 3000 -Role "Web"
Write-CaResult "Port 8000 (API)" "PASS" "Free"
Write-CaResult "Port 3000 (Web)" "PASS" "Free"

Write-CaHeading "Launching services"

$api = Start-Process powershell -PassThru -WorkingDirectory $Backend -ArgumentList @(
    "-NoExit",
    "-Command",
    "`$Host.UI.RawUI.WindowTitle = 'Code Archaeologist API'; uv run python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
)
Write-CaResult "API window" "PASS" "PID $($api.Id) (uvicorn, no --reload)"

$web = Start-Process powershell -PassThru -WorkingDirectory $Frontend -ArgumentList @(
    "-NoExit",
    "-Command",
    "`$Host.UI.RawUI.WindowTitle = 'Code Archaeologist Web'; npm run start"
)
Write-CaResult "Web window" "PASS" "PID $($web.Id) (next start)"

@(
    [pscustomobject]@{ Role = "api"; Pid = $api.Id; StartTime = $api.StartTime.ToString("o") }
    [pscustomobject]@{ Role = "web"; Pid = $web.Id; StartTime = $web.StartTime.ToString("o") }
) | ConvertTo-Json | Set-Content -Path $PidFile -Encoding UTF8

Write-CaHeading "Readiness"

function Wait-ForUrl([string]$Url, [int]$TimeoutSeconds) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            Invoke-WebRequest -Uri $Url -TimeoutSec 4 -UseBasicParsing -ErrorAction Stop | Out-Null
            return $true
        } catch {
            Start-Sleep -Milliseconds 700
        }
    }
    return $false
}

if (Wait-ForUrl -Url "http://127.0.0.1:8000/health" -TimeoutSeconds 45) {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 5
    Write-CaResult "API /health" "PASS" "status=$($health.status) ai_available=$($health.ai_available)"
    if (-not $health.ai_available) {
        Write-Host "  AI is not configured. Git evidence still works; AI answers fall back to retrieved evidence." -ForegroundColor Yellow
    }
} else {
    Write-CaResult "API /health" "FAIL" "Did not respond within 45s. Check the API window."
}

if (Wait-ForUrl -Url "http://127.0.0.1:3000" -TimeoutSeconds 60) {
    Write-CaResult "Web root" "PASS" "http://127.0.0.1:3000"
} else {
    Write-CaResult "Web root" "FAIL" "Did not respond within 60s. Check the Web window."
}

Write-Host ""
Write-Host "DEMO RUNNING" -ForegroundColor Green
Write-Host "  App     http://127.0.0.1:3000"
Write-Host "  API     http://127.0.0.1:8000/health"
Write-Host ""
Write-Host "Stop with: powershell -ExecutionPolicy Bypass -File scripts\stop-demo.ps1"
Write-Host "Recorded PIDs: $PidFile" -ForegroundColor DarkGray
