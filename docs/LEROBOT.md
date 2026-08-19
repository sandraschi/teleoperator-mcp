# LeRobot session recording and export (M4)

Teleoperator-mcp logs every WebXR teleop session as **JSONL episodes** under `data/teleop_recordings/` (configurable via `TELEOP_RECORDING_DIR`). Export to **LeRobot v2.1 parquet** for `lerobot-train`.

Works for **all robot adapters** — `boomy`, `bumi`, `vboomy`, future kaiju vbots — same frame schema; `robot_id` is stored per episode.

## Layout (JSONL capture)

```
data/teleop_recordings/
  meta/
    info.json          # feature schema (once)
    episodes.jsonl     # one row per finished session
  data/
    episode_000000/
      session.json
      frames.jsonl
      summary.json
      images/                    # egress sink: decoded video frames
        observation.image/
          000000.jpg
          000001.jpg
          ...
```

## Export layout (LeRobot parquet)

```
data/lerobot_export/
  meta/
    info.json
    episodes.jsonl
    tasks.jsonl
  data/
    chunk-000/
      episode_000000.parquet
      episode_000000/
        images/
          observation.image/
            000000.jpg
            ...
```

Parquet columns: `timestamp`, `frame_index`, `episode_index`, `index`, `task_index`, `observation.state`, `action`, head/controller floats, `observation.image.image` (when egress recorded frames), `next.done`.

## Video frames (LiveKit egress sink)

The **egress sink** closes the flywheel loop: while a teleop session is active, the LiveKit
publisher hands each decoded JPEG to `recording/egress.py`, which buffers it and matches it
to the nearest teleop frame (within `TELEOP_LIVEKIT_EGRESS_TOLERANCE_MS`). Matched frames
are saved under `images/observation.image/` and referenced by an `observation.image.image`
column (a dataset-relative path). The parquet exporter copies the images into the chunked
layout and sets `info.json` `video_path` when any frames were recorded.

| Env | Default | Meaning |
|-----|---------|---------|
| TELEOP_LIVEKIT_EGRESS_ENABLED | 1 | Record decoded video frames into episodes |
| TELEOP_LIVEKIT_EGRESS_TOLERANCE_MS | 300 | Max offset between a teleop frame and its video frame |
| TELEOP_LIVEKIT_EGRESS_INTERVAL | 2 | Capture every Nth decoded video frame |

A dataset without observation frames is a broken dataset — `scripts/publish-lerobot-hub.py`
refuses to publish one.

## Export

```powershell
Set-Location D:\Dev\repos\teleoperator-mcp
.\scripts\export-lerobot.ps1
.\scripts\export-lerobot.ps1 -InputDir data/teleop_recordings -OutputDir data/lerobot_export -Overwrite
```

Or HTTP:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:10901/api/v1/recording/export `
  -Body (@{ overwrite = $true } | ConvertTo-Json) -ContentType application/json
```

Or Python:

```powershell
py -m teleoperator_mcp.recording.export_lerobot --input data/teleop_recordings --output data/lerobot_export --overwrite
```

## Train (after export)

```powershell
pip install lerobot
lerobot-train --dataset.repo_id=local/teleop --dataset.root=data/lerobot_export
```

Use your policy config / WALL-OSS recipe as needed. Virtual-twin demos (vBoomy, Mechazilla) and physical Boomy episodes can live in one dataset — filter by `meta/episodes.jsonl` `robot_id` when curating.

## Frame schema (JSONL)

| Field | Description |
|-------|-------------|
| `observation.state` | `[linear, angular, linear_y, pan, tilt]` |
| `action` | Same vector (imitation target) |
| `observation.head.*` | WebXR head |
| `observation.controller.*` | Trigger + stick |
| `observation.image.image` | Egress frame path (when recorded) |
| `authority` / `sources` | Arbiter state |

## Enable / disable capture

```env
TELEOP_RECORDING_ENABLED=1
TELEOP_RECORDING_DIR=data/teleop_recordings
TELEOP_RECORDING_FPS=30
```

Recording starts on WebSocket connect (`/ws/teleop?robot=…`) and finalizes on disconnect.

## Status

`GET /api/v1/health` → `teleop.recording` block.

## Related

- [VIRTUAL_TWINS.md](VIRTUAL_TWINS.md) — Resonite vBots + same recording path
- [VBOT_CREATIVE_TWINS.md](VBOT_CREATIVE_TWINS.md) — Mechazilla, kaiju, scale
- [LIVEKIT.md](LIVEKIT.md) — video pipe + egress sink (frames into episodes)
