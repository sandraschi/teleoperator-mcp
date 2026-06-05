# Virtual twins — vBoomy / vBumi training before hardware

Train in **Resonite** with the same teleoperator cockpit used for physical robots. Recordings are compatible with the LeRobot JSONL path.

## Architecture

```
Pico WebXR (?robot=vboomy)
        │
        ▼
teleoperator-mcp :10901
        │  VboomyAdapter
        ▼
robotics-mcp :12230  →  OSC :9000  →  Resonite world (vBoomy rig)
        ▲
LiveKit ← camera (Boomy MJPEG or Resonite head cam)
```

| Robot param | Adapter | Sink | Video room |
|-------------|---------|------|------------|
| `boomy` | BoomyAdapter | yahboom-mcp REST | `teleop-boomy` |
| `vboomy` | VboomyAdapter | robotics-mcp → OSC | `teleop-vboomy` |
| `bumi` | BumiAdapter | bumi-mcp REST | `teleop-boomy` (until vBumi) |
| `vbumi` | (planned) | robotics-mcp → OSC | `teleop-vboomy` |
| `vmechazilla` | (same as vboomy + robot id) | robotics-mcp → OSC | `teleop-vboomy` |

Creative vBots share one OSC contract — swap mesh/scale in Resonite (`mechazilla` type, scale 2.5). Register with `robot_type=mechazilla`.

## vBoomy proof loop

### 1. Prerequisites

- Resonite running, OSC input on port **9000**
- ProtoFlux receivers per [resonite/VBOOMY_OSC.md](resonite/VBOOMY_OSC.md)
- robotics-mcp HTTP: `http://127.0.0.1:12230`
- teleoperator stack (backend + webapp)

### 2. Register virtual robot

```powershell
Set-Location D:\Dev\repos\teleoperator-mcp
.\scripts\register-vboomy.ps1
```

Or manually:

```powershell
$body = @{
  robot_id = "vbot_yahboom_01"
  robot_type = "yahboom"
  platform = "resonite"
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:12230/api/v1/robots -Body $body -ContentType application/json
```

Registration auto-sends `/resonite/vbot/spawn` OSC.

### 3. Teleop

Open Pico Browser (Tailscale HTTPS) → **Enter VR** with `?robot=vboomy` on the webapp URL.

Or local: `http://127.0.0.1:10900/#/?robot=vboomy`

### 4. Verify

- robotics-mcp logs: `OSC → 127.0.0.1:9000 /robot/vbot_yahboom_01/move ...`
- Resonite: robot moves with right stick + trigger
- Head yaw/pitch → `/robot/.../head`
- LeRobot JSONL in `data/teleop_recordings/` on session connect

## Why this matters (paper angle)

- **Same producer/arbiter/recording** for virtual and physical — sim-to-real without schema churn
- **Embodied VR teleop** with first-person video return (LiveKit) — not desktop joystick
- **Fleet MCP composition** — teleoperator + robotics + resonite, not monolithic sim
- **Progression**: vBoomy (wheeled) → vBumi (biped) → rBumi with adapter swap only

## Next: vBumi

Clone vBoomy pattern with humanoid OSC schema + `VbumiAdapter` when Bumi mesh exists in Resonite. See [MANIP_AND_HANDS.md](MANIP_AND_HANDS.md) for hand tracking tiers.
