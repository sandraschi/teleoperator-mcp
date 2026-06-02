# Teleoperator MCP — Product Requirements (v0.1)

**Status:** Draft · **Target:** Boomy (Yahboom Raspbot v2) first · **Platform:** Pico 4 browser (WebXR)

**Long arc:** Direct teleop is v0.1. The telesupervision target (arbiter, per-group authority, VLA producers, hardware ladder) is in **[DUAL_MODE_ARCHITECTURE.md](DUAL_MODE_ARCHITECTURE.md)**. Milestones: **[TODO.md](TODO.md)**.

## 1. Problem

Operators need to drive fleet robots from a VR headset with low enough latency for slow telepresence, without rebuilding control plumbing per robot. The fleet already has robot drivers (`yahboom-mcp`), video paths (`VideoBridge`, LiveKit/myconf), and MCP standards — but no VR pose ingress layer.

## 2. Solution summary

**teleoperator-mcp** is a thin gateway with two surfaces:

| Surface | Role | Latency class |
|---------|------|---------------|
| **Webapp (WebXR)** | Runs **on the Pico**. Captures head + controller pose, renders in-headset HUD, displays return video. | Real-time (~30 Hz pose) |
| **MCP server** | Session config, status, gains, agent tooling. **Not** on the pose hot path. | Cold path (seconds) |
| **WebSocket API** | Pose ingress from headset → mapper → robot REST. | Hot path (~30 Hz) |

The webapp is **not** a separate “admin dashboard” — it **is** the VR client. A minimal 2D landing page exists only to pick robot target and tap **Enter VR** before the immersive session starts.

## 3. Does this need both MCP and webapp?

**Yes — different jobs.**

### MCP server (required for fleet)

- `teleop_status` — is a session active, frame count, client IP, robot target
- `teleop_configure` — mapping gains, watchdog timeout, downstream API URL
- Future: `teleop_session_start/stop`, humbot mapper profiles, LiveKit room provisioning
- Agents and Cursor use MCP; the Pico never speaks MCP

### Webapp (required for Pico)

- **Pre-VR shell** (2D): connect URL, robot selector, HTTPS hint, latency ping
- **Immersive WebXR session**: pose loop, WebSocket client, video plane, **in-XR HUD**
- Served over **HTTPS** (WebXR requirement) from port **10900**, proxied to backend **10901**

**Do not** route 30 Hz pose through MCP tool calls — wrong transport, wrong latency.

## 4. In-headset HUD (non-obstructing)

The HUD lives **inside WebXR**, not as a desktop overlay blocking the robot view.

### v1 layout

```
┌─────────────────────────────────────────┐
│                                         │
│         [ robot camera video ]          │  ← full FOV background (v1.5 LiveKit)
│                                         │
│                                         │
├─────────────────────────────────────────┤
│ ● WS  32ms   ▓▓▓▓ drive   PTZ 42°/−8°  │  ← chin strip (~8% height, bottom)
└─────────────────────────────────────────┘
```

- **Chin strip**: fixed in head space, translated **−0.35 m on Y**, **−0.5 m on Z** (below natural gaze). Semi-transparent dark panel (`opacity ~0.65`).
- **Content**: connection dot, RTT, deadman indicator, optional mini stick visualization — **no text larger than necessary**.
- **Center FOV**: reserved for robot video only (v1 can be empty black until LiveKit slice lands).
- **Wrist panel (v2)**: optional small stats on non-dominant controller — only when user looks at wrist.

### Implementation

- Three.js + WebXR: `Group` parented to `camera` with local offset for chin HUD
- Alternative: `XRDOMOverlay` where Pico supports it — fallback to WebGL quads
- Desktop dev: same page without VR shows 2D debug HUD

## 5. v1 scope (Boomy)

| In scope | Out of scope |
|----------|--------------|
| WebXR pose stream → WebSocket → Boomy drive + PTZ | Stereo video |
| Deadman (trigger) + watchdog e-stop | Humbot arms |
| MCP status + configure tools | WALL-OSS / autonomous missions |
| Chin HUD (connection, RTT, drive state) | Native Pico SDK app |
| yahboom-mcp REST integration | Custom robot firmware |

## 6. v1.5 — video return

- Goliath publishes Boomy `VideoBridge` frames to **myconf LiveKit** room `teleop-boomy`
- WebXR client subscribes, maps track to a large plane in front of user (flat mono, not stereo)
- Reuse myconf token endpoint pattern; document in `docs/LIVEKIT.md`

## 7. v2 — immersion

- Stereo camera or dual-stream compositing
- Left stick strafe (mecanum `linear_y`)
- Wrist HUD, haptic pulse on watchdog trip

## 8. v3 — Wheeled dual-arm (R1-A5-D)

- Separate mapper module; gripper manipulation via VLA producer (see DUAL_MODE_ARCHITECTURE.md)
- Same WebSocket schema, `robot=r1a5d` route param
- Acceptance task: open fridge, retrieve can (Milestone 6 in TODO.md)

## 9. Architecture

```
Pico 4 Browser
  webapp (10900 HTTPS)
    ├─ 2D landing
    └─ WebXR session
         ├─ pose-stream.ts ──wss──► /ws/teleop (10901)
         └─ hud.ts (chin strip in XR space)

Goliath teleoperator-mcp (10901)
  ├─ WebSocket handler + watchdog
  ├─ mappers/boomy.py
  ├─ FastMCP /mcp (status, configure)
  └─ REST /api/v1/health

yahboom-mcp (10892)
  ├─ POST /api/v1/control/move
  └─ POST /api/v1/control/tool (camera_set_pos)

Boomy Pi → rosbridge → /cmd_vel, servos
```

## 10. Pose message schema (v1)

```json
{
  "v": 1,
  "t": 1717334400123,
  "seq": 42,
  "head": { "yaw": 0.12, "pitch": -0.05, "roll": 0.01 },
  "right": {
    "connected": true,
    "axes": [0.0, -0.8],
    "buttons": { "trigger": 1.0, "squeeze": 0.0 }
  },
  "left": { "connected": true, "axes": [], "buttons": {} }
}
```

Heartbeat: `{"v":1,"type":"heartbeat","t":...}` every 500 ms.

## 11. Safety

- **Deadman**: drive only while right trigger > 0.5
- **Squeeze (either controller)**: client sends `estop`; server zeros drive (v0.1 local stop; v0.4 becomes takeover)
- **MCP `teleop_estop`**: agent/operator hard stop
- **Watchdog**: no frame/heartbeat for `TELEOP_WATCHDOG_MS` (default 300) → e-stop (latched until frames resume)
- **Single session**: second WebSocket rejected with 4003
- **Disconnect**: e-stop on WS close

## 12. Ports (fleet)

| Port | Service |
|------|---------|
| 10900 | Webapp (Vite dev / static build) |
| 10901 | Backend (FastAPI + MCP HTTP + WebSocket) |

Register in `mcp-central-docs/operations/WEBAPP_PORTS.md` (done: 10900/10901).

## 13. Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `TELEOP_PORT` | 10901 | Backend listen |
| `TELEOP_YAHBOOM_API_URL` | `http://127.0.0.1:10892` | Robot driver |
| `TELEOP_WATCHDOG_MS` | 300 | E-stop timeout |
| `TELEOP_MAX_LINEAR` | 0.3 | m/s cap |
| `TELEOP_MAX_ANGULAR` | 0.8 | rad/s cap |
| `TELEOP_PAN_GAIN` | 60 | head yaw → pan ° |
| `TELEOP_TILT_GAIN` | 45 | head pitch → tilt ° |
| `TELEOP_CORS_ORIGINS` | localhost dev URLs | Comma-separated HTTPS origins for Pico/Tailscale |

## 14. Success criteria (v1)

1. WebXR emulator sends pose; server logs frames and responds `{ok:true}`
2. Boomy drives with trigger + right stick; head moves PTZ
3. WS disconnect or watchdog stops robot within 300 ms
4. Chin HUD visible in VR without covering center 70% of FOV
5. MCP `teleop_status` reflects live session from Cursor

## 15. Open items

- [ ] HTTPS cert strategy (Tailscale Serve vs self-signed)
- [ ] Confirm yahboom `camera_set_pos` REST path matches deployed API
- [ ] LiveKit publisher sidecar (v1.5)
- [ ] Pico Browser WebXR feature matrix test on hardware
