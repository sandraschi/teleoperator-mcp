# Configuration

This document covers how to configure the Teleoperator MCP gateway: environment variables,
ports, CORS, LiveKit, robot adapters, and runtime tuning.

## Source of truth

All runtime settings are read from environment variables prefixed with `TELEOP_`, loaded by
`pydantic-settings` from a `.env` file at the repo root when present. The template is
`.env.example` — copy it to `.env` and edit:

```powershell
Copy-Item .env.example .env
```

`.env` is gitignored. Never commit real credentials; keep only template values in committed
files.

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| TELEOP_HOST | 0.0.0.0 | Backend bind address |
| TELEOP_PORT | 10901 | Backend port (REST + WebSocket + MCP HTTP) |
| TELEOP_YAHBOOM_API_URL | http://127.0.0.1:10892 | Boomy robot REST API base |
| TELEOP_CORS_ORIGINS | localhost:10900, tauri, ts.net | Allowed browser origins (comma-separated) |
| TELEOP_WATCHDOG_MS | 1000 | Watchdog interval; no frames within it latches drive |
| TELEOP_POSE_HZ_CAP | 30 | Max pose update rate |
| TELEOP_MAX_LINEAR | 0.3 | Max linear velocity m/s |
| TELEOP_MAX_ANGULAR | 0.8 | Max angular velocity rad/s |
| TELEOP_PAN_GAIN | 60.0 | Camera pan gain |
| TELEOP_TILT_GAIN | 45.0 | Camera tilt gain |
| TELEOP_PTZ_PAN_CENTER | 90.0 | Neutral pan (0-180 deg servo range) |
| TELEOP_PTZ_TILT_CENTER | 90.0 | Neutral tilt (0-180 deg servo range) |
| TELEOP_GAZE_EVERY_N_FRAMES | 1 | Head-follow update throttle |
| TELEOP_GAZE_MIN_DELTA_DEG | 1.0 | Head-follow minimum delta to send |
| TELEOP_DEFAULT_ROBOT | boomy | Default WebSocket robot |
| TELEOP_BUMI_API_URL | http://127.0.0.1:10774 | Bumi biped REST API |
| TELEOP_BUMI_MAX_LINEAR | 0.15 | Bumi linear cap m/s |
| TELEOP_BUMI_MAX_ANGULAR | 0.4 | Bumi angular cap rad/s |
| TELEOP_BUMI_HEAD_YAW_GAIN | 57.3 | Bumi head yaw gain |
| TELEOP_BUMI_HEAD_PITCH_GAIN | 45.0 | Bumi head pitch gain |
| TELEOP_ROBOTICS_API_URL | http://127.0.0.1:12230 | Robotics bridge API |
| TELEOP_VBOOMY_ROBOT_ID | vbot_yahboom_01 | Resonite virtual twin robot id |
| TELEOP_LIVEKIT_VBOOMY_ROOM | teleop-vboomy | vboomy LiveKit room |
| TELEOP_RECORDING_ENABLED | 1 | LeRobot JSONL recording |
| TELEOP_RECORDING_DIR | data/teleop_recordings | Recording directory |
| TELEOP_RECORDING_FPS | 30 | Recording frame rate |
| TELEOP_LIVEKIT_ENABLED | 1 | LiveKit video return |
| TELEOP_LIVEKIT_URL | ws://127.0.0.1:15580 | LiveKit server URL |
| TELEOP_LIVEKIT_PUBLIC_URL | (empty) | Headset WSS URL on Tailscale; empty uses LIVEKIT_URL |
| TELEOP_LIVEKIT_API_KEY | devkey | Must match SFU key |
| TELEOP_LIVEKIT_API_SECRET | secret | Must match SFU secret |
| TELEOP_LIVEKIT_ROOM | teleop-boomy | Default room name |
| TELEOP_LIVEKIT_PUBLISHER_IDENTITY | teleop-publisher | Publisher identity |
| TELEOP_LIVEKIT_PUBLISHER_FPS | 15 | Publisher frame rate |
| TELEOP_LIVEKIT_FRAME_WIDTH | 640 | Publisher frame width |
| TELEOP_LIVEKIT_FRAME_HEIGHT | 480 | Publisher frame height |
| TELEOP_LIVEKIT_MJPEG_URL | (empty) | MJPEG source; empty uses yahboom /stream |
| TELEOP_LIVEKIT_SNAPSHOT_FALLBACK | 1 | Poll snapshots if MJPEG fails |
| TELEOP_LIVEKIT_AUTO_START_PUBLISHER | 0 | Auto-start publisher at boot |
| TELEOP_AUTO_MAX_DURATION_S | 10.0 | AUTO mode max seconds |
| TELEOP_AUTO_WARN_BEFORE_S | 3.0 | AUTO cutoff warning lead time |
| TELEOP_AUTO_REQUIRE_WEBXR | 1 | WebXR required for AUTO |
| TELEOP_NAV_STUB_LINEAR | 0.15 | Nav stub linear speed |
| TELEOP_NAV_STUB_ANGULAR | 0.0 | Nav stub angular speed |
| TELEOP_SPEECH_ENABLED | 1 | Spoken warnings |
| TELEOP_SPEECH_MCP_URL | http://127.0.0.1:10909 | speech-mcp endpoint |
| TELEOP_SPEECH_PROVIDER | windows | Speech provider (SAPI fallback) |

## Ports

The gateway owns the 10900/10901 pair (frontend/backend). Downstream services:

| Port | Service |
|------|---------|
| 10900 | Vite webapp (WebXR client) |
| 10901 | teleoperator-mcp backend |
| 10892 | yahboom-mcp (Boomy) |
| 10774 | bumi-mcp (Bumi) |
| 10979 | resonite-mcp (vboomy OSC) |
| 10909 | speech-mcp |
| 15580 | LiveKit SFU |

## CORS

The backend allows the origins in `TELEOP_CORS_ORIGINS` plus an unconditional regex covering
`*.ts.net`, LAN IPs, `localhost`, `127.0.0.1`, and `tauri://localhost`. When launching via
`webapp/start.ps1 -WithTailscaleServe`, the launcher reads `tailscale serve status` and sets
`TELEOP_CORS_ORIGINS` to the tailnet HTTPS origin automatically.

## LiveKit

- The fleet SFU is the `LiveKitSFU` Windows service (NSSM) on port 15580, configured via
  teleconference-mcp's `livekit.yaml`.
- `TELEOP_LIVEKIT_API_KEY` and `TELEOP_LIVEKIT_API_SECRET` must match the SFU.
- `TELEOP_LIVEKIT_PUBLIC_URL` should be set to the headset-reachable WSS URL (e.g.
  `wss://goliath.<tailnet>.ts.net:15580`); empty falls back to `TELEOP_LIVEKIT_URL`.
- The publisher reads the robot MJPEG stream (default `{yahboom_api_url}/stream`), downscales
  to the configured frame size, and publishes VP8 at `TELEOP_LIVEKIT_PUBLISHER_FPS`.
- If MJPEG fails, `TELEOP_LIVEKIT_SNAPSHOT_FALLBACK=1` polls snapshots instead.

## Robot adapters

Select the adapter with the `?robot=` query parameter on `/ws/teleop`:

| Robot | Adapter | Notes |
|-------|---------|-------|
| boomy | BoomyAdapter | Yahboom ROSMASTER X3 via yahboom-mcp |
| bumi | BumiAdapter | Bumi biped via bumi-mcp |
| vboomy | VboomyAdapter | Resonite virtual twin via OSC (port 9000) |

## Runtime tuning

`teleop_configure` (MCP) and `POST /api/v1/teleop/*` (REST mirrors) adjust gains at runtime
without a restart: `max_linear`, `max_angular`, `pan_gain`, `tilt_gain`, `yahboom_api_url`.

## Validation

After changing `.env`, restart the backend and confirm:

- `http://127.0.0.1:10901/api/v1/health` returns `{"status":"ok", ...}`
- The health payload reports the expected `yahboom_api` URL.
- If LiveKit is enabled, `/api/v1/livekit/status` shows the publisher state.
