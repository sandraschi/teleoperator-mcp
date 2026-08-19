$ErrorActionPreference = "Stop"
$log = "D:\Dev\repos\teleconference-mcp\livekit-service-setup.log"

try {
    sc.exe start LiveKitSFU | Out-Null
    Start-Sleep -Seconds 5
    $svc = Get-Service LiveKitSFU
    "STARTED_STATUS=$($svc.Status)" | Out-File $log -Append
    $conn = Get-NetTCPConnection -LocalPort 15580 -State Listen -ErrorAction SilentlyContinue
    if ($conn) { "PORT=15580 LISTENING pid=$($conn.OwningProcess)" | Out-File $log -Append }
    else { "PORT=15580 NOT LISTENING" | Out-File $log -Append }
} catch {
    "ERROR: $($_.Exception.Message)" | Out-File $log -Append
}
