# LeRobot session recording (M4)

Teleoperator-mcp logs every WebXR teleop session as **JSONL episodes** under `data/teleop_recordings/` (configurable via `TELEOP_RECORDING_DIR`).

## Layout

```
data/teleop_recordings/
  meta/
    info.json          # LeRobot v2.1-style feature schema (once)
    episodes.jsonl     # one row per finished session
  data/
    episode_000000/
      session.json     # session metadata
      frames.jsonl     # one row per pose frame
      summary.json     # frame count, duration
```

## Frame schema

Each `frames.jsonl` row includes:

| Field | Description |
|-------|-------------|
| `observation.state` | `[linear, angular, linear_y, pan, tilt]` sent to robot |
| `action` | Same vector (teleop imitation target) |
| `observation.head.*` | Head yaw/pitch/roll from WebXR |
| `observation.controller.*` | Trigger + stick axes |
| `authority` | Per-group DIRECT/AUTO state |
| `sources` | Which producer won each group |

Heartbeats, estop, and takeover messages are **not** logged as frames.

## Enable / disable

```env
TELEOP_RECORDING_ENABLED=1
TELEOP_RECORDING_DIR=data/teleop_recordings
TELEOP_RECORDING_FPS=30
```

Recording starts when a WebSocket session connects (`/ws/teleop?robot=boomy`) and finalizes on disconnect.

## Status

`teleop_status` MCP tool and `GET /api/v1/health` include a `recording` block (active session, frame count, episode path).

## Parquet export + video (later)

Full LeRobot parquet with synced video is **not** in JSONL yet. When M5 video is stable, link episode timestamps to LiveKit egress or frame IDs. See [LIVEKIT.md](LIVEKIT.md) § Recording.

## Related docs

- [ARCHITECTURE.md](ARCHITECTURE.md) — control vs video pipes
- [LIVEKIT.md](LIVEKIT.md) — video setup and troubleshooting
