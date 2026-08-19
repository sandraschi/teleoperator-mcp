# Teleoperator MCP — System Capabilities

## Overview

Teleoperator MCP is a WebXR teleoperation gateway that connects a virtual reality headset
(Pico 4, Meta Quest 3, or any WebXR-capable browser) to physical and virtual robots on the
fleet. A human operator wearing a VR headset sees a 3D telepresence view and their head and
hand pose is streamed over a WebSocket to a Python gateway. The gateway maps that pose into
robot-specific actuator commands through a pluggable adapter layer, and sends those commands
to the robot's own control API. The same gateway exposes MCP tools for supervision — status
queries, authority management, emergency stop, camera gaze control, and LiveKit video return
— so that an LLM agent acting as a supervisor can monitor the teleoperation session, take
emergency action, or hand authority between human and autonomous control.

The system is designed around a strict separation of concerns. The pose hot path (30 Hz
WebSocket frames from the headset) never traverses MCP tool calls. MCP tools operate on the
session at a supervisory cadence of seconds, not milliseconds. Video return flows through a
separate LiveKit WebRTC pipe so that the operator can see what the robot's camera sees with
low latency and without congesting the pose channel. Session recording writes LeRobot-compatible
JSONL episodes that can later be exported to the LeRobot v2.1 parquet format for training
autonomous policies (visual-language-action models).

The fleet target is dual-mode telesupervision: a human teleoperates through WebXR while an
autonomous policy produces candidate commands that a human supervisor can veto. The arbiter
module already implements the authority model: each actuator group (base, gaze, manip) can be
in DIRECT mode (human owns it) or AUTO mode (a producer owns it), and an emergency stop latch
can freeze all drive regardless of mode. The nav stub producer ships as the first autonomous
producer; a headset squeeze gesture reclaims authority instantly.

## Architecture

The server runs as a single Python process on a host machine (Goliath). It is a FastAPI
application that mounts a FastMCP HTTP transport at `/mcp`, exposes a REST API under
`/api/*`, and accepts WebSocket connections at `/ws/teleop`. In stdio mode the same FastMCP
server object runs over the MCP stdio transport, which is what Claude Desktop and IDE agents
connect to.

The control path has these stages:

1. The headset browser opens `/ws/teleop?robot=boomy` and streams pose frames as JSON.
2. The WebSocket handler validates the frame, updates session statistics, and feeds the
   pose into a pose-to-command mapper.
3. The mapper applies gains and safety clamps from settings (max linear velocity, max
   angular velocity, pan/tilt gains).
4. The resulting ProducerCommand is dispatched to the active RobotAdapter.
5. The adapter translates the command into the robot's native REST API call (for example
   `POST /cmd_vel` on yahboom-mcp for Boomy) and reports success or failure.

The video path is separate. An MJPEG publisher reads the robot's camera stream (an MJPEG
HTTP endpoint), encodes frames, and publishes them to a LiveKit server (the fleet runs a
Windows NSSM service named `LiveKitSFU` on port 15580). The headset browser subscribes to
the LiveKit room and renders the robot camera as a textured overlay in the XR scene.

## MCP Tool Surface

There are 12 MCP tools. All tools return a dictionary with at least `success` and `message`
keys, and most include additional domain fields. Tools are annotated as read-only, mutating,
or destructive to inform the agent of side effects before calling.

### teleop_status (read-only)

Returns a complete snapshot of the active teleop session: connection state, robot target,
frame count, watchdog state, authority mode per actuator group, estop latch, AUTO elapsed
time, and the set of groups available. No arguments. This is the primary tool an agent calls
to understand the state of a teleoperation session before doing anything else.

Example response fields: `active`, `robot`, `active_robot`, `robots`, `recording`, `robot_id`,
`display_name`, `frames_in`, `last_frame_at`, `uptime_s`, `client`, `watchdog_latched`,
`estop_count`, `auto_elapsed_s`, `authority` (with `base`, `gaze`, `manip` entries each
carrying `mode` and `owner`), `estop_latched`, `groups_available`, `any_auto`, `yahboom_api`,
`watchdog_ms`.

### teleop_configure (mutating)

Adjusts teleop mapping gains and the downstream robot API URL at runtime without a restart.
Accepted parameters: `max_linear` (m/s linear speed cap), `max_angular` (rad/s angular speed
cap), `pan_gain` (camera pan gain factor), `tilt_gain` (camera tilt gain factor), and
`yahboom_api_url` (override the yahboom-mcp REST base URL). All parameters are optional; only
the ones provided are changed. Returns the new effective values so the agent can confirm.

### teleop_estop (destructive)

Hard emergency stop. Zeroes drive on all actuator groups regardless of current authority mode
and latches the estop flag. This is the operator or agent veto mechanism. It must be used
whenever there is a hazard: unexpected robot motion, loss of safe teleop conditions, or any
anomalous behavior. After the hazard is cleared, `teleop_takeover` clears the latch.

### teleop_set_mode (mutating)

Sets the authority mode for one actuator group. Groups are `base`, `gaze`, and `manip`.
Modes are `DIRECT` (human owns the group) and `AUTO` (a producer owns the group). For base
group AUTO mode, an active WebXR session is normally required unless `confirm_bench` is set
to true, which is intended for bench testing only (a block and timed stop still apply).
Returns the new mode and owner of the group.

### teleop_takeover (mutating)

Human reclaims authority on one actuator group, or on all available groups when no group is
specified. Clears the estop latch. This is how the operator regains control after an AUTO
producer or after an estop. Returns the list of groups taken over.

### teleop_set_gaze (mutating)

Moves the Boomy camera servos to an absolute pan/tilt. Both pan and tilt are expressed in
degrees from 0 to 180 with center at roughly 90 degrees. This is used for PTZ bench testing
and as the neutral reference for head-follow. Returns the applied pan and tilt.

### teleop_gaze_center (mutating)

Centers the camera servos to the neutral head-follow reference (the configured pan and tilt
center values). No arguments.

### teleop_livekit_status (read-only)

Returns the LiveKit video return status: whether LiveKit is enabled, whether the publisher is
running, whether it is connected to the room, the room name, the publisher identity, frames
published, last frame timestamp, last error, source type, frame dimensions, MJPEG URL, and the
public LiveKit URL for the headset.

### teleop_livekit_publisher_start (mutating)

Starts the Goliath-side MJPEG to LiveKit publisher for the Boomy camera. The publisher reads
the MJPEG stream, downscales to the configured frame size (default 640x480), and publishes a
VP8 video track to the configured room at the configured frame rate. Returns publisher status.

### teleop_livekit_publisher_stop (mutating)

Stops the LiveKit camera publisher and disconnects from the room. Returns publisher status.

### show_teleop_status_card (read-only)

Renders the Teleoperator robot status and connection health as a rich Prefab App card in the
chat, with a stat grid (Active, Frames In, Robot, WebXR, LiveKit), an Available Robots
section, and the authority mode. Falls back to a plain dictionary if prefab_ui is not
installed.

### teleop_shutdown (destructive)

Gracefully shuts down the entire teleoperator server: stops the LiveKit publisher,
disconnects all WebXR clients, and terminates the process. Requires `confirm` to be set to
true as a guard against accidental shutdown.

## MCP Resources and Prompts

The server registers one resource, `teleop://status`, which returns the live session status
as a compact pollable text block without requiring a tool call. The block includes active
flag, frames in, robot, WebXR flag, base authority mode, and the yahboom API URL.

The server registers a prompt, `teleop_help`, which provides teleoperation guidance for
supervisors. It supports a topic parameter with values `overview`, `estop`, and `livekit`.
The overview prompt tells the agent to check `teleop_status()`, `teleop_livekit_status()`,
and `GET /api/v1/robots` and explains how to change authority, estop, and takeover. The
estop prompt describes the emergency stop procedure and the latch clearing sequence. The
livekit prompt describes how to check and start the video return publisher.

## REST API Surface

The server exposes a REST API for the webapp and for scripting. Endpoints:

- `GET /api/v1/health` — liveness plus teleop and LiveKit status.
- `GET /api/v1/diagnostics` — full diagnostics for CUA-NSIS smoke testing (tool list, system
  info, errors).
- `GET /api/capabilities` — fleet webapp introspection of the runtime tool surface, features,
  and inventory.
- `GET /api/logs` — ring-buffer log query with limit, offset, level, kind, search, sort.
- `GET /api/logs/stats` — log buffer statistics.
- `GET /api/logs/export` — export logs as JSON or CSV.
- `DELETE /api/logs` — clear the ring buffer.
- `GET /api/v1/robots` — robot adapter catalog.
- `GET /api/v1/livekit/config` — public LiveKit connection info for the headset.
- `POST /api/v1/livekit/token` — issue a subscribe-only JWT.
- `GET /api/v1/livekit/status` — publisher status.
- `POST /api/v1/livekit/publisher/start` and `/stop` — publisher control.
- `POST /api/v1/recording/export` — export JSONL sessions to LeRobot parquet.
- `POST /api/v1/teleop/estop`, `/takeover`, `/gaze`, `/gaze/center`, `/set_mode` — REST mirrors
  of the corresponding MCP tools for bench scripts.
- `POST /api/shutdown` — graceful shutdown, requires `confirm=true`.
- `GET /api/llm/providers` — local LLM provider discovery (Ollama).
- `POST /api/llm/chat` — local LLM chat completion.
- `WS /ws/teleop?robot=` — the pose WebSocket.
- `/mcp` — the FastMCP HTTP transport.

The `/api/logs` endpoints power a ring-buffer logger modal in the webapp. The health endpoint
powers the frontend health dot with exponential backoff polling (1, 2, 4, 8, 16 seconds).

## Environment Variables

All settings are read from the environment with the `TELEOP_` prefix via pydantic-settings,
loaded from `.env` if present. Key variables:

- `TELEOP_HOST` — backend bind address (default 0.0.0.0).
- `TELEOP_PORT` — backend port (default 10901).
- `TELEOP_YAHBOOM_API_URL` — Boomy robot REST API base (default http://127.0.0.1:10892).
- `TELEOP_CORS_ORIGINS` — comma-separated allowed browser origins (WebXR dev + Tailscale).
- `TELEOP_WATCHDOG_MS` — watchdog interval in milliseconds (default 1000).
- `TELEOP_POSE_HZ_CAP` — max pose update rate (default 30).
- `TELEOP_MAX_LINEAR` — max linear velocity m/s (default 0.3).
- `TELEOP_MAX_ANGULAR` — max angular velocity rad/s (default 0.8).
- `TELEOP_PAN_GAIN` / `TELEOP_TILT_GAIN` — PTZ gains.
- `TELEOP_PTZ_PAN_CENTER` / `TELEOP_PTZ_TILT_CENTER` — servo center (default 90 each).
- `TELEOP_GAZE_EVERY_N_FRAMES` / `TELEOP_GAZE_MIN_DELTA_DEG` — head-follow throttling.
- `TELEOP_DEFAULT_ROBOT` — default WS robot (boomy).
- `TELEOP_BUMI_API_URL`, `TELEOP_BUMI_MAX_LINEAR`, `TELEOP_BUMI_MAX_ANGULAR`,
  `TELEOP_BUMI_HEAD_YAW_GAIN`, `TELEOP_BUMI_HEAD_PITCH_GAIN` — Bumi biped adapter settings.
- `TELEOP_ROBOTICS_API_URL`, `TELEOP_VBOOMY_ROBOT_ID`, `TELEOP_LIVEKIT_VBOOMY_ROOM` —
  virtual twin adapter settings.
- `TELEOP_RECORDING_ENABLED` — enable LeRobot JSONL recording (default 1).
- `TELEOP_RECORDING_DIR` — recording directory (default data/teleop_recordings).
- `TELEOP_RECORDING_FPS` — recording frame rate (default 30).
- `TELEOP_LIVEKIT_ENABLED` — enable LiveKit (default 1).
- `TELEOP_LIVEKIT_URL` — LiveKit server URL (default ws://127.0.0.1:15580).
- `TELEOP_LIVEKIT_PUBLIC_URL` — headset-facing WSS URL on Tailscale; empty uses LIVEKIT_URL.
- `TELEOP_LIVEKIT_API_KEY` / `TELEOP_LIVEKIT_API_SECRET` — LiveKit credentials (must match SFU).
- `TELEOP_LIVEKIT_ROOM` — default room name (teleop-boomy).
- `TELEOP_LIVEKIT_PUBLISHER_FPS` — publisher frame rate (default 15).
- `TELEOP_LIVEKIT_SNAPSHOT_FALLBACK` — poll snapshots if MJPEG fails (default 1).
- `TELEOP_LIVEKIT_AUTO_START_PUBLISHER` — auto-start publisher at boot (default 0).
- `TELEOP_AUTO_MAX_DURATION_S` — AUTO mode max seconds (default 10).
- `TELEOP_AUTO_WARN_BEFORE_S` — warning lead time before AUTO cutoff (default 3).
- `TELEOP_AUTO_REQUIRE_WEBXR` — WebXR required for AUTO (default 1).
- `TELEOP_NAV_STUB_LINEAR` / `TELEOP_NAV_STUB_ANGULAR` — nav stub producer speeds.
- `TELEOP_SPEECH_ENABLED` — spoken warnings (default 1).
- `TELEOP_SPEECH_MCP_URL` — speech-mcp endpoint (default http://127.0.0.1:10909).
- `TELEOP_SPEECH_PROVIDER` — speech provider (default windows).

Never put a real LiveKit API secret in a committed file; use the `.env` file which is
gitignored, and keep the committed `.env.example` template values only.

## Robot Adapters

The adapter layer abstracts robot specifics behind a common interface. Adapters are selected
by the `?robot=` query parameter on the WebSocket.

- **BoomyAdapter** (id `boomy`): the Yahboom ROSMASTER X3 wheeled robot. Communicates with
  yahboom-mcp at `TELEOP_YAHBOOM_API_URL` (default port 10892). Supports base drive, PTZ gaze
  (pan/tilt servos 0-180 degrees), and head-follow. This is the flagship adapter and the one
  used for milestone bring-up.
- **BumiAdapter** (id `bumi`): the Bumi biped robot via bumi-mcp at port 10774. Supports base
  drive, legs, arms, and head, with per-gain settings for linear, angular, head yaw, and head
  pitch.
- **VboomyAdapter** (id `vboomy`): a virtual twin of Boomy inside Resonite, controlled over
  OSC on port 9000. This is a purely virtual target used for development and testing without
  physical hardware. Register with `scripts/register-vboomy.ps1`.

The adapter registry is exposed through `GET /api/v1/robots` and `GET /api/v1/health`. Planned
adapters include the Unitree R1-A5-D wheeled dual-arm robot (r1-a5-d).

## Authority Arbiter

The arbiter implements the dual-mode authority model. Each actuator group has an owner. In
DIRECT mode the human (WebXR operator) owns the group and their pose is mapped to commands.
In AUTO mode a producer owns the group. Producers implement a common interface; the first
shipped producer is the nav stub, which drives the base at a fixed linear velocity for a
bounded duration (max 10 seconds by default). AUTO on the base group requires an active WebXR
session unless `confirm_bench=true` is passed, and a timed stop applies regardless.

The estop latch is global. Once latched, all groups stop and remain stopped until
`teleop_takeover` clears the latch. The watchdog also latches: if no pose frames arrive
within the watchdog interval, the watchdog latches and drive stops. This is the safety
backstop against a dead headset or a stalled WebSocket.

The arbiter exposes mode and ownership through `teleop_status` and `GET /api/v1/health`, and
accepts mode changes through `teleop_set_mode` and `POST /api/v1/teleop/set_mode`.

## Session Recording

When recording is enabled, the gateway appends each pose frame and its mapped command to a
LeRobot-compatible JSONL episode file under the configured recording directory. Episodes are
split automatically per session. `POST /api/v1/recording/export` converts completed episodes
to LeRobot v2.1 parquet format for downstream training. The export endpoint accepts optional
input dir, output dir, episode indices, and overwrite flag.

## Safety Governor

Safety is enforced at multiple layers:

- **Velocity clamps**: max linear and max angular are enforced in the mapper, so a pose spike
  or a bad gain cannot command an unbounded robot speed.
- **Watchdog**: no frames within `TELEOP_WATCHDOG_MS` latches the watchdog and stops drive.
- **Estop**: `teleop_estop` zeroes all drive and latches until takeover.
- **AUTO timer**: AUTO mode on base is time-bounded (10 seconds default) and requires WebXR
  unless bench-confirmed.
- **Spoken warnings**: when enabled, the gateway sends warning utterances to speech-mcp
  (port 10909), with a Windows SAPI fallback if the speech server is unreachable.

## Fleet Integration

Teleoperator MCP integrates with the fleet at the following ports and services:

- Webapp frontend: port 10900 (Vite dev).
- Backend: port 10901 (FastAPI + WebSocket + MCP HTTP).
- yahboom-mcp: Boomy robot bridge at port 10892.
- bumi-mcp: Biped robot bridge at port 10774.
- resonite-mcp: Virtual twin via OSC at port 10979.
- speech-mcp: spoken warnings at port 10909.
- LiveKit SFU: Windows service `LiveKitSFU` (native livekit-server, teleconference-mcp
  livekit.yaml) at port 15580.

The headset accesses the webapp over HTTPS through Tailscale Serve on the Goliath tailnet
hostname. The `webapp/start.ps1` launcher clears ports, waits for backend readiness with an
HTTP poll, and optionally enables Tailscale Serve.

## Run Modes

The server supports three modes:

- `--mode stdio` — FastMCP over stdio for Claude Desktop and IDE agents.
- `--mode http` — uvicorn HTTP serving the FastAPI app (REST + WebSocket + /mcp transport).
- `--mode dual` (default) — same as http; kept for clarity that both REST and MCP HTTP coexist.

The packaged Tauri app uses the dual-transport `run_server.py` entry point: it reads
`MCP_PORT`/`PORT` and `MCP_HOST` from the environment and falls back to stdio if no port is
set, which is what the PyInstaller backend executable uses.

## Webapp

The React webapp is the VR client, not a separate admin dashboard. It provides an XR session
controller, a robot selector, KPI cards for backend/teleop/webrtc/uptime, capability badges,
a tools page for REST mirrors, a logs page with ring-buffer query, a settings page with local
LLM glom-on (Ollama and LM Studio auto-detection), a fleet apps page, a help page, and a
floating chat window wired to the local LLM. The health dot uses exponential backoff polling
against `/api/v1/health`. The webapp persists LLM provider and model selections to
localStorage under `llm_provider` and `llm_model`.

## Common Failure Modes

- **Robot not moving**: yahboom-mcp is not running or the robot is powered off. Check port
  10892 and robot power. The health payload reports the yahboom API URL in use.
- **LiveKit no video**: the `LiveKitSFU` Windows service is not running, or the API key and
  secret do not match the SFU configuration. Verify the service (`Get-Service LiveKitSFU`)
  and port 15580. Teleconference-mcp logs at teleconference-mcp/logs/livekit.out.log.
- **WebXR not available**: the browser does not support `immersive-vr` or the page is served
  over HTTP on the headset. WebXR requires HTTPS, which is why Tailscale Serve is required.
- **WebSocket disconnects**: watchdog fires because frames stopped arriving; check network
  latency versus the watchdog interval and that the headset browser tab is active.
- **AUTO mode fails**: AUTO on base requires an active WebXR session unless confirm_bench is
  set, and the AUTO timer bounds the run.

This is the complete server capability reference. Use these tools and endpoints to supervise
teleoperation sessions, respond to hazards, manage authority, and verify video return.

## Supervisory Workflow Patterns

A supervising agent should follow these patterns when working with the server.

**Session intake.** Always begin a supervision task by calling `teleop_status()` to establish
baseline state: is a session active, which robot is selected, are any groups in AUTO, is the
estop latched, and how many frames have arrived. If video matters, follow with
`teleop_livekit_status()` to confirm the publisher is running before asking an operator to
rely on camera feed. Cross-check the robot catalog with `GET /api/v1/robots` so you know
which robot identifiers are valid for the session.

**Hazard response.** If `teleop_status()` reports an unexpected authority change, an AUTO run
that exceeds expectations, a watchdog latch, or any anomaly suggesting uncontrolled motion,
call `teleop_estop()` immediately. Do not attempt to diagnose first; the estop is the correct
first action because it zeroes drive on every actuator group and latches. After the hazard is
contained and you have confirmed it is safe, call `teleop_takeover()` to clear the latch and
return groups to the human operator.

**Authority management.** Use `teleop_set_mode(group=..., mode=...)` only when you have a
concrete reason to change who owns an actuator group. AUTO mode on the base group is bounded
by `TELEOP_AUTO_MAX_DURATION_S` and normally requires an active WebXR session; pass
`confirm_bench=True` only for bench testing. Prefer restoring DIRECT mode when a test is done
so the human retains control. Remember that any AUTO group is a potential runaway if its
producer misbehaves, so monitor `any_auto` in status and react to AUTO with extra scrutiny.

**Camera and video.** When a headset user reports no video, check `teleop_livekit_status()`
and look at `running`, `connected`, and `last_error`. If the publisher is stopped, start it
with `teleop_livekit_publisher_start()`. If `connected` is false, the LiveKit SFU service is
likely down; verify `Get-Service LiveKitSFU` on Goliath and that port 15580 is listening. The
MJPEG source falls back to snapshot polling when the camera stream fails, so `last_error`
plus `source` tell you which path is active.

**Runtime tuning.** If the robot moves too fast or too slowly, or the camera pan feels
over- or under-responsive, use `teleop_configure` to adjust `max_linear`, `max_angular`,
`pan_gain`, and `tilt_gain` at runtime. Confirm the new values in the response. Never exceed
safe limits for the environment; the defaults (0.3 m/s linear, 0.8 rad/s angular) are
conservative and should only be raised with explicit operator agreement.

**Shutdown.** To cleanly stop the server after work, call `teleop_shutdown(confirm=True)`,
which stops the publisher, disconnects all WebXR clients, and exits. Use this only when the
session is over or the host needs to be taken down; a running teleop session is safest left
alone.

## Session Context Summary

You have access to a WebXR teleoperation gateway for fleet robots. VR pose streams via
WebSocket at 30 Hz; MCP tools handle supervision, authority, and LiveKit video return.
Before starting work check `teleop_status()`, `teleop_livekit_status()`, and the robot
catalog. At end of work, return any AUTO group to DIRECT, verify estop state, and leave the
session safe for the next operator.
