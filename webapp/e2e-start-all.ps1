# Playwright: backend (10901) in background, then Vite foreground (10900)
# Idempotent: if a healthy stack is already serving, exit 0 and let Playwright reuse it.
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$RepoRoot = Split-Path -Parent $ProjectRoot

function Test-StackUp {
    try {
        $h = Invoke-RestMethod -Uri "http://127.0.0.1:10901/api/v1/health" -TimeoutSec 3
        if ($h.status -ne "ok") { return $false }
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:10900/" -UseBasicParsing -TimeoutSec 3
        return $r.StatusCode -eq 200
    } catch {
        return $false
    }
}

if (Test-StackUp) {
    Write-Host "Stack already healthy on 10900/10901 - reusing."
    exit 0
}

if (-not (Test-Path $Python)) {
    Write-Error "Python venv not found at $Python. Run 'uv sync' in project root first."
}

function Stop-PortListeners([int]$port) {
    netstat -ano -p tcp | Select-String ":$port\s" | ForEach-Object {
        $parts = ($_.Line -replace '\s+', ' ').Trim().Split(' ')
        $procId = [int]$parts[-1]
        if ($procId -gt 4) {
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        }
    }
}

Stop-PortListeners 10900
Stop-PortListeners 10901
Start-Sleep -Seconds 1

$backend = Start-Process -FilePath $Python -ArgumentList @(
    "-m", "teleoperator_mcp.server", "--mode", "dual", "--port", "10901"
) -WorkingDirectory $RepoRoot -PassThru -WindowStyle Hidden

$ready = $false
for ($i = 0; $i -lt 90; $i++) {
    try {
        $h = Invoke-RestMethod -Uri "http://127.0.0.1:10901/api/v1/health" -TimeoutSec 3
        if ($h.status -eq "ok") {
            $ready = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 1
    }
}
if (-not $ready) {
    Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
    Write-Error "Backend did not become ready on 10901"
}

try {
    & npm run dev -- --host 127.0.0.1 --port 10900 --strictPort
} finally {
    Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
}
