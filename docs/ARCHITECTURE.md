# Architecture overview

Short map of how teleoperator-mcp fits together. For milestone detail see [TODO.md](TODO.md); for dual-mode autonomy see [DUAL_MODE_ARCHITECTURE.md](DUAL_MODE_ARCHITECTURE.md).

---

## Two pipes (control vs video)

Teleop is **not** one protocol. Treat control and video as separate systems that happen to run in the same VR session.

```
                    CONTROL (hot, ~30 Hz)              VIDEO (warm, ~15 FPS)
                    ---------------------              -----------------------

  Headset           WebSocket JSON pose                WebRTC via LiveKit
       |            /ws/teleop?robot=boomy                   |
       v            port 10901                               v
  Goliath           teleoperator-mcp                         teleconference-mcp SFU
       |            arbiter + adapter                         port 15580
       |            |                                         ^
       v            v                                         |
  Boomy Pi          yahboom-mcp REST              publisher pulls MJPEG
                    move + camera_set_pos          from yahboom /stream
```

| If this works | But this fails | Look at |
|---------------|----------------|---------|
| Drive + PTZ | Gray screen / `vid--` | [LIVEKIT.md](LIVEKIT.md) — publisher, PUBLIC_URL, UDP |
| Video `VID` | No movement | WebSocket, yahboom, deadman trigger |
| Neither | | Goliath stack, Tailscale HTTPS, health endpoints |

---

## Goliath process map

| Port | Service | Role |
|------|---------|------|
| 10900 | Vite webapp | WebXR UI, proxies `/api` and `/ws` to 10901 |
| 10901 | teleoperator-mcp | WS teleop, MCP, REST, LiveKit token + publisher control |
| 10892 | yahboom-mcp | Robot driver (from Goliath, targets Boomy Pi) |
| 15580 | teleconference-mcp LiveKit | Video SFU (Docker) |
| 10909 | speech-mcp | Spoken AUTO/watchdog warnings (optional) |

Headset URL: Tailscale Serve → **10900** only. LiveKit is a **second** connection to **15580** (see LIVEKIT.md).

---

## Software layers (inside teleoperator-mcp)

```
server.py          FastAPI + MCP tools + REST
auth.py            Operator claim/token registry (WS gate; estop open)
tasks.py           Language goal -> AUTO waypoint plan
voice_commands.py  STT transcript -> domain action keyword parser
ws/handler.py      WebSocket session, watchdog, presence deadman, recording hooks
runtime.py         bind_robot(?robot=), arbiter + VLA + waypoint singletons
adapters/          BoomyAdapter → yahboom REST (+ bumi, vboomy)
arbiter/           DIRECT / AUTO / SHARED per group (base, gaze, manip)
producers/         human_pose, nav_stub, waypoint (AUTO), fake_vla (test stand-in)
livekit/           MJPEG → LiveKit publisher, JWT tokens, egress feed
recording/         LeRobot JSONL episodes + egress frame sink + parquet export
```

**Rule:** pose never goes through MCP tool calls. MCP is seconds-scale supervision; WebSocket is the hot path.

---

## Data logged (M4 + egress)

Each VR session can write JSONL under `data/teleop_recordings/`. See [LEROBOT.md](LEROBOT.md) — pose, resolved commands, authority state, and (via the egress sink) synced video frames under `images/observation.image/`. Parquet export carries `observation.image.image` into the chunked dataset.

---

## Doc index by task

| I want to… | Read |
|------------|------|
| First hardware session | [BRINGUP.md](BRINGUP.md) |
| Fix black video | [LIVEKIT.md](LIVEKIT.md) |
| Pico + Tailscale | [TAILSCALE_VIEWERS.md](TAILSCALE_VIEWERS.md) |
| HTTPS on Goliath | [HTTPS.md](HTTPS.md) |
| Terms (VLA, arbiter, LeRobot) | [GLOSSARY.md](GLOSSARY.md) |
| Full stack table | [STACK.md](STACK.md) |
