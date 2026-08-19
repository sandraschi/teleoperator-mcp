# Install — teleoperator-mcp

> **First time?** Complete [docs/ONBOARDING.md](docs/ONBOARDING.md) before expecting live
> robot calls or video return.

## Prerequisites

- Python 3.12+ and [uv](https://docs.astral.sh/uv/) (fleet: `C:\Users\sandr\.local\bin\uv.exe`)
- [bun](https://bun.sh) — webapp package manager (fleet standard)
- [just](https://github.com/casey/just) — task runner (optional but recommended)
- Git

## Option A — uv-managed (recommended for development)

```powershell
git clone https://github.com/sandraschi/teleoperator-mcp
cd teleoperator-mcp
just bootstrap            # uv sync --all-extras + bun install + pre-commit install
Copy-Item .env.example .env
.\webapp\start.bat -WithTailscaleServe
```

- Webapp: http://localhost:10900
- Backend health: http://127.0.0.1:10901/api/v1/health
- MCP HTTP: http://127.0.0.1:10901/mcp

## Option B — manual

```powershell
uv sync --all-extras
Set-Location webapp; bun install; Set-Location ..
# Terminal 1: backend
uv run python -m teleoperator_mcp.server --mode dual --port 10901
# Terminal 2: webapp
Set-Location webapp; bun run dev
```

## Option C — Claude Desktop / IDE (stdio)

```json
{
  "mcpServers": {
    "teleoperator-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/teleoperator-mcp", "python", "-m", "teleoperator_mcp.server", "--mode", "stdio"]
    }
  }
}
```

## Option D — MCPB bundle

```powershell
just mcpb-pack      # fresh-stages src/ -> mcpb/src and packs dist/teleoperator-mcp-v0.1.0.mcpb
```

## Option E — Tauri desktop app (native/)

```powershell
just build-native   # requires Rust toolchain + Tauri CLI
```

## Verify

```powershell
Invoke-RestMethod http://127.0.0.1:10901/api/v1/health
```

`status: ok` and `onboarding.configured: true` once yahboom-mcp is reachable. Before driving
from a headset, **claim the robot** (`POST /api/v1/session/claim` or the Home page claim UI) —
the WS gate requires it, estop stays open. Recorded episodes include synced video frames via
the egress sink (see [docs/LEROBOT.md](docs/LEROBOT.md)). See
[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) if anything is off.
