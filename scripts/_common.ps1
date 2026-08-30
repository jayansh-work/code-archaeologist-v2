# Shared helpers for the Code Archaeologist Windows scripts.
# Dot-source this file: . "$PSScriptRoot\_common.ps1"

$script:CaOk = 0

function Get-CaRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

function Write-CaHeading([string]$Text) {
    Write-Host ""
    Write-Host "== $Text ==" -ForegroundColor Cyan
}

function Write-CaResult([string]$Name, [string]$State, [string]$Detail = "") {
    $color = switch ($State) {
        "PASS" { "Green" }
        "WARN" { "Yellow" }
        default { "Red" }
    }
    $label = $State.PadRight(4)
    Write-Host "  [$label] " -ForegroundColor $color -NoNewline
    Write-Host ("{0,-28} {1}" -f $Name, $Detail)
}

# Returns the listening processes on a TCP port, or an empty array.
function Get-CaPortOwner([int]$Port) {
    $owners = @()
    try {
        $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop
    } catch {
        return $owners
    }
    foreach ($connection in $connections) {
        $process = Get-Process -Id $connection.OwningProcess -ErrorAction SilentlyContinue
        $owners += [pscustomobject]@{
            Pid  = $connection.OwningProcess
            Name = if ($process) { $process.ProcessName } else { "unknown" }
            Path = if ($process) { $process.Path } else { $null }
        }
    }
    return $owners
}

function Test-CaPortFree([int]$Port) {
    return (@(Get-CaPortOwner -Port $Port).Count -eq 0)
}

function Test-CaCommand([string]$Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

# True when the key looks configured, without ever reading its value out loud.
function Test-CaGeminiKeyConfigured([string]$EnvFile) {
    foreach ($name in @("GEMINI_API_KEY", "GOOGLE_API_KEY")) {
        $value = [Environment]::GetEnvironmentVariable($name)
        if ($value -and $value.Trim().Length -gt 0) {
            return $true
        }
    }
    if (-not (Test-Path $EnvFile)) {
        return $false
    }
    foreach ($line in Get-Content $EnvFile) {
        if ($line -match '^\s*(GEMINI_API_KEY|GOOGLE_API_KEY)\s*=\s*(.+)\s*$') {
            if ($Matches[2].Trim().Trim('"').Trim("'").Length -gt 0) {
                return $true
            }
        }
    }
    return $false
}

function Get-CaDemoStateDir([string]$Root) {
    # Inside tmp/ so it is already covered by .gitignore.
    $dir = Join-Path $Root "tmp\demo"
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    return $dir
}
