# Restart teleoperator backend with spoken warnings (speech-mcp or Windows SAPI)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

function Invoke-TeleopSpeak {
    param([string]$Text)
    try {
        $body = @{ text = $Text; provider = "windows" } | ConvertTo-Json
        Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:10909/api/v1/tts" -ContentType "application/json" -Body $body -TimeoutSec 45 | Out-Null
    }
    catch {
        Add-Type -AssemblyName System.Speech
        $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
        $synth.Speak($Text)
    }
}

Invoke-TeleopSpeak "Warning. Teleoperator backend restarting in five seconds. Robot will stop."
Write-Host "Restart in 5 seconds..."
Start-Sleep -Seconds 5

$conn = netstat -ano | Select-String ":10901" | Select-String "LISTENING"
if ($conn) {
    $procId = ($conn -split "\s+")[-1]
    if ($procId -match '^\d+$') {
        Write-Host "Stopping PID $procId on port 10901"
        Stop-Process -Id ([int]$procId) -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }
}

if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            Set-Item -Path "env:$($Matches[1].Trim())" -Value $Matches[2].Trim()
        }
    }
}

Write-Host "Starting backend :10901 ..."
Start-Process pwsh -ArgumentList @(
    "-NoLogo", "-NoExit", "-Command",
    "Set-Location '$PWD'; uv run python -m teleoperator_mcp.server --mode dual --port 10901"
) -WindowStyle Minimized

Start-Sleep -Seconds 4
try {
    $h = Invoke-RestMethod -Uri "http://127.0.0.1:10901/api/v1/health" -TimeoutSec 5
    Write-Host "Health OK uptime=$($h.uptime_s)"
    Invoke-TeleopSpeak "Teleoperator backend is online."
}
catch {
    Write-Host "Health check failed: $($_.Exception.Message)"
    Invoke-TeleopSpeak "Warning. Teleoperator backend may not have started correctly."
}
