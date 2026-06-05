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
```

Parquet columns: `timestamp`, `frame_index`, `episode_index`, `index`, `task_index`, `observation.state`, `action`, head/controller floats, `next.done`.

Video is **not** embedded yet (M5: LiveKit egress sync). `meta/info.json` sets `"video_path": null`.

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
- [LIVEKIT.md](LIVEKIT.md) — video pipe (future parquet video sync)
