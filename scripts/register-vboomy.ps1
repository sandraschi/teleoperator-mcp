# Register vBoomy virtual robot with robotics-mcp (Resonite OSC spawn)
param(
    [string]$RoboticsUrl = "http://127.0.0.1:12230",
    [string]$RobotId = "vbot_yahboom_01"
)

$ErrorActionPreference = "Stop"

Write-Host "Checking robotics-mcp at $RoboticsUrl ..."
$health = Invoke-RestMethod -Uri "$RoboticsUrl/api/v1/health" -Method Get
Write-Host "  status: $($health.status)"

$body = @{
    robot_id   = $RobotId
    robot_type = "yahboom"
    platform   = "resonite"
    metadata   = @{
        display_name = "vBoomy"
        scale        = 1.0
        position     = @{ x = 0.0; y = 0.0; z = 0.0 }
    }
} | ConvertTo-Json -Depth 5

Write-Host "Registering $RobotId (platform=resonite, auto-spawn OSC) ..."
$robot = Invoke-RestMethod -Method Post -Uri "$RoboticsUrl/api/v1/robots" -Body $body -ContentType "application/json"
Write-Host "  registered: $($robot.robot_id) virtual=$($robot.is_virtual)"

Write-Host "Done. Use teleoperator ?robot=vboomy"
