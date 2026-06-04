# Milestone 1 — teleoperator stack + Tailscale Serve for Pico WebXR
# Delegates to fleet-standard webapp/start.ps1
$ErrorActionPreference = "Stop"
$launcher = Join-Path $PSScriptRoot "..\webapp\start.ps1"
& $launcher -WithTailscaleServe -Detached
