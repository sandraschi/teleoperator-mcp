set windows-shell := ["pwsh.exe", "-NoLogo", "-Command"]

export NAME := "Teleoperator MCP"
export DESC := "WebXR teleoperation gateway"
export VER  := "0.1.0"
export PORT := "10901"
export WEB_PORT := "10900"
export HOST := "0.0.0.0"

default:
    @pwsh.exe -NoProfile -ExecutionPolicy Bypass -File ../mcp-central-docs/scripts/just-dashboard.ps1 -Path .

bootstrap:
    uv sync --all-extras
    Set-Location webapp; npm install

clean:
    if (Test-Path -Path "__pycache__") { Remove-Item -Recurse -Force "__pycache__" }
    if (Test-Path -Path ".pytest_cache") { Remove-Item -Recurse -Force ".pytest_cache" }

serve port=PORT:
    uv run python -m teleoperator_mcp.server --mode dual --port {{port}}

stdio:
    uv run python -m teleoperator_mcp.server --mode stdio

web:
    Set-Location webapp; npm run dev

dev:
    uv run uvicorn teleoperator_mcp.server:app --reload --port {{PORT}} --host {{HOST}}

lint:
    uv run ruff check .
    Set-Location webapp; npx tsc --noEmit

fix:
    uv run ruff check . --fix
    uv run ruff format .

test:
    uv run pytest tests/ -v
