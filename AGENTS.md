# Teleoperator MCP — AGENTS.md

WebXR teleoperation gateway for the MCP fleet: VR pose from Pico/Meta Quest to
fleet robots (Boomy first), MCP supervision tools, LiveKit video return.

## Reading order

1. `CLAUDE.md` — entry points, key files, stack
2. `docs/ARCHITECTURE.md` — two-pipe map (control vs video), ports
3. `docs/DUAL_MODE_ARCHITECTURE.md` — arbiter / authority model
4. `src/teleoperator_mcp/` — source layout below

## Directory map

| Path | Purpose |
|------|---------|
| `src/teleoperator_mcp/server.py` | Unified FastAPI + FastMCP gateway (tools, REST, WebSocket) |
| `src/teleoperator_mcp/config.py` | pydantic-settings (TELEOP_ prefix) |
| `src/teleoperator_mcp/adapters/` | Robot adapters (boomy, bumi, vboomy) + registry |
| `src/teleoperator_mcp/arbiter/` | Dual-mode authority (DIRECT/AUTO) |
| `src/teleoperator_mcp/mappers/` | Controller/pose → command mappers |
| `src/teleoperator_mcp/producers/` | ProducerCommand producers (human_pose) |
| `src/teleoperator_mcp/recording/` | LeRobot JSONL session recording |
| `src/teleoperator_mcp/ws/` | WebSocket teleop handler |
| `src/teleoperator_mcp/livekit/` | LiveKit publisher + tokens |
| `webapp/src/` | React WebXR client (XR session, HUD, pose) |
| `native/` | Tauri 2.0 NSIS wrapper |
| `scripts/` | Bench, CUA smoke, fleet start helpers |

## Conventions

- Python: FastMCP 3.4+, FastAPI, uvicorn, structlog-style logging
- Ports: backend 10901, webapp 10900 (fleet registry)
- Gates: `just lint` (ruff + tsc), `just test` (pytest), `uv run pyright src/`
