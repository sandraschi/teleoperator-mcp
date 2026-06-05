# vBoomy proof loop — register vbot + print teleop URLs
param(
    [string]$RoboticsUrl = "http://127.0.0.1:12230",
    [string]$TeleopWeb = "http://127.0.0.1:10900"
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
& (Join-Path $here "register-vboomy.ps1") -RoboticsUrl $RoboticsUrl

Write-Host ""
Write-Host "vBoomy teleop URLs:"
Write-Host "  Local:  $TeleopWeb/#/?robot=vboomy"
Write-Host "  WS:     ws://127.0.0.1:10901/ws/teleop?robot=vboomy"
Write-Host ""
Write-Host "Ensure:"
Write-Host "  1. Resonite OSC input on port 9000"
Write-Host "  2. ProtoFlux receivers — docs/resonite/VBOOMY_OSC.md"
Write-Host "  3. robotics-mcp running on $RoboticsUrl"
Write-Host "  4. teleoperator backend + webapp running"
