# Arms, hands, and Pico tracking tiers

How teleoperator-mcp maps human input to Bumi arms — without extra hardware first, with optional Pico add-ons later.

## Current (v0) — controllers + head

| Input | Bumi output | Status |
|-------|-------------|--------|
| Right stick + trigger (deadman) | `POST /api/v1/control/walk` | ✅ `BumiAdapter` |
| Head yaw/pitch | `POST /api/v1/control/head` | ✅ |
| Squeeze (either hand) | Takeover + coarse grip hint | ✅ partial |
| E-stop | `POST /api/v1/control/estop` | ✅ |

Use **`/ws/teleop?robot=bumi`** with `TELEOP_BUMI_API_URL=http://127.0.0.1:10774`.

## Tier 1 — WebXR hand tracking (no extra hardware)

**Pico 4 / Quest** expose **26-joint hand skeletons** via WebXR when the session requests `optionalFeatures: ["hand-tracking"]`.

| Pros | Cons |
|------|------|
| Free, already in headset | No finger force feedback |
| Good for reach + grasp intent | Occlusion when hands leave FOV |
| Works over Tailscale HTTPS | Mapping to Bumi grippers needs calibration |

**Plan**

1. Extend `PoseFrame` with optional `hands.left` / `hands.right` (wrist + key joints).
2. Enable hand-tracking in `xr-session.ts` behind a Settings flag.
3. `HumanPoseProducer._manip_from_hands()` → inverse kinematics or vendor retarget (Noetix SDK).
4. Record hands in LeRobot JSONL for imitation learning.

Meta and Pico both implement the same WebXR hand profile — one code path.

## Tier 2 — Pico Motion Tracker add-ons (body)

Pico sells **SW/MW motion trackers** (waist + feet / full body) for **body pose** without mocap suit cost.

| Use on Bumi | Value |
|-------------|--------|
| Operator torso lean → balance hint | Safer legged teleop |
| Foot intent (weight shift) | Future gait assist |
| Not a substitute for Bumi arm encoders | Robot still needs joint feedback |

**Plan:** optional `body` block on pose frame; arbiter uses it for **walk speed scaling** and logging only until validated with physical bot.

## Tier 3 — Robot-side encoders (always required for real grasp)

Bumi’s **21 DOF** includes arms and hands. Teleop sends *intent*; closed loop needs:

- `/joint_states` from rosbridge (already in bumi-mcp telemetry)
- Vendor grasp commands when Noetix documents them

## Recommended buy order

1. **Ship Bumi EDU** — validate walk/head/estop on hardware.
2. **Try Tier 1 hand tracking** in Pico Browser — zero cost, decide if grip quality is enough.
3. **Buy Pico body trackers** only if legged walk teleop feels unstable without operator body cueing (~fair-priced add-on).
4. Skip external mocap gloves unless Tier 1 fails for your grasp tasks.

## Safety

- **`manip` group** stays **DIRECT-only** (human authority) when enabled; no AUTO on arms.
- Enable arm routing only after `BUMI_ALLOW_MOTION=1` and harnessed stand tests.
- Grip from controller squeeze is **binary hint** until hand skeleton is live.
