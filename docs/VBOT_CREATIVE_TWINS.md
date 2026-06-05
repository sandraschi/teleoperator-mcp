# Creative vBots — Mechazilla, kaiju, Hollywood, any mesh

Resonite is the **fiction layer** of the fleet. Physical robots are scarce and expensive; virtual robots are unlimited. The teleoperator stack does not care whether the mesh is a Yahboom Raspbot or a Godzilla-scale Mechazilla — **one OSC contract, one recording schema, one LeRobot export**.

## Design principle

| Layer | Fixed | Swappable |
|-------|-------|-----------|
| Teleoperator | WebXR producer, arbiter, JSONL/parquet | `?robot=` adapter id |
| robotics-mcp | OSC addresses, vbot registry | `robot_type`, scale, metadata |
| Resonite | Receiver graph (move/head/spawn) | Mesh, scale, world, VFX |
| LeRobot | `observation.state` / `action` vectors | Curate by `robot_id` in meta |

## Registered creative types

| `robot_type` | Example id | Default scale | Notes |
|--------------|--------------|---------------|-------|
| `yahboom` | `vbot_yahboom_01` | 1.0 | vBoomy training twin |
| `mechazilla` | `vbot_mechazilla_01` | 2.5 | Tesla-style kitbash; IRL toy optional |
| `bumi` | `vbot_bumi_01` | 1.0 | Humanoid (rig TBD) |
| `custom` | `vbot_godzilla_01` | **50+** | Kaiju — Resonite handles huge avatars |

Add more types in `robotics-mcp` `SUPPORTED_ROBOT_TYPES` + `resonite-mcp` `VBOT_ROBOT_TYPES` — no teleoperator code change if OSC contract unchanged.

## Mechazilla specifically

Good first **creative** vBot because:

- **Holonomic base** maps cleanly to existing `/move` (same as Boomy).
- **Scale drama** — default spawn scale 2.5; crank to building-sized in Resonite for demos.
- **IRL punchline** — the toy exists; sim-to-real joke becomes sim-to-toy later.
- **Paper narrative** — “same embodied VR teleop pipeline for utilitarian and fictional morphologies.”

Register:

```powershell
$body = @{
  robot_id   = "vbot_mechazilla_01"
  robot_type = "mechazilla"
  platform   = "resonite"
  metadata   = @{ display_name = "vMechazilla"; scale = 2.5 }
} | ConvertTo-Json -Depth 5
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:12230/api/v1/robots -Body $body -ContentType application/json
```

Teleop today: `?robot=vboomy` with `TELEOP_VBOOMY_ROBOT_ID=vbot_mechazilla_01`. Dedicated `?robot=vmechazilla` adapter is optional sugar.

## Japan / Hollywood roster (examples)

Same pipeline for any rigged root with a head slot:

- **Tokusatsu** — Godzilla, Ultraman, Eva unit (non-humanoid gaits need new action schema later)
- **Mecha** — Gundam feet, Patlabor labor, Mechazilla
- **Western** — AT-ST, ED-209, Iron Giant
- **Cute** — Totoro on a Roomba base (holonomic cheat)

Start with **wheeled holonomic** critters; biped/quadruped vBots reuse Bumi/Go2 action schemas when those adapters land.

## Scale in Resonite

Resonite worlds tolerate ** enormous** avatars — city-block Godzilla is a feature, not a bug. Spawn OSC arg `scale` sets initial root scale; adjust in-world for spectacle. Physics: prefer kinematic / CharacterController for kaiju; Rigidbody for car-sized bots.

## Recording & training

Every session → JSONL → `export-lerobot.ps1` → parquet. Tag episodes with `robot_id` (`vbot_mechazilla_01`, etc.). Mix utilitarian and creative demos in one dataset or split by episode index for fine-tunes.

## Docs map

| Repo | Doc |
|------|-----|
| teleoperator-mcp | [VIRTUAL_TWINS.md](VIRTUAL_TWINS.md), [LEROBOT.md](LEROBOT.md) |
| robotics-mcp | CHANGELOG, vbot CRUD |
| resonite-mcp | [VBOT_OSC_RECEIVER.md](https://github.com/sandraschi/resonite-mcp/blob/master/docs/VBOT_OSC_RECEIVER.md) |
| mcp-central-docs | [projects/teleoperator-mcp/VIRTUAL_TWINS_FLEET.md](https://github.com/sandraschi/mcp-central-docs/blob/main/projects/teleoperator-mcp/VIRTUAL_TWINS_FLEET.md) |
