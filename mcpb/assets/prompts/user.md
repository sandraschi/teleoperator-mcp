# Teleoperator MCP — User Guide

## Introduction

Welcome to Teleoperator MCP, the WebXR teleoperation gateway for the MCP fleet. This guide
takes you from zero to operating a robot from a VR headset, supervising sessions through MCP
tools, and troubleshooting the most common failure modes. The system lets a human operator in
a VR headset (Pico 4 or Meta Quest) drive a physical or virtual robot while an AI agent
supervises the session, manages authority between human and autonomous control, and handles
emergency situations.

This guide is written for three audiences: operators who put on the headset and drive,
supervisors who use the MCP tools from an agent or a CLI, and maintainers who set up the
stack on a new machine. The sections are arranged so that you can start with the quick start,
then dig into configuration, then the full tool and endpoint reference, then tutorials, and
finally troubleshooting.

The core principle to remember: pose never traverses MCP tool calls. The webapp is the VR
client. MCP tools supervise. If you remember that, the whole architecture makes sense.

## Quick Start

### Prerequisites

Before you can run anything you need the following on the host machine (Goliath or a dev
laptop):

- Python 3.12 or newer.
- uv (the Python package manager and runner used across the fleet). The fleet uses
  `C:\Users\sandr\.local\bin\uv.exe` on Goliath.
- Node.js and npm (for the Vite webapp). The fleet also has bun installed.
- Git to clone the repository.
- For physical robots: the robot's own bridge (yahboom-mcp for Boomy) and the robot powered
  on and reachable on the network.
- For video return: the LiveKit SFU. On the fleet this is the `LiveKitSFU` Windows service on
  port 15580, managed by NSSM.
- For a headset: a Pico 4 or Meta Quest with Tailscale installed and the webapp served over
  HTTPS (Tailscale Serve on Goliath).

### Clone and install

```powershell
git clone https://github.com/sandraschi/teleoperator-mcp
cd teleoperator-mcp
just bootstrap
```

`just bootstrap` runs `uv sync --all-extras` (installs Python dependencies), runs `npm
install` in the webapp directory (installs frontend dependencies), and installs the
pre-commit hooks. If you do not have `just` installed, run the three commands by hand.

### Start the stack

The simplest way to start the full stack (backend on 10901 and Vite frontend on 10900) is:

```powershell
.\webapp\start.bat -WithTailscaleServe
```

This clears any stale processes on the ports, runs `uv sync` if needed, loads `.env`, detects
your Tailscale hostname for CORS and the public LiveKit URL, starts the backend, waits until
`/api/v1/health` returns 200 (with a 90 second timeout), starts Vite, and then serves the
webapp over Tailscale so the headset can reach it over HTTPS.

Alternatively, start the backend and frontend in separate terminals:

```powershell
# Terminal 1 - backend
uv run python -m teleoperator_mcp.server --mode dual --port 10901

# Terminal 2 - frontend
Set-Location webapp
npm run dev
```

There is also a Pico M1 helper that starts detached windows:

```powershell
.\scripts\m1-up.ps1
```

### Connect a headset

1. Install Tailscale on the Pico 4 or Meta Quest and join the same tailnet as Goliath.
2. Open the headset browser (Pico Browser on the Pico 4) to your Tailscale Serve URL, which
   looks like `https://goliath.<your-tailnet>.ts.net/`.
3. Accept the HTTPS certificate if prompted.
4. Choose a robot (boomy, bumi, or vboomy) from the selector.
5. Click Enter VR. The browser starts a WebXR immersive-vr session.
6. In the headset: squeeze either grip to take over, squeeze the trigger for deadman drive,
   use the right stick for base translation and rotation, and look around to pan and tilt the
   camera when the gaze group is in DIRECT mode.

If you do not have a headset you can still develop and test using the vboomy virtual twin in
Resonite, which needs no physical hardware.

## Configuration

### The `.env` file

All runtime configuration is read from environment variables prefixed with `TELEOP_`. The
repository ships a template at `.env.example`. Copy it to `.env` and edit:

```powershell
Copy-Item .env.example .env
```

The `.env` file is gitignored, so your local values never get committed. The most important
values to set for a fresh install are:

- `TELEOP_YAHBOOM_API_URL` — where yahboom-mcp lives (default http://127.0.0.1:10892).
- `TELEOP_CORS_ORIGINS` — the browser origins allowed to talk to the backend. The launcher
  sets this automatically from `tailscale serve status`; you only need to set it manually if
  you are not using Tailscale.
- `TELEOP_LIVEKIT_API_KEY` and `TELEOP_LIVEKIT_API_SECRET` — must match the LiveKit SFU
  server's configured credentials. The dev defaults are `devkey` and `secret`.
- `TELEOP_LIVEKIT_PUBLIC_URL` — the WSS URL the headset should use. If empty, the server uses
  `TELEOP_LIVEKIT_URL`.

### Ports

The standard ports are:

- 10900 — Vite dev frontend (the WebXR client).
- 10901 — FastAPI backend (REST + WebSocket + MCP HTTP at `/mcp`).
- 10892 — yahboom-mcp (Boomy robot bridge).
- 10774 — bumi-mcp (biped bridge).
- 15580 — LiveKit SFU (video return).
- 10909 — speech-mcp (spoken warnings).

These are registered in the fleet port registry. Do not change them casually; the webapp and
start scripts reference them.

### Environment variable reference

The full table is in `llms-full.txt` and the server docstring. Highlights:

| Variable | Default | Purpose |
|---|---|---|
| TELEOP_HOST | 0.0.0.0 | Backend bind address |
| TELEOP_PORT | 10901 | Backend port |
| TELEOP_YAHBOOM_API_URL | http://127.0.0.1:10892 | Boomy REST API |
| TELEOP_WATCHDOG_MS | 1000 | Watchdog interval |
| TELEOP_POSE_HZ_CAP | 30 | Max pose rate |
| TELEOP_MAX_LINEAR | 0.3 | Max linear m/s |
| TELEOP_MAX_ANGULAR | 0.8 | Max angular rad/s |
| TELEOP_PAN_GAIN | 60.0 | PTZ pan gain |
| TELEOP_TILT_GAIN | 45.0 | PTZ tilt gain |
| TELEOP_DEFAULT_ROBOT | boomy | Default WS robot |
| TELEOP_RECORDING_ENABLED | 1 | JSONL recording |
| TELEOP_LIVEKIT_ENABLED | 1 | LiveKit video |
| TELEOP_LIVEKIT_URL | ws://127.0.0.1:15580 | LiveKit server |
| TELEOP_LIVEKIT_ROOM | teleop-boomy | Room name |
| TELEOP_AUTO_MAX_DURATION_S | 10 | AUTO max seconds |
| TELEOP_AUTO_REQUIRE_WEBXR | 1 | WebXR gate for AUTO |
| TELEOP_SPEECH_ENABLED | 1 | Spoken warnings |
| TELEOP_SPEECH_MCP_URL | http://127.0.0.1:10909 | speech-mcp endpoint |

## Running Modes

The server has three modes, selected with `--mode`:

- `--mode stdio` — runs FastMCP over stdio. This is what Claude Desktop and IDE agents use.
  Run `uv run python -m teleoperator_mcp.server --mode stdio`.
- `--mode http` — runs uvicorn serving the FastAPI app (REST, WebSocket, and `/mcp` HTTP
  transport).
- `--mode dual` — the default, identical to http in current builds; the name signals that
  REST and MCP HTTP coexist on the same port.

The `just serve` recipe runs `--mode dual --port 10901`. The packaged Tauri app uses
`run_server.py`, which reads `MCP_PORT` (or `PORT`) and `MCP_HOST` and falls back to stdio
when no port is set.

## MCP Tools — Complete Reference

Every tool returns a dict with `success` and `message`. Read-only tools never change state;
mutating tools change session state; destructive tools must be used with care.

### teleop_status

Read the full session snapshot. No arguments.

Example session state fields: `active`, `robot`, `frames_in`, `uptime_s`, `watchdog_latched`,
`estop_count`, `authority` (per-group `mode`/`owner`), `groups_available`, `any_auto`.

```json
{
  "success": true,
  "message": "Teleop session active",
  "active": true,
  "robot": "boomy",
  "frames_in": 1250,
  "authority": {
    "base": {"mode": "DIRECT", "owner": "human"},
    "gaze": {"mode": "DIRECT", "owner": "human"},
    "manip": {"mode": "IDLE", "owner": "none"}
  },
  "estop_latched": false,
  "any_auto": false
}
```

### teleop_configure

Adjust mapping gains and the robot API URL at runtime.

Arguments (all optional): `max_linear`, `max_angular`, `pan_gain`, `tilt_gain`,
`yahboom_api_url`.

Example: `teleop_configure(max_linear=0.2, pan_gain=90.0)` reduces the speed cap and
increases the pan sensitivity. Returns the new effective values.

### teleop_estop

Emergency stop. Zeroes drive on all actuator groups and latches the estop flag. No arguments.
Use immediately on any hazard. Afterward, `teleop_takeover` clears the latch.

### teleop_set_mode

Set authority for an actuator group. Arguments: `group` (base, gaze, manip), `mode` (DIRECT,
AUTO), `confirm_bench` (bool, default false).

AUTO on the base group requires an active WebXR session unless `confirm_bench=true`. The AUTO
run is time-bounded by `TELEOP_AUTO_MAX_DURATION_S`.

Example: `teleop_set_mode(group="base", mode="AUTO", confirm_bench=True)`.

### teleop_takeover

Human reclaims authority on one group or all groups. Clears the estop latch. Argument:
`group` (optional; omit for all).

Example: `teleop_takeover(group="base")`.

### teleop_set_gaze

Move the Boomy camera to absolute pan/tilt. Arguments: `pan`, `tilt` (0-180 degrees, center
~90).

Example: `teleop_set_gaze(pan=120, tilt=60)` looks up-right.

### teleop_gaze_center

Center the camera servos. No arguments.

### teleop_livekit_status

LiveKit video return status. No arguments. Returns `enabled`, `running`, `connected`, `room`,
`identity`, `frames_published`, `last_error`, `source`, `width`, `height`, `mjpeg_url`,
`livekit_url`.

### teleop_livekit_publisher_start

Start the MJPEG to LiveKit publisher. No arguments.

### teleop_livekit_publisher_stop

Stop the publisher. No arguments.

### show_teleop_status_card

Render a Prefab App status card in the chat with the stat grid, robot catalog, and authority
mode. No arguments.

### teleop_shutdown

Gracefully shut down the server: stop publisher, disconnect clients, exit. Argument:
`confirm` (must be true).

## REST API Reference

The backend exposes a REST API. All JSON unless noted.

### Health

`GET /api/v1/health` — liveness plus session and LiveKit status.

```json
{
  "status": "ok",
  "service": "teleoperator-mcp",
  "version": "0.1.0",
  "uptime_s": 123.4,
  "teleop": {...},
  "livekit": {...}
}
```

### Diagnostics

`GET /api/v1/diagnostics` — full diagnostics for CUA-NSIS smoke tests: tool list, system
info, errors.

### Capabilities

`GET /api/capabilities` — runtime tool surface, features, inventory, transport info.

### Logs

- `GET /api/logs?limit=50&offset=0&level=INFO&kind=system&search=&sort=desc&after_id=`
  — query the ring buffer.
- `GET /api/logs/stats` — buffer stats.
- `GET /api/logs/export?format=json|csv` — export logs.
- `DELETE /api/logs` — clear the buffer.

### Robots

`GET /api/v1/robots` — robot adapter catalog.

### LiveKit

- `GET /api/v1/livekit/config?robot=` — public connection info for the headset.
- `POST /api/v1/livekit/token` with `{"identity": "...", "room": "...", "name": "..."}` —
  subscribe-only JWT.
- `GET /api/v1/livekit/status` — publisher status.
- `POST /api/v1/livekit/publisher/start` and `/stop` — publisher control.

### Teleop REST mirrors

- `POST /api/v1/teleop/estop`
- `POST /api/v1/teleop/takeover`
- `POST /api/v1/teleop/gaze?pan=90&tilt=90`
- `POST /api/v1/teleop/gaze/center`
- `POST /api/v1/teleop/set_mode?group=base&mode=DIRECT&confirm_bench=false`

### Recording export

`POST /api/v1/recording/export` with optional body `{"input_dir": "...", "output_dir": "...",
"episodes": [0,1], "overwrite": false}` — convert JSONL episodes to LeRobot parquet.

### Shutdown

`POST /api/shutdown?confirm=true` — graceful shutdown.

### Local LLM

- `GET /api/llm/providers` — detect Ollama and list models.
- `POST /api/llm/chat` with `{"model": "...", "prompt": "..."}` — chat completion.

### WebSocket

`WS /ws/teleop?robot=boomy` — the pose stream. The client sends JSON pose frames and receives
acknowledgements and state updates. The watchdog stops drive if frames stop arriving.

## Tutorials

### Tutorial 1: Drive Boomy from the webapp (no headset)

You can drive Boomy from a normal browser tab that emulates enough to exercise the session,
or simply verify the pipeline is alive:

1. Start the stack: `.\webapp\start.bat` (skip Tailscale for a local browser test).
2. Open http://localhost:10900.
3. Confirm the backend dot shows ok and the KPI cards render.
4. If you have no physical robot, select `vboomy` (virtual twin) instead of `boomy`.

This verifies the webapp, backend, health polling, and capabilities introspection all work.

### Tutorial 2: Full headset teleop with Boomy

1. Ensure yahboom-mcp is running on 10892 and Boomy is powered on.
2. Start the stack with `.\webapp\start.bat -WithTailscaleServe`.
3. Put the Pico 4 or Quest on the tailnet and open the Serve URL.
4. Select boomy and Enter VR.
5. Squeeze a grip to take over, then hold the trigger to drive with the right stick.
6. Watch the KPI cards: Frames In should climb, Teleop session Active.
7. Confirm camera video arrives via LiveKit.

If the robot does not move, check tutorial 7 (troubleshooting) and the LiveKit section.

### Tutorial 3: Supervise a session with MCP tools

From Claude Desktop, an agent, or the CLI:

1. Call `teleop_status()` — learn whether a session is active, which robot, and the authority
   state.
2. Call `teleop_livekit_status()` — confirm video return.
3. Change authority for a test: `teleop_set_mode(group="base", mode="AUTO",
   confirm_bench=True)` on the bench, or `teleop_set_mode(group="base", mode="DIRECT")` to
   hand back to the human.
4. Verify with `teleop_status()` that `any_auto` and per-group modes reflect the change.

### Tutorial 4: Emergency stop drill

Practice the hazard sequence so it is automatic:

1. Start a session (real or bench).
2. Call `teleop_estop()`. Confirm `estop_latched` becomes true in the response and that drive
   stops.
3. Observe `teleop_status()` reports `estop_latched: true`.
4. Clear it: `teleop_takeover()`.
5. Confirm the latch clears and groups return to DIRECT/human.

### Tutorial 5: Camera gaze control

1. With Boomy's camera online, call `teleop_set_gaze(pan=90, tilt=90)` to center.
2. Sweep to `teleop_set_gaze(pan=150, tilt=70)`.
3. Return with `teleop_gaze_center()`.
4. In head-follow mode (gaze group DIRECT), look around and watch the camera track your head
   within the configured gains and center.

### Tutorial 6: Start and stop the LiveKit publisher

1. Check `teleop_livekit_status()`.
2. If not running, call `teleop_livekit_publisher_start()`.
3. Confirm `running` and `connected` become true and `frames_published` increases.
4. On the headset, confirm the camera video overlay renders.
5. When done, `teleop_livekit_publisher_stop()`.

### Tutorial 7: Record and export a session

1. Ensure `TELEOP_RECORDING_ENABLED=1` in `.env`.
2. Run a teleop session.
3. Afterward, `POST /api/v1/recording/export` to convert JSONL to LeRobot parquet.
4. Confirm the output directory contains the exported episodes.

### Tutorial 8: Runtime tuning with teleop_configure

1. Drive Boomy and observe its speed and camera feel.
2. Call `teleop_configure(max_linear=0.2, max_angular=0.6, pan_gain=75.0, tilt_gain=50.0)`.
3. Re-drive and compare. Confirm the new values are returned.
4. To point the adapter at a different robot API:
   `teleop_configure(yahboom_api_url="http://192.168.1.100:10892")`.

### Tutorial 9: vboomy virtual twin on Resonite

1. Start Resonite and load your robot scene.
2. Run `.\scripts\register-vboomy.ps1` to register the OSC target.
3. In the webapp select vboomy and Enter VR.
4. Drive; the twin in Resonite should mirror the pose via OSC on port 9000.

### Tutorial 10: Integration test harness

With the backend running, exercise the full pose pipeline headlessly:

```powershell
just integration-test
```

This runs `scripts/ws-integration-harness.py --frames 60 --look`, which connects to the
WebSocket, streams synthetic frames, and checks handshake, acks, estop, authority, recording
on disk, and the watchdog. A 12/12 pass means the pipeline is healthy end to end.

## Troubleshooting

### Robot does not move

1. Confirm yahboom-mcp is running and reachable: `Invoke-RestMethod http://127.0.0.1:10892/...`.
2. Confirm Boomy is powered on and on the network.
3. Confirm the session is active: `teleop_status()` shows `active: true` and frames increasing.
4. Confirm the estop is not latched and no watchdog latch is set.
5. Confirm authority: the base group must be DIRECT (or AUTO with an active producer) and
   owned by someone.
6. Check `GET /api/v1/health` for the yahboom API URL in use.

### No video in the headset

1. `teleop_livekit_status()` — if `running` is false, start the publisher.
2. If `connected` is false, the LiveKit SFU is down. Check `Get-Service LiveKitSFU` and that
   port 15580 listens.
3. Check teleconference-mcp logs: `teleconference-mcp/logs/livekit.out.log`.
4. Verify the API key/secret match the SFU config.
5. If MJPEG fails, the snapshot fallback should still produce frames; check `source`.

### WebXR not available

1. The browser must support `immersive-vr`. The Pico 4 uses Pico Browser; the Quest uses its
   built-in browser.
2. WebXR requires HTTPS. If you are on HTTP, use Tailscale Serve (`-WithTailscaleServe`).
3. Check `navigator.xr.isSessionSupported("immersive-vr")` in the headset browser console.

### WebSocket disconnects / watchdog trips

1. The watchdog latches when no pose frames arrive within `TELEOP_WATCHDOG_MS`. Check the
   frame rate is actually flowing (KPI Frames In).
2. Network latency above the watchdog interval on Tailscale can cause trips; raise
   `TELEOP_WATCHDOG_MS` if the link is slow.
3. Keep the headset browser tab in the foreground.

### AUTO mode fails to start

1. AUTO on base requires an active WebXR session unless `confirm_bench=true`.
2. The AUTO timer bounds the run at `TELEOP_AUTO_MAX_DURATION_S`.
3. If a warning fires, the speech server may be down; the SAPI fallback should still speak.

### Backend fails to start

1. Port 10901 may be occupied; the launcher clears it, but if a zombie process holds it,
   kill it with `taskkill /F /PID <pid>`.
2. `uv sync` may need re-running after a dependency change.
3. Check the backend window for a traceback; common causes are missing `.env` variables and
   LiveKit credentials that do not match the SFU.

### CORS errors in the headset browser

1. The headset accesses the webapp over a `*.ts.net` origin. `TELEOP_CORS_ORIGINS` must
   include that origin. The launcher sets it from `tailscale serve status`.
2. If you set it manually, include both the https origin and localhost origins.

## FAQ

**Do I need a headset to use this?** No. You can use the vboomy virtual twin in Resonite for
development and testing without physical hardware.

**Does pose go through MCP?** No. Pose travels the WebSocket hot path; MCP tools supervise.

**Which robots are supported?** Boomy (Yahboom ROSMASTER X3), Bumi (biped), and vboomy
(Resonite virtual twin). More adapters are planned.

**What is the dual-mode authority model?** Each actuator group is owned by the human (DIRECT)
or a producer (AUTO). An estop latch stops everything until cleared by takeover.

**How do I stop the robot in an emergency?** Call `teleop_estop()` immediately. It zeroes all
drive and latches until `teleop_takeover()`.

**Why does AUTO stop after a few seconds?** AUTO is time-bounded by `TELEOP_AUTO_MAX_DURATION_S`
(default 10 s) as a safety measure.

**Where do recordings go?** `data/teleop_recordings` as JSONL episodes, exportable to LeRobot
parquet via `/api/v1/recording/export`.

**What is port 15580?** The LiveKit SFU for video return, run as a Windows service on Goliath.

**How do I integrate with Claude Desktop?** Add the stdio command to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "teleoperator-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/teleoperator-mcp", "python", "-m", "teleoperator_mcp.server", "--mode", "stdio"]
    }
  }
}
```

**How do I run the tests?** `just test` runs the pytest suite; `just lint` runs ruff and
TypeScript checks; `just ci` runs the same gates as GitHub Actions locally.

## Where to go next

- `docs/ARCHITECTURE.md` — the two-pipe map (control vs video), ports, module index.
- `docs/DUAL_MODE_ARCHITECTURE.md` — the arbiter / authority model.
- `docs/LIVEKIT.md` — video return setup and troubleshooting.
- `docs/LEROBOT.md` — session recording and export.
- `docs/TAILSCALE_VIEWERS.md` — headset and Tailscale setup.
- `docs/BRINGUP.md` — milestone 1 hardware checklist.
- `llms-full.txt` — the full machine-readable manifest.

## Safety Notes

- Always be ready to hit the estop. Physical robots can cause injury or property damage.
- Keep velocity clamps conservative. Raise limits only with explicit operator agreement.
- AUTO mode is a bounded test capability; never rely on it as a production autonomous driver.
- Never commit a real `.env` with LiveKit credentials or robot API secrets.
- The watchdog is your friend: if frames stop, drive stops. Do not disable it.

## The Dual-Mode Architecture Explained

The system is heading toward dual-mode telesupervision: a human teleoperates while an
autonomous policy proposes actions and a human supervisor retains veto power. The pieces
shipped so far are the arbiter (authority model) and the first producer (nav stub). Here is
how to reason about the model.

Each actuator group can be owned by exactly one actor. When the group is in DIRECT mode, the
human owns it: the WebXR headset pose is mapped to commands for that group. When the group is
in AUTO mode, a producer owns it: some program emits commands for that group instead. The
estop latch is global and overrides everything: while latched, no group receives drive.

The authority state is exposed through `teleop_status()` in the `authority` object. Each of
`base`, `gaze`, and `manip` has a `mode` and an `owner`. `any_auto` is a quick aggregate: if
true, at least one group is in AUTO. `estop_latched` reports the latch. `groups_available`
tells you which groups exist for the current robot.

The typical AUTO flow is: an operator (or an agent acting on their behalf) calls
`teleop_set_mode(group="base", mode="AUTO")`. The arbiter checks the AUTO safety gates: an
active WebXR session must exist unless `confirm_bench=true`, and the run is time-bounded by
`TELEOP_AUTO_MAX_DURATION_S` with a warning at `TELEOP_AUTO_WARN_BEFORE_S`. The nav stub
producer then emits commands until the timer expires, at which point authority returns and
the operator reclaims with `teleop_takeover()`.

Why does AUTO require WebXR by default? Because a robot moving on its own is risky; requiring
a live operator connection means the human can immediately intervene. Bench mode bypasses the
WebXR requirement only for controlled test environments, and the timed stop still applies so
a forgotten bench run cannot drive forever.

## WebSocket Protocol Reference

The pose stream is a JSON protocol over the `/ws/teleop` WebSocket. It is the fastest path in
the system and should be used only for high-frequency pose updates; everything else goes
through MCP tools or REST.

Client sends pose frames such as:

```json
{
  "type": "pose",
  "timestamp": 1690000000.123,
  "position": [0.1, 1.2, 0.0],
  "rotation": [0.0, 0.0, 0.0, 1.0],
  "grip": [0.0, 1.0],
  "trigger": 0.0
}
```

The server acknowledges frames, updates session statistics (frames in, last frame time), maps
the pose to robot commands, and applies watchdog monitoring. If no frames arrive within
`TELEOP_WATCHDOG_MS`, the watchdog latches and drive stops. A stale headset therefore never
leaves the robot running unattended.

The integration harness in `scripts/ws-integration-harness.py` drives this protocol headlessly
and is the canonical reference for what a well-behaved client sends. It verifies handshake,
acks, estop behavior, authority changes, recording to disk, and watchdog latching — 12 checks
in total against the live stack.

## Configuration Walkthrough

### First-time machine setup

1. Install Python 3.12+, uv, Node.js, and just.
2. Clone the repo.
3. `just bootstrap`.
4. `Copy-Item .env.example .env`.
5. Edit `.env` with your Tailscale hostname, LiveKit credentials, and robot URLs.
6. Start with `.\webapp\start.bat` and verify http://localhost:10900 and
   http://127.0.0.1:10901/api/v1/health.

### LiveKit credentials

The LiveKit SFU is a fleet service (`LiveKitSFU` Windows service, port 15580). The
`TELEOP_LIVEKIT_API_KEY` and `TELEOP_LIVEKIT_API_SECRET` must match what the SFU is
configured with. The dev defaults `devkey` / `secret` work only against a dev SFU. If the
publisher connects but the headset gets a token rejection, the mismatch is the cause.

### CORS for the headset

The headset loads the webapp from a `https://*.ts.net` origin. The backend must allow that
origin. `webapp/start.ps1` calls `tailscale serve status` and builds `TELEOP_CORS_ORIGINS`
automatically. If you run the backend by hand, set `TELEOP_CORS_ORIGINS` to include your
Tailscale hostname plus localhost origins:

```powershell
$env:TELEOP_CORS_ORIGINS = "https://goliath.tailfab45.ts.net,http://localhost:10900,http://127.0.0.1:10900"
```

## Advanced Topics

### Head-follow mode

When the gaze group is in DIRECT mode, the head pose drives the Boomy camera pan and tilt
within the configured center and gains. `TELEOP_PTZ_PAN_CENTER` and `TELEOP_PTZ_TILT_CENTER`
set the neutral position (both default to 90 degrees on the 0-180 servo range).
`TELEOP_GAZE_EVERY_N_FRAMES` and `TELEOP_GAZE_MIN_DELTA_DEG` throttle the gaze updates so the
camera servos do not chatter. Use `teleop_gaze_center()` to return to the neutral reference.

### Bench mode

`confirm_bench=true` on `teleop_set_mode` skips the WebXR requirement for AUTO. Bench mode is
for a robot on blocks or a test bench where no operator is present. The timed stop still
applies. Always double-check the robot cannot move before enabling bench mode.

### Recording pipeline

With recording enabled, each session writes a LeRobot-compatible JSONL episode under
`data/teleop_recordings`. Episodes are time-stamped and robot-tagged. After a session,
`POST /api/v1/recording/export` converts them to LeRobot v2.1 parquet. You can select specific
episodes with the `episodes` array and force overwrite with `overwrite: true`.

### Spoken warnings

With `TELEOP_SPEECH_ENABLED=1`, the gateway sends warning utterances to speech-mcp at
`TELEOP_SPEECH_MCP_URL`. If the speech server is unreachable, the gateway falls back to
Windows SAPI. Warnings typically fire around AUTO mode transitions and watchdog events.

## Deployment Notes

### As a Windows service

The fleet runs the LiveKit SFU as a Windows service via NSSM (`LiveKitSFU`). The teleop
backend itself is normally launched by `webapp/start.ps1` or the Tauri desktop shell. The
Tauri build embeds the backend as a PyInstaller executable and the NSIS installer wires it
into the desktop app. For a headless service install, wrap `uv run python -m
teleoperator_mcp.server --mode dual` with NSSM and set the working directory to the repo
root.

### Tauri desktop app

The `native/` directory contains the Tauri 2.0 shell. `just build-native` builds the
installer. The app embeds the backend executable, launches it, waits for the backend port,
and then opens the webapp. The frontend polls `/api/v1/health` with exponential backoff. The
backend executable reads `MCP_PORT`/`MCP_HOST` from the environment, which is how the shell
tells it which port to bind.

## Troubleshooting Reference Card

| Symptom | First check | Fix |
|---|---|---|
| Robot frozen | `teleop_status()` → `estop_latched`, `watchdog_latched`, `authority` | `teleop_takeover()`, verify frames flowing |
| No video | `teleop_livekit_status()` → `running`, `connected`, `last_error` | start publisher; restart LiveKitSFU service |
| WebXR missing | browser + HTTPS | use Tailscale Serve; check `navigator.xr` |
| Disconnects | frames in / watchdog | raise `TELEOP_WATCHDOG_MS`; foreground the tab |
| AUTO refused | WebXR session | pass `confirm_bench=true` on the bench |
| CORS blocked | browser console | set `TELEOP_CORS_ORIGINS` incl. ts.net origin |
| Port busy | backend window traceback | clear port, `uv sync`, retry |

## FAQ

**Do I need a headset to use this?** No. You can use the vboomy virtual twin in Resonite for
development and testing without physical hardware.
