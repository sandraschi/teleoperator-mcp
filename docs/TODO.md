# TODO / Plan

Concrete milestone plan. Timelines are **AI-assisted realistic** (days, not weeks) and assume single-developer pace on Goliath. Hardware-gated items have no date until the hardware is on the bench. Checkboxes track state; nothing here is marked done that is not actually done.

Source of truth for the *why*: [DUAL_MODE_ARCHITECTURE.md](DUAL_MODE_ARCHITECTURE.md). This file is the *what/when*.

---

## Milestone 0 - v0.1 defect fixes (~0.5-1 day, no hardware)

Make the direct-teleop path solid enough to put on a real robot.

- [x] **configure-URL bug:** `BoomyMapper.api_base` reads `settings.yahboom_api_url` per call (no stale cache).
- [x] **`teleop_estop` MCP tool:** hard stop via yahboom REST; `trigger_estop()` shared with WS handler.
- [x] **Bind squeeze -> immediate stop** in WebXR client (`sendEstop` on squeeze; blocks drive frames while held).
- [x] **CORS:** `TELEOP_CORS_ORIGINS` allowlist (no `*` + credentials).
- [x] **HUD redraw throttle:** diff rendered line; skip CanvasTexture upload when unchanged.
- [x] **WS reconnect/backoff** in `pose-stream.ts` (exponential backoff; `disconnect()` opts out).
- [x] **Watchdog latch:** e-stop once when frames cease; unlatch when frames/heartbeats resume; notify client `{watchdog:true}`.
- [x] **Unicode-safety fix:** em-dash removed from `start.ps1`.

---

## Milestone 1 - Boomy hardware bring-up (~1-2 days, needs Boomy)

Prove the data plane on real hardware before adding anything on top.

- [ ] Confirm the yahboom REST contract is real: `POST /api/v1/control/move` (linear/angular/linear_y) and `/api/v1/control/tool` `camera_set_pos`. PRD open item; adjust mapper if the deployed API differs.
- [ ] HTTPS for the webapp on 10900 (WebXR requirement). Decide Tailscale Serve vs self-signed; document in `docs/HTTPS.md`.
- [ ] Pico Browser WebXR feature-matrix test on hardware (immersive-vr, local-floor, gamepad axes/buttons).
- [ ] End-to-end: Pico pose -> drive + PTZ on Boomy; verify deadman, watchdog (<300 ms stop), single-session reject.
- [ ] Measure real latency (motion-to-command, and later motion-to-photon once video lands).

**Acceptance:** Boomy drives from the Pico with trigger + stick; head moves PTZ; releasing trigger or dropping WS stops the robot within 300 ms.

---

## Milestone 2 - Robot adapter + capability descriptor (~1 day, no hardware)

The abstraction that makes the hardware ladder a driver swap.

- [ ] Define `adapters/` interface: command groups (`base`, `manip`, `gaze`) + `RobotCapabilities` (`has_base`, `has_legs`, `balance_risk`, `has_arms`, `hand_type`, `programmable`).
- [ ] Implement `BoomyAdapter` wrapping the existing REST calls. No behaviour change.
- [ ] Make `BoomyMapper` emit a `ProducerCommand` keyed by group instead of calling the robot directly.

---

## Milestone 3 - Arbiter + AUTO stub (~1-2 days, no hardware)

- [ ] `arbiter/` module: per-group authority vector, hard switching (DIRECT / AUTO only; SHARED deferred), takeover, e-stop. Single source of authority state shared by the WS handler and MCP tools.
- [ ] MCP tools: `teleop_set_mode(group, mode)`, `teleop_takeover(group?)`, extend `teleop_status` with per-group owner + active producer.
- [ ] Bumpless handoff: on takeover, seed human command from the producer's current output; on hand-back, force re-plan from current state.
- [ ] Nav-stub AUTO producer on Boomy (drive to a saved waypoint) to exercise switching with no real autonomy.
- [ ] Authority gated by capability (no `manip` group on Boomy; stricter takeover when `balance_risk`).

**Acceptance:** from Cursor, switch `base` to AUTO (Boomy drives to waypoint), squeeze in VR to take over instantly with no lurch, `teleop_estop` halts everything.

---

## Milestone 4 - Data flywheel (~1 day, no hardware)

- [ ] Log every teleop session as a **LeRobot-format dataset** (pose + robot state + group commands + video frames where available).
- [ ] Even Boomy demos (base motion only) get recorded, to prove the pipeline before manipulation hardware exists.

---

## Milestone 5 - Video return v1.5 (~1-2 days, needs myconf)

- [ ] Encode on **Goliath**, not the Pi (Pi 5 has no hardware H.264 encoder). Boomy ships raw/MJPEG to Goliath; Goliath encodes and publishes to LiveKit room `teleop-boomy`.
- [ ] WebXR client subscribes to the LiveKit track, maps to the front plane (flat mono).
- [ ] Reuse myconf token endpoint pattern; document in `docs/LIVEKIT.md`.
- [ ] Re-measure motion-to-photon latency; assess vestibular comfort with head-coupled PTZ (may decouple in v1 if nauseating).

---

## Milestone 6 - Wheeled dual-arm rung (hardware-gated: R1-A5-D)

The manipulation handoff. No date until the platform is on the bench.

- [ ] `R1A5DAdapter`: `base` (wheels) + `manip` (arms + gripper) + `gaze` (head), capability `hand_type="gripper"`, `balance_risk=false`.
- [ ] VLA producer **out-of-process** (WALL-OSS or UnifoLM via LeRobot on the 4090); arbiter speaks to it as a client.
- [ ] `teleop_task_dispatch(goal)` -> language goal to the VLA producer.
- [ ] **v1 manipulation acceptance task: "open fridge, retrieve can."**
  - Target `hand_type = gripper` (opposed-thumb pinch). Dexterity not required.
  - Demo rig: block half the door magnet to cut break force, but keep enough hinge friction that the door stays put once cracked (a free-swinging door is a moving target).
  - Perception split: nav = coarse SLAM map + saved fridge waypoint (static world); grasp = live head-stereo policy finds handle + can (dynamic targets). Global map never carries the can.
  - Honest residual hard part: following the door's hinge arc while the wheeled base backs up and reorients. Verify R1-A5 arm reach + pull force + base coordination against real specs before committing the platform to this demo.

---

## Fleet-compliance backlog (non-blocking, fold in opportunistically)

- [ ] **Prefab UI:** `teleop_status` must return `ToolResult` + `PrefabApp` (status-tool mandate). `prefab-ui` is already a dependency.
- [ ] **Naked-PC install:** `Require-Command` in `start.ps1` (winget auto-install uv + Node), import smoke-test, health-timeout message; add `INSTALL.md`. Reference: `aiwatcher-mcp`.
- [ ] **Bun migration:** webapp uses npm; fleet standard is Bun (`bun install` / `bun run`, commit `bun.lock`). Vite stays the bundler.
- [ ] **Playwright e2e** (headless) for the webapp + README preview screenshot.
- [x] **Register ports** 10900/10901 in `mcp-central-docs/operations/WEBAPP_PORTS.md`.
- [ ] **`mcpb pack`** validation + pack for distribution (do not use init/publish).
- [ ] **`llms-full.txt`** to complete the required llms.txt pair.

---

## Open decisions (resolve before the milestone that needs them)

1. **Arbiter location:** in-process module shared by WS handler + MCP tools (leaning yes) vs separate service.
2. **VLA producer transport:** out-of-process (leaning yes, crash isolation) vs in-process (lower latency).
3. **Takeover granularity:** squeeze = take-over-all (proposed) vs per-group takeover gestures.
4. **Bumi's place:** given no hands, is rung 2 worth doing before the wheeled dual-arm, or is it a decoupled "legged handoff" side-experiment? (Most exposed item after the wheeled pivot.)
5. **Ops webapp vs VR client:** WEBAPP_SOTA_STANDARDS mandates Dashboard/Tools/Logs pages for MCP frontends; here the frontend is intentionally a VR client, not a dashboard. Decide whether a separate minimal ops webapp is warranted or the standard is waived for this server class.
6. **Boomy adapter target:** wrap existing REST vs go straight to the yahboom ROS 2 layer (depends on Milestone 1 contract check).
7. **SHARED mode:** confidence-blended human+policy authority is out of scope for the first arbiter cut (hard switching only). Schedule if/when needed.

---

## Sequencing note

Milestones 0 -> 5 are mostly hardware-light and can run now in order; 2 and 3 are the real architectural work and should not start until Milestone 1 proves the data plane on Boomy. Milestone 6 waits on hardware. Rough cumulative for 0-4 (the software spine, no waiting on parts): ~5-7 working days.
