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
    Set-Location webapp; bun install
    uv run pre-commit install

clean:
    if (Test-Path -Path "__pycache__") { Remove-Item -Recurse -Force "__pycache__" }
    if (Test-Path -Path ".pytest_cache") { Remove-Item -Recurse -Force ".pytest_cache" }

serve port=PORT:
    uv run python -m teleoperator_mcp.server --mode dual --port {{port}}

stdio:
    uv run python -m teleoperator_mcp.server --mode stdio

web:
    Set-Location webapp; bun run dev

dev:
    uv run uvicorn teleoperator_mcp.server:app --reload --port {{PORT}} --host {{HOST}}

lint:
    uv run ruff check .
    Set-Location webapp; bunx tsc --noEmit
    Set-Location webapp; bunx biome check src/

types:
    uv run pyright src/

fmt:
    uv run ruff format .

fix:
    uv run ruff check . --fix
    uv run ruff format .

test:
    uv run pytest tests/ -v

gates-green: lint types test

# --- Headless WS integration harness  proves pose pipeline against live stack ---
integration-test:
    uv run python scripts/ws-integration-harness.py --frames 60 --look

# --- Latency benchmark (motion-to-command; backend must be running) ---
latency-bench:
    uv run python scripts/latency-bench.py

# --- Publish a curated LeRobot dataset to the hub (add --push to upload) ---
publish-hub:
    uv run python scripts/publish-lerobot-hub.py --input dist/lerobot_export --repo teleop-datasets/teleoperator

ci:
    uv sync --all-extras
    uv run pytest tests/ -q
    Set-Location webapp; bun install --frozen-lockfile; bun run check
    Set-Location webapp; bun run biome:ci

# --- Tauri Native ---

# Build Tauri native desktop app (full pipeline: frontend + backend)
build-native:
    Set-Location '{{justfile_directory()}}\native'
    $env:Path = "$env:USERPROFILE\.cargo\bin;$env:Path"
    pwsh -NoProfile -File '{{justfile_directory()}}\native\build.ps1'

# One command: pre-flight checks -> build -> genuine CUA verification.
tauri: tauri-preflight build-native cua-nsis-test

# Fails fast if pywinauto/pyinstaller aren't real project deps (both caused
# silent false passes fleet-wide on 2026-09-17 -- see mcp-central-docs
# HANDOVER.md). Seconds, not a multi-minute Rust compile, to catch it.
tauri-preflight:
    @echo "== Tauri pre-flight checks =="
    uv run python -c "import pywinauto"; if ($LASTEXITCODE -ne 0) { Write-Error "FATAL: pywinauto not importable -- run: uv add --dev pywinauto pillow pytesseract"; exit 1 }
    if (-not (Test-Path '.venv\Scripts\pyinstaller.exe')) { Write-Error "FATAL: pyinstaller missing from project venv -- run: uv add --dev pyinstaller pefile altgraph"; exit 1 }
    $gi = Get-Content .gitignore -Raw -ErrorAction SilentlyContinue; if ($gi -notmatch 'resources.*\.exe') { Write-Warning "gitignore may not cover resources/*.exe" }; if ($gi -notmatch 'cua-reports') { Write-Warning "gitignore may not cover cua-reports/" }
    @echo "== Pre-flight OK =="


# Bootstrap: install dev deps + pre-commit hook
