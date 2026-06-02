# Teleoperator MCP - start backend (port 10901)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
uv run python -m teleoperator_mcp.server --mode dual --port 10901
