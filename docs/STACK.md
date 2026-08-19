# Stack

Full technology stack for `teleoperator-mcp`, present and planned. Marks clearly what exists today versus what the [dual-mode architecture](DUAL_MODE_ARCHITECTURE.md) adds.

Status legend: **[now]** shipped in v0.1 - **[next]** near-term (v0.2-v0.5) - **[later]** hardware-gated (v1.5+).

---

## 1. Backend (Goliath)

| Concern | Choice | Status | Notes |
|---------|--------|--------|-------|
| Language / runtime | Python 3.12+, `uv` | now | `uv run python ...`, never naked python |
| MCP framework | FastMCP 3.2 (`fastmcp>=3.2,<4`) | now | `mcp.http_app()` mounted under FastAPI at `/mcp` |
| Web framework | FastAPI `>=0.115` | now | Justified over Starlette: external-facing surface = REST health + WebSocket + MCP HTTP. Per `STARLETTE_NO_PYDANTIC_STANDARD` this earns FastAPI. |
| ASGI server | uvicorn[standard] `>=0.32` | now | `--mode dual` runs MCP + REST + WS in one process |
| HTTP client (downstream) | httpx (async) | now | Calls yahboom-mcp REST |
| Config | pydantic-settings `>=2`, env prefix `TELEOP_` | now | `src/teleoperator_mcp/config.py` |
| Logging | structlog `>=24` | now (dep present) | stderr, JSON-RPC-safe |
| Prefab UI | prefab-ui `>=0.14` | dep present, not wired | Fleet mandate: status/list/stats tools must return `ToolResult` + `PrefabApp`. `teleop_status` is still a plain dict. See TODO. |

### Backend modules (`src/teleoperator_mcp/`)

- `server.py` - FastAPI app, FastMCP tools (`teleop_status`, `teleop_configure`, `teleop_estop`), `/api/v1/health`, `/ws/teleop`, lifespan nesting the MCP http_app lifespan correctly.
- `ws/handler.py` - single-session WebSocket handler, latched watchdog, estop message type, `trigger_estop()`. **[now]**
- `mappers/boomy.py` - `BoomyMapper`: head -> PTZ, stick -> cmd_vel; `api_base` reads live settings. **[now]**
- `arbiter/` - authority arbiter, per-group ownership, takeover, bumpless handoff. **[next, does not exist]**
- `adapters/` - `RobotAdapter`, `BoomyAdapter`, `RobotCapabilities`. **[now]**
- `recording/` - LeRobot JSONL session recorder (M4). **[now]**
- `livekit/` - MJPEG publisher, JWT tokens (M5). **[now]**

---

## 2. Data plane (hot path, ~30 Hz)

| Concern | Choice | Status |
|---------|--------|--------|
| Transport | WebSocket `/ws/teleop?robot=<id>` | now |
| Message schema | JSON pose frame v1 (head yaw/pitch/roll, controller axes + buttons), 500 ms heartbeat | now |
| Rate | 30 Hz send cap client-side; PTZ subsampled to ~10 Hz server-side | now |
| Safety | deadman (trigger > 0.5), squeeze estop, MCP teleop_estop, latched watchdog (300 ms), single-session lock | now |

**Rule:** pose never traverses MCP tool calls. MCP is the cold control plane only.

---

## 3. VR client (Pico 4 browser)

| Concern | Choice | Status | Notes |
|---------|--------|--------|-------|
| Build | Vite 6 + TypeScript 5.6 | now | `webapp/` |
| 3D / XR | Three.js 0.170, WebXR Device API | now | `immersive-vr`, `local-floor` reference space |
| Pose source | `getViewerPose` -> YXZ Euler; Gamepad API for axes/trigger/squeeze | now | `xr-session.ts` |
| Transport client | native `WebSocket`, ack-based RTT, exponential reconnect | now | `pose-stream.ts` |
| HUD | chin-strip canvas texture; redraw only when line changes | now | `hud.ts` |
| Video return | LiveKit track → Three.js `VideoTexture` plane | now (M5) | `livekit-video.ts`; see [LIVEKIT.md](LIVEKIT.md) |
| Package manager | npm | now | Fleet standard is **Bun** (`BUN_STANDARDS`); migration is a TODO |

Serving requires **HTTPS** (WebXR constraint). See [HTTPS.md](HTTPS.md).

---

## 4. Autonomy (the Mode B brain)

| Concern | Choice | Status | Notes |
|---------|--------|--------|-------|
| Manipulation VLA | **WALL-OSS / WALL-OSS-0.5** (X Square, 4B, open) OR **UnifoLM-VLA-0** (Unitree, Qwen2.5-VL-7B, open) | later | Producer interface is model-agnostic. WALL-OSS leans dexterous-hand-native; on a gripper, fine-tune onto gripper actions (its 0.5 use case) or prefer a gripper-native policy. |
| VLA runtime | LeRobot / WallX on the RTX 4090 | later | 4B fits comfortably; run **out-of-process** so a policy crash cannot drop the arbiter/safety layer |
| Locomotion (biped) | platform's own RL gait controller | later | NOT the VLA. Commanded by velocity/heading or nav goal |
| Navigation | ROS 2 Nav2 / occupancy grid | later | Coarse metric map; static-world waypoints |

---

## 5. Perception

Two representations at two scales. Do not conflate them (see DUAL_MODE §perception).

| Layer | Sensor | Representation | Status |
|-------|--------|----------------|--------|
| Navigation | base LiDAR | coarse SLAM occupancy map + **saved waypoints** for fixed furniture (the fridge does not move) | later |
| Manipulation | head stereo / RGB-D (R1-A5 binocular: RGB+depth 1280x720@30) | none pre-built; **live closed-loop** policy perception finds handle + can | later |

Static world -> map. Dynamic targets (door angle, can position) -> live policy. The global map never carries the can.

---

## 6. Robot hardware ladder

| Rung | Platform | Locomotion | Hands | Programmable | Role |
|------|----------|-----------|-------|--------------|------|
| 0 | Boomy (Yahboom Raspbot v2) | wheeled | none | yes (RPi5/ROS 2) | control-plane validation, zero physical risk |
| 1 | Unitree R1-A5-D / A7-D | wheeled | gripper or dexterous (modular) | yes (research SKU) | manipulation handoff, no balance risk. Base $4,290 torso bare; hands+Jetson+base extra |
| 2 (optional) | Noetix Bumi / full R1 | bipedal | Bumi: none | Bumi closed; R1 only via EDU | legged-locomotion handoff experiment only |

SKU traps (do not misbuy): R1 Air ($4,900) / R1 standard ($5,900) are **closed**, no functional hands; only **EDU** (~$10-12K+) is programmable; dexterous hands only on Pro ($20-35K).

**Controller-swap path (accepted):** buy a sealed unit, remove stock controller, drop in RPi/Jetson, drive over the motor bus. Tractable on **wheeled** (no balance policy to reimplement); on a biped you inherit the balance/locomotion controller, which is the hard part. Voids warranty/ToS; the real cost is safety ownership.

---

## 7. Fleet integration

| Concern | Choice | Status |
|---------|--------|--------|
| Ports | webapp 10900, backend 10901 (WS + REST + MCP HTTP) | now; registered in WEBAPP_PORTS |
| Packaging | `uv` + `justfile` + `llms.txt` + `glama.json`; `mcpb pack` for distribution | partial |
| Install | Naked-PC standard (`Require-Command` in `start.ps1`, `INSTALL.md`) | TODO (start.ps1 minimal launcher only) |
| Data logging | LeRobot JSONL episodes (`data/teleop_recordings/`) | now (M4); parquet + video sync later |
| Downstream robot | yahboom-mcp (10892) | now |
| Video | teleconference-mcp LiveKit (15580) + teleoperator publisher | now (M5); headset sign-off pending |

---

## 8. Dev tooling

- Ruff (line length 100, py312) + pre-commit
- pytest + pytest-asyncio (`asyncio_mode = auto`); current tests cover the mapper only, WS/watchdog untested
- TypeScript `tsc --noEmit` for the webapp
- Playwright (headless) for webapp e2e - per fleet standard, not yet present
