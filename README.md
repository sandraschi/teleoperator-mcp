# Teleoperator MCP

WebXR teleoperation gateway for the MCP fleet, evolving into a **dual-mode teleop + telesupervision** stack. Stream head and controller pose from a **Pico 4 browser** to Goliath, map to robot commands, and (target state) hand off to an autonomous policy while the operator becomes a supervisor. Return camera video over LiveKit (v1.5).

[![FastMCP 3.2](https://img.shields.io/badge/FastMCP-3.2-7c5cfc?style=flat-square)](https://github.com/jlowin/fastmcp)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776ab?style=flat-square&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![status: alpha](https://img.shields.io/badge/status-alpha-f59e0b?style=flat-square)](#current-status)

---

## What this is

Two surfaces, two latency classes, one gateway:

- **VR client (webapp on the Pico):** captures head + controller pose, renders an in-headset HUD, displays return video. Real-time, ~30 Hz.
- **MCP server (the supervisor interface):** session config, status, gains, and — in the target architecture — mode switching, task dispatch, takeover, and e-stop. Cold path, seconds.

The 30 Hz pose stream runs over a **WebSocket**, never through MCP tool calls. The webapp is not an admin dashboard bolted onto VR; it **is** the VR client.

The larger arc (direct teleop <-> autonomy, operator as telesupervisor) is specified in **[docs/DUAL_MODE_ARCHITECTURE.md](docs/DUAL_MODE_ARCHITECTURE.md)**. v0.1 below is the direct-teleop foundation that arc refactors on top of.

---

## Documentation map

| Doc | Contents |
|-----|----------|
| **[docs/PRD.md](docs/PRD.md)** | v1 product spec: pose schema, HUD, safety, ports, env |
| **[docs/DUAL_MODE_ARCHITECTURE.md](docs/DUAL_MODE_ARCHITECTURE.md)** | The target architecture: arbiter, per-group authority, robot adapter, hardware ladder, controller-swap, perception split |
| **[docs/STACK.md](docs/STACK.md)** | Full technology stack across all layers, present and planned |
| **[docs/HTTPS.md](docs/HTTPS.md)** | Pico HTTPS: Tailscale Serve vs self-signed |
| **[docs/BRINGUP.md](docs/BRINGUP.md)** | Milestone 1 bench checklist (Boomy + Pico) |
| **[docs/TODO.md](docs/TODO.md)** | Concrete milestone plan with realistic timelines and fleet-compliance gaps |

---

## Quick start

```powershell
git clone https://github.com/sandraschi/teleoperator-mcp
cd teleoperator-mcp
just bootstrap
just serve    # backend :10901
just web      # webapp  :10900
```

Open `https://<goliath>:10900` on the Pico browser, then **Enter VR**. WebXR without a headset: open the webapp in Chrome with the [WebXR Emulator](https://github.com/MozillaReality/WebXREmulatorExtension) extension.

---

## Stack (v0.1)

| Layer | Technology | Port | Role |
|-------|------------|------|------|
| **Webapp** | Vite + TypeScript + Three.js WebXR | 10900 | Pico client: pose capture, in-headset HUD, video plane |
| **Backend** | FastAPI + FastMCP 3.2 + WebSocket | 10901 | Pose ingress, mapping, watchdog, MCP tools |
| **Robot driver** | [yahboom-mcp](https://github.com/sandraschi/yahboom-mcp) REST | 10892 | `/cmd_vel`, PTZ servos |
| **Video (v1.5)** | [myconf](https://github.com/sandraschi/myconf) LiveKit | 15580 | Robot camera -> headset |

Full stack including the planned arbiter, VLA producers, perception, and hardware: **[docs/STACK.md](docs/STACK.md)**.

```
+------------- Pico 4 Browser -------------+
|  webapp (10900 HTTPS)                    |
|    2D landing -> Enter VR                |
|    WebXR: pose @ 30Hz --wss--+           |
|    chin HUD (non-blocking)   |           |
|    video plane (v1.5 LiveKit)|           |
+------------------------------|-----------+
                               v
+------------- Goliath --------------------+
|  teleoperator-mcp (10901)                |
|    WS /ws/teleop -> mappers/boomy        |
|    MCP /mcp -> teleop_status, configure  |
+------------------------------|-----------+
                               v
+------------- Boomy Pi -------------------+
|  yahboom-mcp -> rosbridge -> /cmd_vel    |
+------------------------------------------+
```

---

## MCP tools

| Tool | Status | Description |
|------|--------|-------------|
| `teleop_status` | shipped | Active session, frame count, robot target, watchdog config |
| `teleop_configure` | shipped (see known bug) | Runtime gains (`max_linear`, `pan_gain`, `yahboom_api_url`, ...) |
| `teleop_estop` | shipped | Hard stop, all actuator groups (operator/agent veto) |
| `teleop_set_mode` | planned | DIRECT or AUTO per actuator group (SHARED deferred) |
| `teleop_task_dispatch` | planned | Hand a language goal to the active manipulation policy |
| `teleop_takeover` | planned | Human reclaims authority immediately |

---

## Environment

| Variable | Default |
|----------|---------|
| `TELEOP_YAHBOOM_API_URL` | `http://127.0.0.1:10892` |
| `TELEOP_WATCHDOG_MS` | `300` |
| `TELEOP_MAX_LINEAR` | `0.3` |
| `TELEOP_MAX_ANGULAR` | `0.8` |
| `TELEOP_PAN_GAIN` | `60` |
| `TELEOP_TILT_GAIN` | `45` |
| `TELEOP_CORS_ORIGINS` | localhost dev URLs (comma-separated) |

Full list: [docs/PRD.md](docs/PRD.md) §13.

---

## Safety

- **Deadman:** drive only while the right trigger is held (> 0.5)
- **Squeeze (either hand):** client estop; drive frames suppressed while held
- **MCP `teleop_estop`:** hard stop from Cursor/agents
- **Watchdog:** no pose/heartbeat for `TELEOP_WATCHDOG_MS` (300 ms) -> latched e-stop until frames resume
- **Single session:** one active WebSocket at a time (second rejected with 4003)
- **Planned:** per-group takeover via arbiter (squeeze redefined in M3). See [docs/TODO.md](docs/TODO.md).

---

## Current status

Honest state, not aspiration:

- **Working:** FastAPI + FastMCP + WebSocket gateway, `BoomyMapper` (head -> PTZ, stick -> drive), single-session WS handler with latched watchdog and e-stop-on-disconnect, WebXR client (pose loop, squeeze estop, WS reconnect, throttled chin HUD), MCP tools (`teleop_status`, `teleop_configure`, `teleop_estop`).
- **Unverified on hardware:** the yahboom REST contract, Pico Browser WebXR feature matrix, end-to-end latency.
- **Not built:** the arbiter, per-group authority, robot adapter, autonomy producers, LeRobot logging. These are the [DUAL_MODE_ARCHITECTURE](docs/DUAL_MODE_ARCHITECTURE.md) target.

---

## Roadmap (summary)

| Phase | Scope | Gated by |
|-------|-------|----------|
| **v0.1** | WebXR pose -> Boomy drive + PTZ, chin HUD, MCP status + estop | M0 done; M1 hardware next |
| **v0.3** | Robot adapter + capability descriptor; mapper becomes a producer | none |
| **v0.4** | Arbiter (hard per-group switching, takeover, estop) + nav-stub AUTO producer | none |
| **v0.5** | LeRobot episode logging (the data flywheel) | none |
| **v1.5** | LiveKit video return (flat mono) | myconf |
| **v2** | Wheeled dual-arm rung: VLA producer, gripper manipulation, "open fridge, get can" | R1-A5-D hardware |

Full plan with timelines: **[docs/TODO.md](docs/TODO.md)**.

---

## Development

```powershell
just lint
just test
just dev     # backend reload
```

---

## License

MIT
