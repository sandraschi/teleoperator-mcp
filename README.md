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

Two surfaces, two latency classes, one gateway:

| Surface | Role | Latency |
|---------|------|---------|
| **Webapp (WebXR)** | VR client on Pico / Meta — pose, HUD, video | ~30 Hz WebSocket |
| **MCP server** | Supervisor tools — status, configure, estop, (future) mode switch | seconds |
| **Robot adapter** | Maps standard commands to yahboom-mcp REST (Boomy today) | same hot path |

Pose **never** traverses MCP tool calls. The webapp **is** the VR client, not a separate admin dashboard.

Target architecture (arbiter, per-group authority, LeRobot logging, VLA producers): **[docs/DUAL_MODE_ARCHITECTURE.md](docs/DUAL_MODE_ARCHITECTURE.md)**.

---

## Documentation

| Doc | Contents |
|-----|----------|
| [docs/GLOSSARY.md](docs/GLOSSARY.md) | **LeRobot, VLA, arbiter, WebXR**, fleet terms |
| [docs/PRD.md](docs/PRD.md) | v1 product spec |
| [docs/WEBXR.md](docs/WEBXR.md) | In-repo VR client (no Pico SDK) |
| [docs/TAILSCALE_VIEWERS.md](docs/TAILSCALE_VIEWERS.md) | **Pico / Meta + Tailscale** — setup and pitfalls |
| [docs/HTTPS.md](docs/HTTPS.md) | Tailscale Serve on Goliath |
| [docs/BRINGUP.md](docs/BRINGUP.md) | Milestone 1 hardware checklist |
| [docs/STACK.md](docs/STACK.md) | Full technology stack |
| [docs/TODO.md](docs/TODO.md) | Milestone plan |

---

## Quick start

```powershell
git clone https://github.com/sandraschi/teleoperator-mcp
cd teleoperator-mcp
just bootstrap
.\scripts\m1-up.ps1   # backend + webapp + Tailscale Serve
```

Headset URL: `https://goliath.<your-tailnet>.ts.net/` → **Enter VR**.

---

## Stack (v0.2)

| Layer | Technology | Port |
|-------|------------|------|
| Webapp | Vite + Three.js WebXR | 10900 |
| Backend | FastAPI + FastMCP + WebSocket | 10901 |
| Adapter | `BoomyAdapter` → [yahboom-mcp](https://github.com/sandraschi/yahboom-mcp) | 10892 |
| Video (planned) | [myconf](https://github.com/sandraschi/myconf) LiveKit | 15580 |

```
  Pico / Meta Quest (Tailscale + Browser)
           |  HTTPS / WSS
           v
  Goliath: teleoperator-mcp (adapter + producer + MCP)
           |
           v
  Boomy Pi: yahboom-mcp -> /cmd_vel, PTZ
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
| `teleop_task_dispatch` | planned |

---

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
| M4 | [LeRobot](docs/GLOSSARY.md#autonomy-and-learning-future-phases) episode logging | planned |
| v1.5 | LiveKit video return | planned |

---

## Development

```powershell
just lint
just test
just serve
just web
```

---

## License

MIT
