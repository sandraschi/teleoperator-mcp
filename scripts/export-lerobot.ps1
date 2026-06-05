# Export teleop JSONL recordings to LeRobot v2.1 parquet dataset
param(
    [string]$InputDir = "data/teleop_recordings",
    [string]$OutputDir = "data/lerobot_export",
    [string]$Episodes = "",
    [int]$Fps = 30,
    [switch]$Overwrite
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $repoRoot

$argsList = @(
    "-m", "teleoperator_mcp.recording.export_lerobot",
    "--input", $InputDir,
    "--output", $OutputDir,
    "--fps", $Fps
)
if ($Episodes) { $argsList += @("--episodes", $Episodes) }
if ($Overwrite) { $argsList += "--overwrite" }

py @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Next: pip install lerobot"
Write-Host "  lerobot-train --dataset.repo_id=local/teleop --dataset.root=$OutputDir"
