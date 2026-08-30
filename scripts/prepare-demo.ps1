# Code Archaeologist — build and verify everything the demo needs.
#
#   powershell -ExecutionPolicy Bypass -File scripts\prepare-demo.ps1
#
# Stops at the first failure. Prints DEMO BUILD READY only when every step
# actually succeeded. Never prints secret values.

$ErrorActionPreference = "Stop"

. "$PSScriptRoot\_common.ps1"

$Root = Get-CaRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"

function Invoke-Step([string]$Name, [string]$WorkingDirectory, [string]$Command) {
    Write-CaHeading $Name
    Write-Host "  $Command" -ForegroundColor DarkGray
    Push-Location $WorkingDirectory
    try {
        # cmd /c keeps npm.cmd exit codes intact under PowerShell 5.1.
        & cmd /c "$Command"
        $code = $LASTEXITCODE
    } finally {
        Pop-Location
    }
    if ($code -ne 0) {
        Write-Host ""
        Write-Host "FAILED: $Name (exit code $code)" -ForegroundColor Red
        Write-Host "Fix the problem above and run scripts\prepare-demo.ps1 again." -ForegroundColor Red
        exit $code
    }
    Write-CaResult $Name "PASS"
}

Write-Host "Preparing the Code Archaeologist demo build" -ForegroundColor White
Write-Host "Repository: $Root"

if (-not (Test-Path (Join-Path $Frontend "node_modules"))) {
    Write-Host ""
    Write-Host "frontend\node_modules is missing. Run 'npm install' in frontend\ first." -ForegroundColor Red
    exit 1
}

# The production build rewrites .next, which fails or corrupts chunks while a
# Next process still holds it. Refuse rather than produce a broken build.
if (-not (Test-CaPortFree -Port 3000)) {
    $owners = @(Get-CaPortOwner -Port 3000)
    Write-Host ""
    Write-Host "Port 3000 is in use, so a Next.js server is probably still running." -ForegroundColor Red
    foreach ($owner in $owners) {
        Write-Host "  $($owner.Name) PID $($owner.Pid) $($owner.Path)" -ForegroundColor Yellow
    }
    Write-Host "Stop that server (scripts\stop-demo.ps1, or close its window), then run this again." -ForegroundColor Red
    Write-Host "Building while .next is in use is what produces 'Cannot find module ./833.js'." -ForegroundColor DarkGray
    exit 1
}

Invoke-Step "Backend tests"      $Backend  "uv run pytest -q"
Invoke-Step "Frontend lint"      $Frontend "npm run lint"
Invoke-Step "Frontend typecheck" $Frontend "npm run typecheck"
Invoke-Step "Frontend build"     $Frontend "npm run build"

if (-not (Test-Path (Join-Path $Frontend ".next\BUILD_ID"))) {
    Write-Host ""
    Write-Host "FAILED: the build finished but frontend\.next\BUILD_ID is missing." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "DEMO BUILD READY" -ForegroundColor Green
Write-Host "Start it with: powershell -ExecutionPolicy Bypass -File scripts\demo.ps1"
