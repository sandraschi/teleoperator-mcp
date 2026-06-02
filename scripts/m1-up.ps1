# Milestone 1 - start teleoperator stack + Tailscale Serve for Pico WebXR
# Run from repo root. Requires: uv, npm, tailscale CLI.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

if (-not (Test-Path "webapp\node_modules")) {
    Set-Location webapp
    npm install
    Set-Location ..
}

if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            Set-Item -Path "env:$($Matches[1].Trim())" -Value $Matches[2].Trim()
        }
    }
}

if (-not $env:TELEOP_CORS_ORIGINS) {
    $tsStatus = tailscale serve status 2>&1 | Out-String
    if ($tsStatus -match '(https://[^\s/]+\.ts\.net)') {
        $tsHost = $Matches[1]
        $env:TELEOP_CORS_ORIGINS = "$tsHost,http://localhost:10900,http://127.0.0.1:10900"
        Write-Host "TELEOP_CORS_ORIGINS=$env:TELEOP_CORS_ORIGINS"
    }
}

Write-Host "Starting backend :10901 ..."
Start-Process pwsh -ArgumentList @(
    "-NoLogo", "-NoExit", "-Command",
    "Set-Location '$PWD'; uv run python -m teleoperator_mcp.server --mode dual --port 10901"
) -WindowStyle Minimized

Start-Sleep -Seconds 2

Write-Host "Starting webapp :10900 ..."
Start-Process pwsh -ArgumentList @(
    "-NoLogo", "-NoExit", "-Command",
    "Set-Location '$PWD\webapp'; npm run dev"
) -WindowStyle Minimized

Start-Sleep -Seconds 2

Write-Host "Tailscale Serve -> http://127.0.0.1:10900"
tailscale serve --bg http://127.0.0.1:10900
tailscale serve status

Write-Host ""
Write-Host "Pico URL: open the https://*.ts.net URL above"
Write-Host "Local:    http://localhost:10900"
Write-Host "Health:   http://127.0.0.1:10901/api/v1/health"
