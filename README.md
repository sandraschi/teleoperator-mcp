# Teleoperator MCP

WebXR teleoperation gateway for the MCP fleet: stream VR pose from **Pico 4** or **Meta Quest** to Goliath, drive fleet robots (Boomy first), and evolve toward **dual-mode telesupervision** (human teleop ↔ autonomous policy with human veto). Video return via LiveKit (v1.5).

<p align="center">
  <a href="https://github.com/sandraschi/teleoperator-mcp/actions"><img src="https://img.shields.io/badge/CI-GitHub_Actions-2088FF?style=flat-square&logo=githubactions&logoColor=white" alt="CI"></a>
  <a href="https://github.com/jlowin/fastmcp"><img src="https://img.shields.io/badge/FastMCP-3.2-7c5cfc?style=flat-square" alt="FastMCP 3.2"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.12+"></a>
  <a href="https://vitejs.dev/"><img src="https://img.shields.io/badge/Vite-6-646CFF?style=flat-square&logo=vite&logoColor=white" alt="Vite 6"></a>
  <a href="https://threejs.org/"><img src="https://img.shields.io/badge/Three.js-WebXR-000000?style=flat-square&logo=three.js&logoColor=white" alt="Three.js WebXR"></a>
  <a href="https://tailscale.com/"><img src="https://img.shields.io/badge/Tailscale-Serve-242424?style=flat-square&logo=tailscale&logoColor=white" alt="Tailscale Serve"></a>
  <img src="https://img.shields.io/badge/status-alpha-f59e0b?style=flat-square" alt="status alpha">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue?style=flat-square" alt="MIT License"></a>
</p>

**New here?** Read the **[glossary](docs/GLOSSARY.md)** for LeRobot, VLA, arbiter, and other terms used in the docs.

---

## What this is

Two surfaces, two latency classes, one gateway — plus a **separate video pipe** (LiveKit):

| Surface | Role | Latency |
|---------|------|---------|
| **Webapp (WebXR)** | VR client on Pico / Meta — pose, HUD, video | ~30 Hz WebSocket + ~15 FPS WebRTC |
| **MCP server** | Supervisor tools — status, configure, estop, mode, LiveKit publisher | seconds |
| **Robot adapter** | Maps standard commands to yahboom-mcp REST (Boomy today) | same hot path |

**Confused by ports?** Start with **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** (control vs video explained simply).

Pose **never** traverses MCP tool calls. The webapp **is** the VR client, not a separate admin dashboard.

Target architecture (arbiter, per-group authority, LeRobot logging, VLA producers): **[docs/DUAL_MODE_ARCHITECTURE.md](docs/DUAL_MODE_ARCHITECTURE.md)**.

---

## Documentation

| Doc | Contents |
|-----|----------|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | **Two-pipe map** (control vs video), ports, module index |
| [docs/GLOSSARY.md](docs/GLOSSARY.md) | **LeRobot, VLA, arbiter, WebXR**, fleet terms |
| [docs/CONFIGURATION.md](docs/CONFIGURATION.md) | Environment variables, ports, CORS, LiveKit |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Layout, gates, conventions, contributing |
| [docs/TOOLS.md](docs/TOOLS.md) | MCP tools + REST endpoint reference |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Symptom-first fix guide |
| [docs/LIVEKIT.md](docs/LIVEKIT.md) | **Video return** — setup, env vars, troubleshooting |
| [docs/LEROBOT.md](docs/LEROBOT.md) | Session recording (JSONL episodes) |
| [docs/PRD.md](docs/PRD.md) | v1 product spec |
| [docs/WEBXR.md](docs/WEBXR.md) | In-repo VR client (no Pico SDK) |
| [docs/TAILSCALE_VIEWERS.md](docs/TAILSCALE_VIEWERS.md) | **Pico / Meta + Tailscale** — setup and pitfalls |
| [docs/HTTPS.md](docs/HTTPS.md) | Tailscale Serve on Goliath |
| [docs/BRINGUP.md](docs/BRINGUP.md) | Milestone 1 hardware checklist |
| [docs/STACK.md](docs/STACK.md) | Full technology stack |
| [docs/TODO.md](docs/TODO.md) | Milestone plan |
| [docs/ONBOARDING.md](docs/ONBOARDING.md) | First-timer setup, pitfalls, sanity check |
| [INSTALL.md](INSTALL.md) | Install and run the stack |
| [CHANGELOG.md](CHANGELOG.md) | Release notes |

---

## Quick start

```powershell
git clone https://github.com/sandraschi/teleoperator-mcp
cd teleoperator-mcp
just bootstrap
.\webapp\start.bat -WithTailscaleServe    # fleet standard (backend + Vite + Serve)
# or Pico M1 helper (detached windows):
.\scripts\m1-up.ps1
```

Headset URL: `https://goliath.<your-tailnet>.ts.net/` → **Enter VR**.

---

## Stack (v0.2)

| Layer | Technology | Port |
|-------|------------|------|
| Webapp | Vite 6 + React (Iron Shell) + Three.js WebXR | 10900 |
| Backend | FastAPI + FastMCP + WebSocket | 10901 |
| Adapter | `BoomyAdapter` → [yahboom-mcp](https://github.com/sandraschi/yahboom-mcp) | 10892 |
| Video | [teleconference-mcp](https://github.com/sandraschi/teleconference-mcp) LiveKit + Goliath publisher | 15580 |

```
  Pico / Meta Quest (Tailscale + Browser)
     |  HTTPS/WSS pose (:10900 → :10901)
     |  WebRTC video (:15580 LiveKit)
     v
  Goliath: teleoperator-mcp + LiveKit publisher
     |
     v
  Boomy Pi: yahboom-mcp → /cmd_vel, PTZ, camera /stream
```

---

## MCP tools

| Tool | Status |
|------|--------|
| `teleop_status` | shipped |
| `teleop_configure` | shipped |
| `teleop_estop` | shipped |
| `teleop_set_mode` | shipped (M3) |
| `teleop_takeover` | shipped (M3) |
| `teleop_set_gaze` | shipped (PTZ bench / head-follow prep) |
| `teleop_gaze_center` | shipped |
| `teleop_livekit_status` | shipped (M5) |
| `teleop_livekit_publisher_start` / `_stop` | shipped (M5) |
| `show_teleop_status_card` | shipped (Prefab) |
| `teleop_voice_command` | shipped (speech-mcp STT control) |
| `teleop_shutdown` | shipped |

---

## Fleet integration

Teleoperator is the **VLA Fleet Control Tower** hub — the supervision surface that ties the
robotics fleet together (teleop, claims, episodes/curation, VLA producers). See
[`mcp-central-docs/patterns/VLA_FLEET_CONTROL_TOWER.md`](https://github.com/sandraschi/mcp-central-docs/blob/main/patterns/VLA_FLEET_CONTROL_TOWER.md).

- **Supervision**: `GET /api/v1/supervision` — every robot's claim + reachability (webapp `/ops`).
- **Episodes**: `GET /api/v1/episodes` + replay + curation (webapp `/episodes`).
- **Task dispatch**: `teleop_task_dispatch(goal)` — AUTO waypoint plans (VLA branch hardware-gated).
- **Voice**: `teleop_voice_command` over the fleet voice bus.
- **Data flywheel**: `scripts/publish-lerobot-hub.py` packs curated episodes for VLA fine-tuning.

## Tailscale on viewers

**No fundamental problem** — install Tailscale on Pico or Meta Quest, same tailnet as Goliath, open the `https://*.ts.net` URL. Headsets do not talk to Boomy's LAN IP; Goliath bridges via yahboom-mcp.

Details and troubleshooting: **[docs/TAILSCALE_VIEWERS.md](docs/TAILSCALE_VIEWERS.md)**.

---

## Roadmap

| Phase | Scope | Status |
|-------|-------|--------|
| v0.1 | WebXR pose, safety, MCP estop | done |
| M1 | Boomy + headset hardware bring-up | in progress |
| M2 | Robot adapter + `ProducerCommand` | **adapter layer shipped** |
| M3 | Arbiter + AUTO stub | **shipped** (headset squeeze test pending M1) |
| M4 | LeRobot JSONL session logging | **shipped** |
| M5 | LiveKit video return | **shipped** (headset + latency sign-off pending) |

---

## Development

```powershell
just lint            # ruff + tsc + biome
just types           # pyright
just test            # pytest (coverage gate >=50%)
just gates-green     # lint + types + test
just ci              # same gates as GitHub Actions (Windows)
just serve
just web
just mcpb-pack       # build .mcpb bundle (fresh-stages src/ -> mcpb/src)
just integration-test   # headless WS harness vs live stack (needs backend up)
# Webapp e2e (Playwright, reuses running stack when healthy):
Set-Location webapp; npx playwright test
```

---

## License

MIT
