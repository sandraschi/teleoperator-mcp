# Video return with LiveKit (M5)

**Audience:** you on Goliath bringing up teleop, or future-you debugging “why is the headset black?”

**Related:** [BRINGUP.md](BRINGUP.md) (full lab checklist), [HTTPS.md](HTTPS.md) (headset URL), [GLOSSARY.md](GLOSSARY.md) (SFU, WebRTC), fleet [LiveKit integration guide](https://github.com/sandraschi/mcp-central-docs/blob/main/integrations/livekit/LIVEKIT_INTEGRATION_GUIDE.md), myconf `livekit.yaml`.

---

## TL;DR

Teleop uses **two separate network pipes**:

| Pipe | What moves | Protocol | Port |
|------|------------|----------|------|
| **Control** | Head + controller → drive + PTZ | WebSocket | **10901** (`/ws/teleop`) |
| **Video** | Boomy camera → your eyes | WebRTC (LiveKit) | **15580** (myconf SFU) |

They are **independent**. You can drive without video (gray plane). You can publish video without an active VR session. If one breaks, check the other first.

**Minimum to see robot video in VR:**

1. myconf LiveKit running on Goliath (`:15580`)
2. yahboom camera streaming (`http://127.0.0.1:10892/stream` or snapshot)
3. teleoperator **publisher** started (`scripts/start-livekit-publisher.ps1`)
4. Headset can reach LiveKit WebSocket (`TELEOP_LIVEKIT_PUBLIC_URL` on Tailscale)
5. Enter VR — chin HUD shows **`VID`** when the track is live

---

## Mental model (60 seconds)

```
  [ Pico browser ]                    [ Goliath PC ]                    [ Boomy Pi ]
        |                                   |                                |
        |  WSS pose 30 Hz                   |                                |
        +------------------------------->  teleoperator :10901              |
        |                                   |  REST move/PTZ                 |
        |                                   +------------------------------> yahboom :10892
        |                                   |                                |
        |  WebRTC video (LiveKit)           |  MJPEG pull                    |
        +<===============================>  publisher ----GET /stream------+
        |         myconf :15580           |                                |
```

**Why Goliath sits in the middle for video:** the Pi has no good hardware H.264 encoder. Goliath pulls JPEG frames from yahboom-mcp, converts them, and **publishes** one video track into a LiveKit room. The headset **subscribes** to that track. LiveKit (SFU) handles fan-out and WebRTC negotiation.

**Terms in one line:**

- **SFU** — LiveKit server; relays video between publisher and viewers.
- **Room** — named session (`teleop-boomy`); publisher and headset must use the same name.
- **Token** — short-lived JWT; proves you may join a room (subscribe for headset, publish for Goliath).
- **Publisher** — our Python task on Goliath that reads camera frames and feeds LiveKit.
- **MJPEG** — a long HTTP response of JPEG images; yahboom `/stream`.

---

## What runs where

| Process | Machine | Starts how |
|---------|---------|------------|
| yahboom-mcp | Goliath (talks to Pi) | `just serve` in yahboom-mcp |
| teleoperator backend | Goliath | `scripts/restart-backend.ps1` |
| teleoperator webapp | Goliath | `just web` or m1-up |
| **LiveKit SFU** | Goliath (Docker) | `docker compose up -d livekit` in **myconf** |
| **LiveKit publisher** | Goliath (inside teleoperator) | `scripts/start-livekit-publisher.ps1` or MCP `teleop_livekit_publisher_start` |
| WebXR + video client | Pico / Quest browser | User taps **Enter VR** |

Code locations:

- Publisher: `src/teleoperator_mcp/livekit/publisher.py`
- Tokens: `src/teleoperator_mcp/livekit/tokens.py`
- Webapp subscribe: `webapp/src/livekit-video.ts`

---

## First-time setup checklist

Work top to bottom. Stop when a step fails and use [Troubleshooting](#troubleshooting).

### Step 1 — LiveKit server

```powershell
Set-Location D:\Dev\repos\myconf
docker compose up -d livekit
```

**Expect:** container healthy; port **15580** listening on Goliath.

**Keys must match:** myconf `livekit.yaml` uses `devkey` / `secret` by default — same as teleoperator `.env`.

### Step 2 — Camera on Boomy

Open in a desktop browser on Goliath:

`http://127.0.0.1:10892/stream`

**Expect:** moving MJPEG, or fix camera first (yahboom-mcp STATUS.md — `/dev/video0` contention is common).

**Fallback:** publisher can poll `/api/v1/snapshot` if MJPEG fails (`TELEOP_LIVEKIT_SNAPSHOT_FALLBACK=1`).

### Step 3 — teleoperator `.env`

Copy `.env.example` → `.env`. Minimum for video:

```env
TELEOP_LIVEKIT_ENABLED=1
TELEOP_LIVEKIT_URL=ws://127.0.0.1:15580
TELEOP_LIVEKIT_API_KEY=devkey
TELEOP_LIVEKIT_API_SECRET=secret
TELEOP_LIVEKIT_ROOM=teleop-boomy
```

For **Pico on Tailscale**, add (replace with your hostname):

```env
TELEOP_LIVEKIT_PUBLIC_URL=wss://goliath.tailfab45.ts.net:15580
```

Publisher uses `LIVEKIT_URL` (localhost). Browser uses `PUBLIC_URL` (Tailscale). **Do not** point the publisher at a URL the Pi cannot reach via loopback.

Restart backend after editing `.env`.

### Step 4 — Start publisher

```powershell
Set-Location D:\Dev\repos\teleoperator-mcp
.\scripts\start-livekit-publisher.ps1
```

**Expect JSON:**

- `success: true`
- `connected: true`
- `frames_published` increasing over a few seconds

Manual check:

```powershell
Invoke-RestMethod http://127.0.0.1:10901/api/v1/livekit/status
```

### Step 5 — VR or desktop test

1. Open `https://goliath.<tailnet>.ts.net/`
2. **Enter VR** (or use desktop WebXR if available)
3. Chin HUD: `vid--` → **`VID`** when video connected
4. Center view: robot camera (not solid gray)

---

## Configuration reference

| Variable | Default | Plain English |
|----------|---------|---------------|
| `TELEOP_LIVEKIT_ENABLED` | `1` | Off = no token API, webapp skips LiveKit |
| `TELEOP_LIVEKIT_URL` | `ws://127.0.0.1:15580` | Where **publisher** connects (always Goliath-local) |
| `TELEOP_LIVEKIT_PUBLIC_URL` | *(empty)* | Where **headset browser** connects; set for Tailscale |
| `TELEOP_LIVEKIT_API_KEY` / `SECRET` | `devkey` / `secret` | Must match myconf LiveKit |
| `TELEOP_LIVEKIT_ROOM` | `teleop-boomy` | Room name; publisher + viewers must agree |
| `TELEOP_LIVEKIT_PUBLISHER_FPS` | `15` | Target frames/sec (lower = less CPU/bandwidth) |
| `TELEOP_LIVEKIT_FRAME_WIDTH` / `HEIGHT` | `640` / `480` | Resize before publish |
| `TELEOP_LIVEKIT_MJPEG_URL` | *(empty)* | Override camera URL; default `{YAHBOOM}/stream` |
| `TELEOP_LIVEKIT_SNAPSHOT_FALLBACK` | `1` | If MJPEG dies, poll JPEG snapshots |
| `TELEOP_LIVEKIT_AUTO_START_PUBLISHER` | `0` | Start publisher when backend boots |

---

## Daily ops (normal session)

```powershell
# 1. Stack already up from m1-up or manual terminals
# 2. Start video publisher (once per session)
.\scripts\start-livekit-publisher.ps1

# 3. Optional: watch stats
Invoke-RestMethod http://127.0.0.1:10901/api/v1/livekit/status

# 4. Headset: open HTTPS URL, Enter VR

# 5. When done
Invoke-RestMethod -Method Post http://127.0.0.1:10901/api/v1/livekit/publisher/stop
```

From Cursor MCP: `teleop_livekit_status`, `teleop_livekit_publisher_start`, `teleop_livekit_publisher_stop`.

---

## Troubleshooting

Read the symptom, not the stack trace first.

### “Publisher won't start / connected: false”

1. Is LiveKit up? `docker ps` in myconf
2. Do keys match `.env` vs `livekit.yaml`?
3. Run `uv sync` in teleoperator-mcp (needs `livekit` Python packages)
4. Read `last_error` in `/api/v1/livekit/status`

### “frames_published stays 0”

1. Open `http://127.0.0.1:10892/stream` — any image?
2. Kill host `raspbot` on Pi if it holds `/dev/video0` (yahboom docs)
3. Try snapshot: `Invoke-RestMethod http://127.0.0.1:10892/api/v1/snapshot -OutFile test.jpg`
4. Enable snapshot fallback if MJPEG is flaky

### “Drive works, video is gray / vid--”

Control pipe is fine; video pipe is broken.

1. Confirm publisher running and `frames_published` > 0
2. **`TELEOP_LIVEKIT_PUBLIC_URL`** set for headset? Browser devtools not available on Pico — test token URL from desktop first
3. WebRTC UDP **50000–60000** open Goliath ↔ headset; enable TURN in myconf `livekit.yaml` if needed
4. Same room name everywhere (`teleop-boomy`)

### “Video works on desktop, not on Pico”

Almost always **network**: Tailscale WSS URL, UDP, or firewall. Pico must reach `:15580` on Goliath hostname, not `127.0.0.1`.

### “Video laggy / nauseating with head PTZ”

Expected until tuned. Mitigations:

- Lower `TELEOP_LIVEKIT_PUBLISHER_FPS` or resolution
- Measure motion-to-photon (BRINGUP §6)
- Future: decouple head PTZ from video frame (TODO M5 acceptance)

---

## HTTP API (quick reference)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/livekit/config` | Safe public config for webapp (url, room, enabled) |
| POST | `/api/v1/livekit/token` | Body: `{"identity":"viewer-1","room":"teleop-boomy"}` → subscribe JWT |
| GET | `/api/v1/livekit/status` | Publisher health + frame count |
| POST | `/api/v1/livekit/publisher/start` | Start MJPEG → LiveKit |
| POST | `/api/v1/livekit/publisher/stop` | Stop publisher |

Health aggregate: `GET /api/v1/health` includes `livekit` block.

---

## WebXR client behavior

On **Enter VR**:

1. `GET /api/v1/livekit/config`
2. `POST /api/v1/livekit/token` with generated viewer identity
3. `livekit-client` connects and subscribes
4. First remote **video** track → `THREE.VideoTexture` on 1.6 m × 0.9 m plane (center FOV)
5. HUD prefix **`VID`** when track is playing

Pose WebSocket is unchanged — see [WEBXR.md](WEBXR.md).

---

## Recording (M4) and video

Session JSONL ([LEROBOT.md](LEROBOT.md)) logs pose and commands today, **not** video files. Parquet + synced video is a follow-on once M5 is stable (LiveKit egress or frame timestamps).

---

## Acceptance criteria (M5)

- [ ] Publisher runs 60 s with steady `frames_published` on bench
- [ ] VR session shows live camera (`VID` in HUD)
- [ ] Tailscale path documented with your real hostname
- [ ] Motion-to-photon latency noted in BRINGUP.md

---

## Further reading

- myconf: `docs/LIVEKIT.md`, port **15580**
- Fleet: `mcp-central-docs/integrations/livekit/`
- Architecture context: [PRD.md §6](PRD.md), [STACK.md §3](STACK.md)
