# Fire vBoomy OSC test sequence to Resonite (port 9000)
param(
    [string]$OscHost = "127.0.0.1",
    [int]$Port = 9000,
    [string]$RobotId = "vbot_yahboom_01",
    [string]$RobotType = "yahboom",
    [string]$ResoniteApi = "http://127.0.0.1:8787"
)

$ErrorActionPreference = "Stop"

function Send-OscViaResoniteMcp {
    param([string]$Address, [object[]]$Values)
    $body = @{
        host    = $OscHost
        port    = $Port
        address = $Address
        values  = @($Values)
    } | ConvertTo-Json -Depth 5
    Invoke-RestMethod -Method Post -Uri "$ResoniteApi/api/osc/send" -Body $body -ContentType "application/json"
}

Write-Host "vBot OSC test -> ${OscHost}:${Port} ($RobotId / $RobotType)"

try {
    $null = Invoke-RestMethod -Method Post -Uri "$ResoniteApi/api/resonite/vbot/test?robot_id=$RobotId&robot_type=$RobotType&host=$OscHost&osc_port=$Port"
    Write-Host "Sent via resonite-mcp /api/resonite/vbot/test"
    exit 0
} catch {
    Write-Host "resonite-mcp not reachable ($ResoniteApi) — sending OSC steps manually..."
}

$scale = if ($RobotType -eq "mechazilla") { 2.5 } else { 1.0 }
Send-OscViaResoniteMcp "/resonite/vbot/spawn" @($RobotId, $RobotType, 0.0, 0.0, 0.0, $scale)
Start-Sleep -Milliseconds 200
Send-OscViaResoniteMcp "/robot/$RobotId/reset" @(1.0)
Start-Sleep -Milliseconds 200
Send-OscViaResoniteMcp "/robot/$RobotId/move" @(0.15, 0.0)
Start-Sleep -Milliseconds 500
Send-OscViaResoniteMcp "/robot/$RobotId/head" @(10.0, -5.0)
Start-Sleep -Milliseconds 500
Send-OscViaResoniteMcp "/robot/$RobotId/stop" @(1.0)
Write-Host "Done — check Resonite vBotRoot motion."
