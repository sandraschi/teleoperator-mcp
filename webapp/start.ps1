param(
    [switch]$Headless,
    [switch]$BackendOnly,
    [switch]$FrontendOnly,
    [switch]$NoBrowser,
    [switch]$WithTailscaleServe,
    [switch]$Detached,
    [switch]$ReuseIfRunning)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$FleetStartPath = Join-Path $ProjectRoot "scripts\FleetStartMode.ps1"
if (-not (Test-Path -LiteralPath $FleetStartPath)) {
    Write-Host "ERROR: Missing vendored launcher helper: $FleetStartPath" -ForegroundColor Red
    exit 1
}
. $FleetStartPath
$FleetStart = Initialize-FleetStartMode @PSBoundParameters
Enter-FleetHeadlessConsole -Headless:$Headless -BackendOnly:$BackendOnly

$portResolve = @{
    Ports      = @($WebPort, $BackendPort)
    Label      = "teleoperator-mcp"
    AllowReuse = $ReuseIfRunning
}
if ($ReuseIfRunning) {
    $portResolve.HealthChecks = @{
        $WebPort = "http://127.0.0.1:$WebPort/"
        $BackendPort = "http://127.0.0.1:$BackendPort/api/v1/health"
    }
}
$portState = Resolve-FleetPortConflict @portResolve
if ($portState.Action -eq 'Blocked') { exit 1 }
if ($portState.Reuse) { return }
$WebPort = 10900
$BackendPort = 10901
$HealthUrl = "http://127.0.0.1:${BackendPort}/api/v1/health"
$FrontendUrl = "http://127.0.0.1:${WebPort}/"

function Import-RepoDotEnv {
    param([string]$Root)
    $envFile = Join-Path $Root ".env"
    if (-not (Test-Path $envFile)) { return }
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            Set-Item -Path "env:$($Matches[1].Trim())" -Value $Matches[2].Trim()
        }
    }
}

function Set-TeleopCorsFromTailscale {
    if ($env:TELEOP_CORS_ORIGINS) { return }
    try {
        $tsStatus = tailscale serve status 2>&1 | Out-String
        if ($tsStatus -match '(https://[^\s/]+\.ts\.net)') {
            $tsHost = $Matches[1]
            $env:TELEOP_CORS_ORIGINS = "$tsHost,http://localhost:${WebPort},http://127.0.0.1:${WebPort}"
            Write-Host "TELEOP_CORS_ORIGINS=$env:TELEOP_CORS_ORIGINS" -ForegroundColor DarkGray
            if (-not $env:TELEOP_LIVEKIT_PUBLIC_URL) {
                $wssHost = $tsHost -replace '^https://', 'wss://'
                $env:TELEOP_LIVEKIT_PUBLIC_URL = "${wssHost}:15580"
                Write-Host "TELEOP_LIVEKIT_PUBLIC_URL=$env:TELEOP_LIVEKIT_PUBLIC_URL" -ForegroundColor DarkGray
            }
        }
    } catch {
        Write-Host "Tailscale CLI not available; set TELEOP_CORS_ORIGINS in .env for Pico HTTPS." -ForegroundColor Yellow
    }
}

function Wait-BackendReady {
    param(
        [string]$Url,
        [int]$TimeoutSec = 90
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $null = Invoke-RestMethod -Uri $Url -TimeoutSec 2
            return $true
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    return $false
}

function Start-BackendProcess {
    $backendArgs = @("-NoLogo")
    if (-not $Detached) {
        $backendArgs += "-NoExit"
    }
    $backendArgs += "-Command"
    $backendArgs += "Set-Location '$ProjectRoot'; uv run python -m teleoperator_mcp.server --mode dual --port $BackendPort"
    $style = if ($Detached) { "Minimized" } else { "Normal" }
    return Start-Process pwsh -ArgumentList $backendArgs -WorkingDirectory $ProjectRoot -WindowStyle $style -PassThru
}

function Start-FrontendProcess {
    if (-not (Test-Path (Join-Path $PSScriptRoot "node_modules"))) {
        Write-Host "node_modules missing - running npm install..." -ForegroundColor Yellow
        Start-Process cmd -WorkingDirectory $PSScriptRoot -ArgumentList "/c", "npm", "install" -Wait -NoNewWindow
    }
    if ($Detached) {
        $frontendArgs = @(
            "-NoLogo", "-NoExit", "-Command",
            "Set-Location '$PSScriptRoot'; npm run dev"
        )
        return Start-Process pwsh -ArgumentList $frontendArgs -WorkingDirectory $PSScriptRoot -WindowStyle Minimized -PassThru
    }
    # npm is npm.cmd on Windows - invoke via cmd.exe (see yahboom-mcp webapp/start.ps1)
    return Start-Process cmd -WorkingDirectory $PSScriptRoot -ArgumentList "/c", "npm", "run", "dev" -NoNewWindow -PassThru
}

Write-Host ""
Write-Host "[TELEOPERATOR-MCP] WebXR gateway - web $WebPort / backend $BackendPort" -ForegroundColor Cyan

Write-Host "[1/5] Port cleanup..." -ForegroundColor Cyan

Write-Host "[2/5] Python deps (uv sync)..." -ForegroundColor Cyan
Push-Location $ProjectRoot
uv sync --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] uv sync failed." -ForegroundColor Red
    exit 1
}
Import-RepoDotEnv -Root $ProjectRoot
Set-TeleopCorsFromTailscale
Pop-Location

$serverProc = $null
$dashboardProc = $null

try {
    if ($FleetStart.RunBackend) {
        Write-Host "[3/5] Starting backend on :$BackendPort ..." -ForegroundColor Green
        $serverProc = Start-BackendProcess
        if (-not (Wait-BackendReady -Url $HealthUrl)) {
            Write-Host "[ERROR] Backend did not become ready at $HealthUrl within 90s." -ForegroundColor Red
            exit 1
        }
        Write-Host "      Backend ready." -ForegroundColor Green
    }

    if (-not $FleetStart.RunFrontend) {
        if ($Detached) { return }
        try { while ($true) { Start-Sleep -Seconds 1 } } finally { }
        return
    }

    Write-Host "[4/5] Starting Vite on :$WebPort ..." -ForegroundColor Green
    $dashboardProc = Start-FrontendProcess

    if ($WithTailscaleServe) {
        Write-Host "[5/5] Tailscale Serve -> http://127.0.0.1:$WebPort" -ForegroundColor Cyan
        tailscale serve --bg "http://127.0.0.1:${WebPort}"
        tailscale serve status
    } else {
        Write-Host "[5/5] Skipped Tailscale Serve (use -WithTailscaleServe for Pico HTTPS)." -ForegroundColor DarkGray
    }

    Write-Host ""
    Write-Host "[SUCCESS] Teleoperator stack running." -ForegroundColor Green
    Write-Host "----------------------------------------------------"
    Write-Host "  Webapp:  $FrontendUrl"
    Write-Host "  Backend: http://127.0.0.1:${BackendPort}/api/v1/health"
    Write-Host "  MCP:     http://127.0.0.1:${BackendPort}/mcp"
    Write-Host "  Pico:    https://goliath.<tailnet>.ts.net/  (after Tailscale Serve)"
    Write-Host "----------------------------------------------------"

    if (-not $FleetStart.SkipBrowser) {
        $pollAndOpen = "for (`$i = 0; `$i -lt 60; `$i++) { try { `$null = Invoke-WebRequest -Uri '$FrontendUrl' -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop; Start-Process '$FrontendUrl'; exit } catch { Start-Sleep -Seconds 1 } }"
        Start-Process pwsh -ArgumentList @("-NoProfile", "-WindowStyle", "Hidden", "-Command", $pollAndOpen)
    }

    if ($Detached) {
        return
    }

    Write-Host "Press Ctrl+C to stop..."
    while ($true) { Start-Sleep -Seconds 1 }
}
finally {
    if (-not $Detached) {
        Write-Host ""
        Write-Host "[SHUTDOWN] Stopping processes..." -ForegroundColor Yellow
        if ($serverProc) { Stop-Process -Id $serverProc.Id -Force -ErrorAction SilentlyContinue }
        if ($dashboardProc) { Stop-Process -Id $dashboardProc.Id -Force -ErrorAction SilentlyContinue }
        Write-Host "[DONE]" -ForegroundColor Green
    }
}

