set windows-shell := ["powershell.exe", "-NoProfile", "-Command"]
import 'scripts/just/fleet.just'

export NAME := "Teleoperator MCP"
export DESC := "WebXR teleoperation gateway"
export VER  := "0.1.0"
export PORT := "10901"
export WEB_PORT := "10900"
export HOST := "0.0.0.0"

default:
    @just --list

bootstrap:
    uv sync --all-extras
    Set-Location webapp; npm install
    uv run pre-commit install

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

fmt:
    uv run ruff format .

fix:
    uv run ruff check . --fix
    uv run ruff format .

test:
    uv run pytest tests/ -v

# Headless WS integration harness — proves pose pipeline against live stack
integration-test:
    uv run python scripts/ws-integration-harness.py --frames 60 --look

ci:
    uv sync --all-extras
    uv run pytest tests/ -q
    Set-Location webapp; npm ci; npm run check

# ── Tauri Native ───────────────────────────────────────────────────────────────

# Build Tauri native desktop app (full pipeline: frontend + backend)
build-native:
    Set-Location '{{justfile_directory()}}\native'
    $env:Path = "$env:USERPROFILE\.cargo\bin;$env:Path"
    npx @tauri-apps/cli build


# Bootstrap: install dev deps + pre-commit hook
