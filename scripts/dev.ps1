# Code Archaeologist — local development helper (Windows PowerShell)
#
#   powershell -ExecutionPolicy Bypass -File scripts\dev.ps1
#
# Starts the API with --reload and the Next.js dev server in two new windows.
# Use scripts\demo.ps1 for anything being demonstrated: hot reload and the dev
# error overlay are exactly what you do not want in front of a judge.

$ErrorActionPreference = "Stop"

. "$PSScriptRoot\_common.ps1"

$Root = Get-CaRoot

foreach ($entry in @(@{ Port = 8000; Role = "API" }, @{ Port = 3000; Role = "Web" })) {
    $owners = @(Get-CaPortOwner -Port $entry.Port)
    if ($owners.Count -gt 0) {
        Write-Host "Port $($entry.Port) ($($entry.Role)) is already in use:" -ForegroundColor Red
        foreach ($owner in $owners) {
            Write-Host "  PID $($owner.Pid)  $($owner.Name)  $($owner.Path)" -ForegroundColor Yellow
        }
        Write-Host "Close that process yourself, then run this script again." -ForegroundColor Red
        exit 1
    }
}

Start-Process powershell -WorkingDirectory (Join-Path $Root "backend") -ArgumentList @(
    "-NoExit",
    "-Command",
    "`$Host.UI.RawUI.WindowTitle = 'Code Archaeologist API (dev)'; uv run python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
)

Start-Process powershell -WorkingDirectory (Join-Path $Root "frontend") -ArgumentList @(
    "-NoExit",
    "-Command",
    "`$Host.UI.RawUI.WindowTitle = 'Code Archaeologist Web (dev)'; npm run dev"
)

Write-Host "Started backend (http://127.0.0.1:8000) and frontend (http://127.0.0.1:3000) in separate windows." -ForegroundColor Green
