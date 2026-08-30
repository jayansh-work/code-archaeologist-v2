# Code Archaeologist — environment check (Windows PowerShell)
#
# Run this immediately before a demo. It never prints secret values.
#
#   powershell -ExecutionPolicy Bypass -File scripts\doctor.ps1

. "$PSScriptRoot\_common.ps1"

$Root = Get-CaRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$failures = 0
$warnings = 0

function Record([string]$Name, [string]$State, [string]$Detail = "") {
    Write-CaResult $Name $State $Detail
    if ($State -eq "FAIL") { $script:failures++ }
    if ($State -eq "WARN") { $script:warnings++ }
}

Write-Host "Code Archaeologist environment check" -ForegroundColor White
Write-Host "Repository: $Root"

Write-CaHeading "Toolchain"

if (Test-CaCommand "git") {
    Record "Git" "PASS" ((git --version) -join " ")
} else {
    Record "Git" "FAIL" "Git is required to clone repositories for analysis."
}

if (Test-CaCommand "python") {
    $pythonVersion = (python --version 2>&1) -join " "
    if ($pythonVersion -match "Python (\d+)\.(\d+)") {
        $major = [int]$Matches[1]
        $minor = [int]$Matches[2]
        if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 11)) {
            Record "Python" "PASS" $pythonVersion
        } else {
            Record "Python" "WARN" "$pythonVersion (3.11+ recommended)"
        }
    } else {
        Record "Python" "WARN" $pythonVersion
    }
} else {
    Record "Python" "WARN" "Not on PATH. uv can still manage its own interpreter."
}

if (Test-CaCommand "uv") {
    Record "uv" "PASS" ((uv --version) -join " ")
} else {
    Record "uv" "FAIL" "Install uv: https://docs.astral.sh/uv/"
}

if (Test-CaCommand "node") {
    $nodeVersion = (node --version) -join " "
    if ($nodeVersion -match "v(\d+)") {
        if ([int]$Matches[1] -ge 18) {
            Record "Node.js" "PASS" $nodeVersion
        } else {
            Record "Node.js" "FAIL" "$nodeVersion (Next.js 15 needs Node 18.18+)"
        }
    } else {
        Record "Node.js" "WARN" $nodeVersion
    }
} else {
    Record "Node.js" "FAIL" "Node.js 18.18+ is required."
}

if (Test-CaCommand "npm") {
    Record "npm" "PASS" ((npm --version) -join " ")
} else {
    Record "npm" "FAIL" "npm is required to build the frontend."
}

Write-CaHeading "Project"

if (Test-Path (Join-Path $Backend "pyproject.toml")) {
    Record "Backend project" "PASS" "backend\pyproject.toml"
} else {
    Record "Backend project" "FAIL" "backend\pyproject.toml is missing."
}

if (Test-Path (Join-Path $Backend ".venv")) {
    Record "Backend deps" "PASS" "backend\.venv present"
} else {
    Record "Backend deps" "WARN" "Run 'uv sync' in backend\ first."
}

if (Test-Path (Join-Path $Frontend "node_modules")) {
    Record "Frontend deps" "PASS" "frontend\node_modules present"
} else {
    Record "Frontend deps" "FAIL" "Run 'npm install' in frontend\ first."
}

if (Test-Path (Join-Path $Frontend ".next")) {
    $buildId = Join-Path $Frontend ".next\BUILD_ID"
    if (Test-Path $buildId) {
        $age = [int]((Get-Date) - (Get-Item $buildId).LastWriteTime).TotalMinutes
        Record "Production build" "PASS" "frontend\.next built $age minute(s) ago"
    } else {
        Record "Production build" "WARN" "frontend\.next exists but has no BUILD_ID. Run scripts\prepare-demo.ps1."
    }
} else {
    Record "Production build" "WARN" "No production build yet. Run scripts\prepare-demo.ps1."
}

$envFile = Join-Path $Backend ".env"
if (Test-Path $envFile) {
    Record "Backend .env" "PASS" "backend\.env present (ignored by Git)"
} else {
    Record "Backend .env" "WARN" "Copy backend\.env.example to backend\.env."
}

if (Test-CaGeminiKeyConfigured -EnvFile $envFile) {
    Record "Gemini key" "PASS" "Configured (value not shown)"
} else {
    Record "Gemini key" "WARN" "Not configured. Git analysis works; AI answers fall back to retrieved evidence."
}

Write-CaHeading "Ports"

foreach ($entry in @(@{ Port = 8000; Role = "API" }, @{ Port = 3000; Role = "Web" })) {
    $owners = @(Get-CaPortOwner -Port $entry.Port)
    if ($owners.Count -eq 0) {
        Record "Port $($entry.Port) ($($entry.Role))" "PASS" "Free"
    } else {
        $detail = ($owners | ForEach-Object { "$($_.Name) PID $($_.Pid)" }) -join ", "
        Record "Port $($entry.Port) ($($entry.Role))" "WARN" "In use by $detail"
    }
}

Write-CaHeading "Running services"

try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 4 -ErrorAction Stop
    Record "API /health" "PASS" "status=$($health.status) ai_available=$($health.ai_available)"
} catch {
    Record "API /health" "WARN" "Not responding. Start the backend if you expected it running."
}

try {
    $web = Invoke-WebRequest -Uri "http://127.0.0.1:3000" -TimeoutSec 6 -UseBasicParsing -ErrorAction Stop
    Record "Web root" "PASS" "HTTP $($web.StatusCode)"
} catch {
    Record "Web root" "WARN" "Not responding. Start the frontend if you expected it running."
}

Write-Host ""
if ($failures -gt 0) {
    Write-Host "DOCTOR: $failures blocking problem(s), $warnings warning(s)." -ForegroundColor Red
    exit 1
}
if ($warnings -gt 0) {
    Write-Host "DOCTOR: OK with $warnings warning(s)." -ForegroundColor Yellow
    exit 0
}
Write-Host "DOCTOR: ALL CHECKS PASSED" -ForegroundColor Green
exit 0
