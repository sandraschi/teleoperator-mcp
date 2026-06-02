# Start LiveKit MJPEG publisher (bench / ops)
$ErrorActionPreference = "Stop"
$base = "http://127.0.0.1:10901"
Write-Host "Starting LiveKit publisher via $base ..."
$result = Invoke-RestMethod -Method Post -Uri "$base/api/v1/livekit/publisher/start"
$result | ConvertTo-Json -Depth 5
if (-not $result.success) {
    exit 1
}
Start-Sleep -Seconds 2
$status = Invoke-RestMethod -Uri "$base/api/v1/livekit/status"
Write-Host "Status:"
$status | ConvertTo-Json -Depth 5
