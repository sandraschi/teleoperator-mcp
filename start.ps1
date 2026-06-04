# Repo-root launcher — delegates to webapp/start.ps1 (fleet standard).
$ErrorActionPreference = "Stop"
$launcher = Join-Path $PSScriptRoot "webapp\start.ps1"
if (-not (Test-Path $launcher)) {
    Write-Error "Missing webapp/start.ps1"
    exit 1
}
& $launcher @args
