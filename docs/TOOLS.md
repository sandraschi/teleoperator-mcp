# Tools

Complete reference for the MCP tools, REST endpoints, resources, prompts, and the WebSocket
protocol exposed by teleoperator-mcp.

## MCP tools

All tools return `{success, message, ...}`. Annotations: `[RO]` read-only, `[M]` mutating,
`[D]` destructive.

| Tool | Ann | Purpose | Key args |
|------|-----|---------|----------|
| teleop_status | RO | Full session snapshot (frames, robot, authority, estop, watchdog) | — |
| teleop_configure | M | Runtime gains + robot API URL | max_linear, max_angular, pan_gain, tilt_gain, yahboom_api_url |
| teleop_estop | D | Hard stop all groups, latch estop | — |
| teleop_set_mode | M | Set group authority DIRECT/AUTO | group, mode, confirm_bench |
| teleop_takeover | M | Human reclaims groups, clears estop | group (optional) |
| teleop_set_gaze | M | Absolute pan/tilt (0-180 deg) | pan, tilt |
| teleop_gaze_center | M | Center camera servos | — |
| teleop_livekit_status | RO | LiveKit video return status | — |
| teleop_livekit_publisher_start | M | Start MJPEG->LiveKit publisher | — |
| teleop_livekit_publisher_stop | M | Stop publisher | — |
| show_teleop_status_card | RO | Prefab App status card | — |
| teleop_voice_command | M | Execute speech-mcp STT command (estop/takeover/mode/gaze/video) | transcript |
| teleop_task_dispatch | M | Dispatch a language goal to the AUTO producer (waypoint/VLA) | goal |
| teleop_shutdown | D | Graceful shutdown | confirm (must be true) |

### teleop_status

Returns: `success`, `message`, `active`, `robot`, `active_robot`, `robots`, `recording`,
`robot_id`, `display_name`, `frames_in`, `last_frame_at`, `uptime_s`, `client`,
`watchdog_latched`, `estop_count`, `auto_elapsed_s`, `authority` (per-group `mode`/`owner`),
`groups_available`, `any_auto`, `yahboom_api`, `watchdog_ms`.

### teleop_configure

Returns the new effective values: `max_linear`, `max_angular`, `pan_gain`, `tilt_gain`,
`yahboom_api_url`.

### teleop_estop

Returns `estop_count` and `estop_latched`. Zeroes drive on all groups.

### teleop_set_mode

Valid groups: `base`, `gaze`, `manip`. Valid modes: `DIRECT`, `AUTO`. AUTO on base requires
an active WebXR session unless `confirm_bench=true`. Returns group, mode, owner,
confirm_bench.

### teleop_takeover

`group` optional; omit to reclaim all. Clears the estop latch. Returns `takeover` list and
`estop_latched`.

### teleop_set_gaze / teleop_gaze_center

Pan/tilt in degrees, 0-180, center ~90. Returns applied pan/tilt.

### teleop_livekit_status

Returns `config` plus publisher status: `enabled`, `running`, `connected`, `room`,
`identity`, `frames_published`, `last_frame_at`, `last_error`, `source`, `width`, `height`,
`mjpeg_url`, `livekit_url`.

### show_teleop_status_card

Renders a PrefabApp card (fallback dict if prefab_ui unavailable).

### teleop_voice_command

Executes a voice command from speech-mcp STT. Keyword-rule dispatch (no LLM): emergency
stop, take over, center camera, look left/right/up/down, start/stop video, set base/gaze to
AUTO/DIRECT, status. Returns `action` and the underlying tool `result`.

### teleop_shutdown

Requires `confirm=true`. Stops publisher, disconnects clients, exits.

## Resources

| URI | Description |
|-----|-------------|
| teleop://status | Pollable text status block (active, frames, robot, webxr, mode, api) |

## Prompts

| Prompt | Params | Purpose |
|--------|--------|---------|
| teleop_help | topic (overview/estop/livekit) | Supervisor guidance for session, estop, video |

## REST endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/health | Liveness + teleop + LiveKit status |
| GET | /api/v1/diagnostics | Tool list, system info, errors (smoke tests) |
| GET | /api/capabilities | Runtime tool surface / features / inventory |
| GET | /api/logs | Ring-buffer query (limit, offset, level, kind, search, sort, after_id) |
| GET | /api/logs/stats | Buffer stats |
| GET | /api/logs/export | Export JSON/CSV |
| DELETE | /api/logs | Clear buffer |
| GET | /api/v1/robots | Robot adapter catalog |
| GET | /api/v1/livekit/config | Public LiveKit connection info |
| POST | /api/v1/livekit/token | Subscribe JWT `{identity, room?, name?}` |
| GET | /api/v1/livekit/status | Publisher status |
| GET | /api/v1/livekit/egress | Egress sink status (video frames recorded into episodes) |
| POST | /api/v1/livekit/publisher/start | Start publisher |
| POST | /api/v1/livekit/publisher/stop | Stop publisher |
| POST | /api/v1/teleop/estop | REST mirror of teleop_estop |
| POST | /api/v1/teleop/takeover | REST mirror of teleop_takeover |
| POST | /api/v1/teleop/gaze | REST mirror of teleop_set_gaze (pan, tilt) |
| POST | /api/v1/teleop/gaze/center | REST mirror of teleop_gaze_center |
| POST | /api/v1/teleop/voice | REST mirror of teleop_voice_command (STT transcript body) |
| POST | /api/v1/teleop/task | Dispatch a language goal to the AUTO producer |
| POST | /api/v1/session/claim | Claim a robot for an operator — returns WS token |
| POST | /api/v1/session/release | Release a claim by token |
| GET | /api/v1/session/claims | List active robot claims |
| GET | /api/v1/supervision | Multi-robot supervision view |
| GET | /api/v1/episodes | List recorded episodes |
| GET | /api/v1/episodes/{idx} | One episode including frames |
| POST | /api/v1/episodes/{idx}/curate | Attach keep/reject/uncertain label + note |
| GET | /api/v1/episodes/{idx}/image/{frame} | Serve one egress frame JPEG (path-traversal guarded) |
| POST | /api/v1/teleop/set_mode | REST mirror of teleop_set_mode (group, mode, confirm_bench) |
| POST | /api/v1/recording/export | Export JSONL to LeRobot parquet |
| POST | /api/shutdown | Graceful shutdown (confirm=true) |
| GET | /api/llm/providers | Local LLM provider discovery (Ollama) |
| POST | /api/llm/chat | Local LLM chat completion |
| GET | /docs | FastAPI Swagger UI |
| WS | /ws/teleop | Pose stream (?robot= param) |
| | /mcp | FastMCP HTTP transport |

## WebSocket protocol

`/ws/teleop?robot=boomy` accepts JSON pose frames. The server acks frames, updates session
stats, maps pose to robot commands, and watches the watchdog. See
[docs/ARCHITECTURE.md](ARCHITECTURE.md) and `scripts/ws-integration-harness.py`.

## Quick examples

```powershell
# Status
Invoke-RestMethod http://127.0.0.1:10901/api/v1/health

# E-stop
Invoke-RestMethod -Method Post http://127.0.0.1:10901/api/v1/teleop/estop

# Set gaze
Invoke-RestMethod -Method Post "http://127.0.0.1:10901/api/v1/teleop/gaze?pan=90&tilt=90"

# Diagnostics
Invoke-RestMethod http://127.0.0.1:10901/api/v1/diagnostics

# Logs
Invoke-RestMethod "http://127.0.0.1:10901/api/logs?limit=20"
```
