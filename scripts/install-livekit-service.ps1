$ErrorActionPreference = "Stop"
$log = "D:\Dev\repos\myconf\livekit-service-setup.log"
$nssm = "C:\Users\sandr\AppData\Local\Microsoft\WinGet\Links\nssm.exe"
$exe = "C:\Users\sandr\AppData\Local\Programs\LiveKit\livekit-server.exe"
$cfg = "D:\Dev\repos\myconf\livekit.yaml"
$stdout = "D:\Dev\repos\myconf\logs\livekit.out.log"
$stderr = "D:\Dev\repos\myconf\logs\livekit.err.log"

try {
    New-Item -ItemType Directory -Force -Path "D:\Dev\repos\myconf\logs" | Out-Null

    $old = Get-Service LiveKitSFU -ErrorAction SilentlyContinue
    if ($old) {
        sc.exe stop LiveKitSFU | Out-Null
        Start-Sleep -Seconds 2
        sc.exe delete LiveKitSFU | Out-Null
        Start-Sleep -Seconds 2
    }

    & $nssm install LiveKitSFU $exe "--config" $cfg | Out-File $log
    & $nssm set LiveKitSFU AppDirectory "C:\Users\sandr\AppData\Local\Programs\LiveKit" | Out-Null
    & $nssm set LiveKitSFU DisplayName "LiveKit SFU (myconf teleop video)" | Out-Null
    & $nssm set LiveKitSFU Description "LiveKit WebRTC SFU for teleoperator-mcp video return (myconf livekit.yaml)" | Out-Null
    & $nssm set LiveKitSFU Start SERVICE_AUTO_START | Out-Null
    & $nssm set LiveKitSFU AppStdout $stdout | Out-Null
    & $nssm set LiveKitSFU AppStderr $stderr | Out-Null
    & $nssm set LiveKitSFU AppRotateFiles 1 | Out-Null
    & $nssm set LiveKitSFU AppRotateBytes 10485760 | Out-Null
    & $nssm set LiveKitSFU AppExit Default Restart | Out-Null
    & $nssm set LiveKitSFU AppRestartDelay 5000 | Out-Null
    & $nssm set LiveKitSFU Throttle 0 | Out-Null

    sc.exe start LiveKitSFU | Out-Null
    Start-Sleep -Seconds 6
    $svc = Get-Service LiveKitSFU
    "NSSM_STATUS=$($svc.Status) STARTTYPE=$($svc.StartType)" | Out-File $log -Append
    $conn = Get-NetTCPConnection -LocalPort 15580 -State Listen -ErrorAction SilentlyContinue
    if ($conn) { "PORT=15580 LISTENING pid=$($conn.OwningProcess)" | Out-File $log -Append }
    else { "PORT=15580 NOT LISTENING" | Out-File $log -Append }
} catch {
    "ERROR: $($_.Exception.Message)" | Out-File $log -Append
}
