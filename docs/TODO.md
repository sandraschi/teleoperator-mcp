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
- [x] **Watchdog latch:** e-stop once when pose frames cease; heartbeats do **not** reset latch (2026-06-04); default watchdog **1000 ms**.
- [x] **Unicode-safety fix:** em-dash removed from `start.ps1`.

---

## Milestone 1 - Boomy hardware bring-up (~1-2 days, needs Boomy)

Prove the data plane on real hardware before adding anything on top.

- [x] Confirm the yahboom REST contract: `POST /api/v1/control/move` and `/api/v1/control/tool` `camera_set_pos` — verified 2026-06-02 (Boomy on Raspbot AP, `192.168.1.11`, ros + cmd_vel + video active).
- [x] **HTTPS doc:** [HTTPS.md](HTTPS.md). Deployed: Tailscale Serve -> `https://goliath.tailfab45.ts.net/`, Vite `allowedHosts` fixed.
- [ ] WebXR matrix on Pico 4 / Meta Quest. Checklist: [BRINGUP.md](BRINGUP.md) section 4.
- [ ] End-to-end: headset pose -> drive + PTZ on Boomy; deadman, watchdog, single-session. *(Bench: drive + PTZ verified 2026-06-02; headset sign-off pending Pico charge.)*
- [ ] Measure latency (motion-to-command).

**Acceptance:** Boomy drives from the Pico with trigger + stick; head moves PTZ; releasing trigger or dropping WS stops the robot within 300 ms.

---

## Milestone 2 - Robot adapter + capability descriptor (~1 day, no hardware)

The abstraction that makes the hardware ladder a driver swap.

- [x] Define types: `ProducerCommand`, `RobotCapabilities`, actuator groups (`src/teleoperator_mcp/types.py`).
- [x] `RobotAdapter` ABC + `BoomyAdapter` wrapping yahboom REST (`src/teleoperator_mcp/adapters/`).
- [x] `HumanPoseProducer` maps WebXR frames to `ProducerCommand`; WS handler uses adapter (no direct mapper calls).
- [x] Wire adapter selection by `?robot=` route (`boomy` live; `r1-a5-d` stub returns 4004).

---

## Milestone 3 - Arbiter + AUTO stub (~1-2 days, no hardware)

- [x] `arbiter/` module: per-group authority vector, hard switching (DIRECT / AUTO only; SHARED deferred), takeover, e-stop. Single source of authority state shared by the WS handler and MCP tools.
- [x] MCP tools: `teleop_set_mode(group, mode)`, `teleop_takeover(group?)`, extend `teleop_status` with per-group owner + active producer.
- [x] Bumpless handoff: on takeover, seed human command from the producer's current output; on hand-back, force re-plan from current state (`nav_stub.reset_plan()`).
- [x] Nav-stub AUTO producer on Boomy (slow forward + gentle sweep after 5s) to exercise switching with no real autonomy.
- [x] Authority gated by capability (no `manip` group on Boomy; stricter takeover when `balance_risk` — deferred until legged platform).
- [x] Squeeze in WebXR -> `takeover` WS message (M3); MCP `teleop_estop` remains hard stop.
- [x] AUTO safety: 10 s max duration, WebXR required (or `confirm_bench`), lower crawl speed, forward-only stub, spoken warnings via speech-mcp.

**Acceptance:** from Cursor, switch `base` to AUTO (Boomy drives to waypoint), squeeze in VR to take over instantly with no lurch, `teleop_estop` halts everything.

---

## Milestone 4 - Data flywheel (~1 day, no hardware)

- [x] Log every teleop session as **LeRobot-compatible JSONL** (pose + resolved commands + authority). See [LEROBOT.md](LEROBOT.md).
- [ ] Parquet export + video frames (depends on M5 LiveKit return path).
- [x] Boomy base-only demos are recorded to prove the pipeline before manipulation hardware exists.

---

## Milestone 5 - Video return v1.5 (~1-2 days, needs myconf)

- [x] Goliath-side publisher: yahboom MJPEG/snapshot → LiveKit track (`src/teleoperator_mcp/livekit/`).
- [x] Token + config REST; MCP `teleop_livekit_*` tools; webapp `livekit-client` subscribe → center plane.
- [x] Document in [LIVEKIT.md](LIVEKIT.md).
- [x] **SOTA webapp** — Iron Shell dashboard, `/logs`, `/tools`, fleet pages ([WEBAPP_STANDARDS](https://github.com/sandraschi/mcp-central-docs/blob/main/standards/WEBAPP_STANDARDS.md)).
- [ ] Encode path tuned (FFmpeg H.264 ingest optional; current path is I420 frame publish).
- [ ] Tailscale WSS + UDP bench on Pico; motion-to-photon latency measurement. *(2026-06-04: LiveKit STUN fixed on Goliath; publisher bench OK; Pico `VID` sign-off pending.)*
- [ ] Re-assess vestibular comfort with head-coupled PTZ + video lag (decouple if nauseating).

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
