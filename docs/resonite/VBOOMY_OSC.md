# Resonite OSC receivers for vBoomy teleop (ProtoFlux setup guide)

Enable **OSC Input** in Resonite: Settings → OSC → port **9000**.

Create a world with a wheeled **vBoomy** root (Rigidbody + collider). Attach ProtoFlux OSC receivers:

| OSC address | Args | Action |
|-------------|------|--------|
| `/resonite/vbot/spawn` | `robot_id, robot_type, x, y, z, scale` | Place/scale robot at origin |
| `/robot/{id}/reset` | `1` | Zero velocities, snap to spawn |
| `/robot/{id}/move` | `linear, angular` | Holonomic drive (m/s, rad/s) |
| `/robot/{id}/stop` | `1` | Zero cmd_vel |
| `/robot/{id}/head` | `yaw_deg, pitch_deg` | Pan/tilt head/camera slot |
| `/fleet/emergency_stop` | `1` | Stop all fleet robots |

Default robot id: **`vbot_yahboom_01`**.

## Drive math (ProtoFlux hint)

```
linear_x = linear
angular_y = angular
```

Apply to Rigidbody velocity each frame while move messages arrive (teleoperator sends ~30 Hz).

## First-person eyes

1. Add a **Camera** under the robot head slot.
2. Stream that camera to LiveKit (OBS Virtual Camera, Spout, or future resonite-mcp capture) → `TELEOP_LIVEKIT_MJPEG_URL`.
3. Pico Browser WebXR subscribes to room **`teleop-vboomy`** (see teleoperator `?robot=vboomy`).

For the proof loop, you can reuse the **physical Boomy MJPEG** stream until Resonite capture is wired — same HUD path, virtual drive.

## Quick test (no ProtoFlux)

Use **OSC Debug** or resonite-mcp to send:

```
/resonite/vbot/spawn  vbot_yahboom_01 yahboom 0 0 0 1
/robot/vbot_yahboom_01/move  0.1 0.0
```

Then start teleoperator with `?robot=vboomy` and confirm robotics-mcp logs show matching OSC outbound.
