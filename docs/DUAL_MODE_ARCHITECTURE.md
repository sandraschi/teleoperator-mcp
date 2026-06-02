# Dual-Mode Teleoperation + Telesupervision

**Status:** Design note (for review) - 2026-06-02
**Relationship to PRD:** Extends `docs/PRD.md`. The PRD describes v1 direct teleop. This note describes the larger arc (direct teleop <-> autonomy, operator becomes telesupervisor) and the hardware ladder we intend to climb. Nothing here changes shipped v1 behaviour yet; it defines the target the v1 code should be refactored toward.
**Audience:** Cursor / reviewers. Comment inline. Open questions are collected in section 9.

---

## 1. The decision, in one paragraph

`teleoperator-mcp` becomes a **two-mode** gateway with a sliding-authority layer between them. Mode A is **direct teleop** (human pose -> robot, what v1 already does). Mode B is **autonomy** (a policy drives; the human watches and can veto or retask). The human is the same person in both: in Mode B they are a **telesupervisor**, not a driver. The piece that makes this tractable is an **arbiter** that owns robot authority and accepts commands from N interchangeable **producers** (the human pose-mapper, a nav/gait controller, a manipulation VLA). Authority is held **per actuator group**, not globally, so a human can drive the base while a policy runs the arms, or vice versa. We validate the entire software spine on the **carbot (Boomy)** first, then move up to a **wheeled dual-arm** platform for the manipulation handoff, and only touch a **biped** if and when we specifically want legged-locomotion autonomy.

---

## 2. What changed our read of WALL-OSS

WALL-OSS is a **manipulation** foundation model, not a locomotion one. X Square Robot's explicit thesis is that the field over-indexes on bipedal locomotion and that the real bottleneck is generalized manipulation with hands and fingers. WALL-OSS-0.5 (open-sourced 2026-05-28, 4B params, weights + training code + recipes) is a VLA for real-robot manipulation, deployable zero-shot as a prior for downstream fine-tuning. It runs comfortably on the 4090 via LeRobot / WallX.

Consequence: in Mode B, **WALL-OSS owns the task/manipulation layer once the robot is in position. It does not walk anything.** Gait stays with the platform's own RL controller. This single fact reshapes the hardware ladder (section 6), because a manipulation brain needs something to manipulate with.

Unitree's **UnifoLM-VLA-0** (Qwen2.5-VL-7B base, ~12 task categories, open on GitHub) is a second open manipulation VLA, native to the Unitree ecosystem. The arbiter's producer interface must therefore be **model-agnostic**: WALL-OSS if we stay platform-neutral, UnifoLM if we stay in Unitree's stack. Do not hardcode WALL-OSS.

---

## 3. Arbiter architecture

```
                 +-----------------------------+
   producers --> |          ARBITER            | --> sink (robot adapter)
                 |  authority vector per group |
                 +-----------------------------+
   human pose-mapper  ----\
   nav / gait controller  ---->  arbiter decides, per group, who is driving
   manipulation VLA   ----/
```

- **One arbiter, one sink, N producers.** `teleoperator-mcp` owns the arbiter and the single actuator sink (the robot adapter, section 5). Producers emit commands in a common schema; the arbiter resolves who owns each actuator group this tick.
- **Authority is a vector, not a scalar.** Groups: `base` (locomotion/drive), `manip` (arms/hands), `gaze` (head/PTZ). A global DIRECT/AUTO flag cannot express "human drives base, policy scans with head" - which is the interesting regime - so authority is held independently per group.
- **The MCP surface IS the telesupervisor interface.** Supervisor verbs over `/mcp` (first cut: **hard switching only** — DIRECT or AUTO per group; SHARED blending is deferred):
  - `teleop_set_mode(group, mode)` - set DIRECT or AUTO on one actuator group
  - `teleop_task_dispatch(goal)` - hand a language goal to the active manipulation producer (WALL-OSS / UnifoLM)
  - `teleop_takeover(group?)` - human reclaims authority immediately
  - `teleop_estop` - hard stop, all groups, all producers (the veto; see safety)
  - `teleop_status` - already exists, extend with per-group authority + active producer
- **The VR client's role bifurcates.** It stops being only a continuous pose source. It becomes (a) presence + monitoring (you are *in* the robot, watching autonomy work) and (b) an **instant physical takeover device**: grab the controllers, squeeze = reclaim. The continuous-pose path is still there for Mode A; in Mode B the same loop is dormant until takeover.
- **Bumpless handoff is the actual hard problem.** Sliding autonomy's failure point is the authority-switch transient.
  - On **takeover**: seed the human command with the producer's current output so nothing lurches at the switch.
  - On **hand-back**: the autonomy producer must re-plan from current state, never resume a stale plan.
  - The existing watchdog + e-stop is the floor. Takeover arbitration is the ceiling.

---

## 4. Producer + sink contract (sketch)

A **producer** emits, per tick, a partial command keyed by actuator group:

```
ProducerCommand = {
  producer_id: str,
  groups: {
    "base":  { linear, angular, linear_y } | null,
    "manip": { <platform-specific> }       | null,
    "gaze":  { pan, tilt }                  | null,
  },
  confidence?: float,    # optional, for SHARED blending later
}
```

The **arbiter** holds `authority: { base: producer_id, manip: producer_id, gaze: producer_id }` and forwards only the owning producer's command for each group to the sink. The **sink** is the robot adapter (section 5). Producers that try to command a group they do not own are ignored, not errored - this keeps a backgrounded autonomy producer alive and warm for fast hand-back.

This is the refactor target for the current code: today `ws/handler.py` calls `BoomyMapper` directly (single producer, single implicit sink). The mapper becomes *one producer*; the arbiter sits between producers and the adapter.

---

## 5. Robot adapter + capability descriptor

The abstraction that turns "Boomy -> wheeled dual-arm -> biped" into a driver swap instead of three rewrites.

Each platform implements an adapter exposing the command groups it physically has, plus a **capability descriptor**:

```
RobotCapabilities = {
  has_base:        bool,   # can it translate/rotate?
  has_legs:        bool,   # bipedal locomotion?
  balance_risk:    bool,   # can it fall over if control glitches?
  has_arms:        bool,
  hand_type:       "none" | "gripper" | "dexterous",
  programmable:    bool,   # can we command actuators directly at all?
}
```

The arbiter **gates authority by capability**: no `manip` group is exposed on Boomy (no arms); no `teleop_task_dispatch` to a dexterous VLA on a gripper-only torso; takeover semantics get stricter when `balance_risk` is true. The MCP surface and arbiter stay byte-identical across robots. Only the adapter and the descriptor change.

---

## 6. Hardware ladder

Each rung proves different things. They are not strictly sequential; they are orthogonal risk reductions, and the order should follow what we actually want to de-risk for the **manipulation** endgame.

| Rung | Platform | Proves | Does NOT prove | Notes |
|------|----------|--------|----------------|-------|
| 0 | **Boomy** (Yahboom Raspbot v2, wheeled) | Entire software spine: arbiter, per-group authority, handoff, takeover, watchdog/e-stop, MCP supervisor surface, LeRobot logging, WebXR loop, latency | Anything legged; anything manipulation | Zero physical risk. Already in hand. |
| 1 | **Wheeled dual-arm** (Unitree R1-A5-D / A7-D) | Manipulation handoff + telesupervised VLA, on a base that **cannot fall over** | Legged locomotion / balance handoff | Best fit for the WALL-OSS/UnifoLM endgame. See SKU notes. |
| 2 (optional) | **Biped** (Bumi, full R1) | Locomotion-authority handoff on legs; the balance/fall failure mode | Manipulation (Bumi has no hands) | Only if we specifically want legged autonomy. Higher risk, lower manipulation payoff. |

### Why wheeled-before-biped (and maybe wheeled-instead-of-biped)

Going legged -> wheeled is not just losing the cartwheels (spectacular, practically useless, and arguably a threat vector near people). It removes the single hardest and most dangerous part of the stack: **the balance controller.** On a biped, autonomy-handoff failure can mean a fall; on a wheeled base the worst case is it stops or drifts. For a manipulation research program, the legs are pure liability with no upside. The wheeled dual-arm torso gives a real VLA target with none of the balance risk.

### SKU traps (do not buy the wrong R1)

- **R1 Air ($4,900) and R1 standard ($5,900) are closed systems.** Only the **EDU** edition supports secondary development, and EDU starts around $10-12K. The cheap R1 is a sealed appliance you cannot program.
- **Base R1 has no functional hands** (fist-style, non-functional in most demos). Dexterous hands appear only on Pro configs ($20-35K).
- **R1-A5 / A7** (announced 2026-05-01) is the relevant product: dual-arm torso, fittable with 2-finger grippers or 3/5-finger dexterous hands, fixed or wheeled base, binocular vision (1280x720@30), optional Jetson Orin. **Base $4,290 is the torso bare**; hands + compute + wheeled base push it toward EDU money, not Pro money. The "-D" wheeled variants (~30-32 kg) are explicitly aimed at researchers training embodied-AI models. A7 has longer arms and +4 DOF over A5.

### The controller-swap path (accepted)

Plan of record includes the option to buy a sealed "demo toy", remove the stock controller, drop in a Raspberry Pi (or Jetson), and drive the actuators directly through our stack over the motor bus. Honest engineering notes:

- This **voids warranty and almost certainly the ToS.** Noted and accepted. Many people will do the same; expect a community to form around exactly this.
- The real consequence is not legal, it is **safety ownership**: ripping out the vendor controller means you inherit whatever that firmware was doing. **On a biped that includes the balance/locomotion RL policy - the hard part - and you are now responsible for keeping it upright.** That is a serious undertaking and another reason to prefer wheeled.
- **On a wheeled platform the controller-swap is genuinely tractable**: there is no balance policy to reimplement. You command wheel motors + arm joints over CAN / serial / EtherCAT and you are done. The wheeled pivot and the controller-swap reinforce each other - wheeled is the platform class where "rip the controller, run our stack" is a weekend's risk, not a research project.

---

## 7. Honest boundaries

- Boomy de-risks the control plane to ~100% and the physical humanoid risk to ~0%. Do not be surprised when rung 1/2 surface problems Boomy could not.
- WALL-OSS / UnifoLM are manipulation policies. Until a rung-1 platform exists, Mode B autonomy is **nav/gait only** (Boomy: yahboom autonomy / ROS 2 nav). The manipulation handoff is unproven until there is something with hands on the bench.
- SHARED mode (blended human + policy authority within one group, via confidence) is **not** in scope for the first arbiter cut. First cut is hard switching: DIRECT or AUTO per group, with takeover. Blending is a later milestone.

---

## 8. Data flywheel

Log every Mode A teleop session as a **LeRobot-format dataset** from day one (pose + robot state + video + group commands). This is not housekeeping; it is the point. WALL-OSS-0.5's stated purpose is being a strong prior for downstream adaptation, and teleop episodes are exactly that fine-tuning corpus. The loop: teleop -> demos -> fine-tune VLA -> autonomy -> telesupervise + correct -> more demos. Recording must land before rung 1, ideally during Boomy work even though Boomy demos only teach base motion.

---

## 9. Open questions (Cursor: comment here)

1. **Arbiter location.** In `teleoperator-mcp` process, or a separate `arbiter` module the WS handler and MCP tools both import? Leaning: in-process module, single source of authority state, both surfaces mutate it.
2. **Producer transport.** Human pose-mapper is in-process. Are the VLA producers in-process (load WALL-OSS in the same Python process) or out-of-process (VLA as its own service, producer is a client)? Latency vs isolation tradeoff. Leaning out-of-process for the VLA so a policy crash cannot take down the safety/arbiter layer.
3. **Authority state in `teleop_status`.** Confirm the Prefab status card shape: per-group owner + active producers + mode. (Fleet standard wants a Prefab surface for status tools.)
4. **Takeover binding.** Squeeze = takeover-all is proposed. Do we want per-group takeover gestures, or is all-or-nothing fine for the first cut?
5. **Adapter for Boomy.** Wrap the existing `BoomyMapper` REST calls behind the adapter interface, or rewrite against the yahboom ROS 2 layer directly? (PRD open item: confirm the yahboom REST contract is real first.)
6. **Bumi's place.** Given it has no hands, is rung 2 (Bumi) worth doing at all before a wheeled dual-arm, or does it become a pure "legged handoff" side-experiment decoupled from the manipulation line?

---

## 10. Rough sequence (AI-assisted, realistic)

1. Land v1 direct-teleop defects (configure-URL bug, `teleop_estop`, CORS allowlist, HUD redraw throttle) so the data plane is solid on real hardware. ~0.5-1 day.
2. Get Boomy driving from the Pico, prove pose path + safety stops + latency on hardware. ~1-2 days incl. hardware fiddling (HTTPS cert, Pico WebXR matrix).
3. Introduce adapter + capability descriptor; wrap `BoomyMapper` as a producer behind it. No behaviour change. ~1 day.
4. Introduce arbiter (hard switching, per-group, takeover, estop) with a nav-stub AUTO producer on Boomy. ~1-2 days.
5. LeRobot episode logging during teleop. ~1 day.
6. (Rung 1 hardware dependent) wheeled dual-arm adapter + VLA producer out-of-process. Estimate when hardware is on the bench.

---

## Sources (provenance, 2026-06-02)

- WALL-OSS / WALL-OSS-0.5: X-Square-Robot/wall-x (GitHub), HF LeRobot WALL-OSS docs, paper arXiv:2509.11766, PR Newswire 2026-05-28 release.
- UnifoLM-VLA-0: Unitree, Qwen2.5-VL-7B base, open on GitHub (per BotInfo G1 writeup).
- Noetix Bumi: $1,400 / ~9,998 CNY, 94 cm, 12 kg, 21 DOF (legs/hips/torso/arms), bipedal, no dexterous hands, education focus; delivery Apr-Jun 2026.
- Unitree R1: R1 Air $4,900 (20 DOF), R1 std $5,900 (26 DOF); R1/R1 Air closed, only EDU programmable (~$10-12K+); base lacks functional hands; Pro $20-35K dexterous.
- Unitree R1-A5/A7 (2026-05-01): dual-arm modular torso, grippers or 3/5-finger hands, fixed/wheeled base, binocular vision, optional Jetson Orin, base $4,290; CNX Software / Humanoids Daily.
