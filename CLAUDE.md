# Teleoperator MCP — CLAUDE.md

WebXR teleoperation gateway for the MCP fleet. Stream VR pose from Pico/Meta Quest
to fleet robots (Boomy via yahboom-mcp), with MCP tools for supervision and LiveKit
video return. Pose **never** traverses MCP tool calls — the webapp IS the VR client.

## Stack
- Backend: FastAPI + FastMCP 3.4+ + WebSocket + LiveKit (10901)
- Frontend: Vite + React + Three.js WebXR + Tailwind + Zustand + LiveKit (10900)
- Robot: yahboom-mcp adapter (10892), Bumi adapter, vBoomy virtual twin
- Architecture docs: docs/ARCHITECTURE.md, docs/DUAL_MODE_ARCHITECTURE.md

## Key Files
- `src/teleoperator_mcp/server.py` — unified FastAPI + FastMCP gateway (575 lines)
- `src/teleoperator_mcp/config.py` — pydantic-settings (TELEOP_ prefix)
- `src/teleoperator_mcp/adapters/` — robot adapter registry (boomy, bumi, vboomy)
- `src/teleoperator_mcp/arbiter/` — dual-mode authority (DIRECT/AUTO)
- `src/teleoperator_mcp/recording/` — LeRobot JSONL session recording
- `src/teleoperator_mcp/ws/` — WebSocket teleop handler (pose stream)
- `webapp/src/` — React webapp with XR session, HUD, pose streaming
- `native/` — Tauri 2.0 NSIS installer

## Entry Points
- `just serve` — backend on 10901 (dual mode: HTTP + MCP)
- `just web` — Vite dev on 10900
- `just dev` — uvicorn with reload on 10901
- `just test` — pytest (38 tests)
- `mcp.run(transport="stdio")` — Claude Desktop / IDE stdio
