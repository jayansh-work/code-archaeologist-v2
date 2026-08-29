# Code Archaeologist — local development helper (Windows)

Starts the API and the Next.js app in two new PowerShell windows.
README commands remain the supported path if this script is unused.

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")

Start-Process powershell -WorkingDirectory (Join-Path $Root "backend") -ArgumentList @(
    "-NoExit",
    "-Command",
    "uv run python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
)

Start-Process powershell -WorkingDirectory (Join-Path $Root "frontend") -ArgumentList @(
    "-NoExit",
    "-Command",
    "npm run dev"
)

Write-Host "Started backend (127.0.0.1:8000) and frontend (127.0.0.1:3000) in separate windows."
