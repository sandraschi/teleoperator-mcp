# Controller-Swap Weekend Guide — wheeled dual-arm (T4.3)

The plan-of-record option to buy a sealed "demo toy" robot, remove the stock controller,
and drive the actuators directly through the fleet stack. This is a **weekend project only
on a wheeled base** — see `docs/DUAL_MODE_ARCHITECTURE.md` §5 for why a biped swap is a
research project, not a weekend.

> **Warranty + ToS note (accepted):** ripping out the vendor controller voids warranty and
> almost certainly the ToS. The real consequence is **safety ownership**: you inherit
> whatever the stock firmware was doing.

## Why wheeled works

On a wheeled platform there is **no balance policy to reimplement**. You command wheel
motors + arm joints over CAN / serial / EtherCAT and you are done. Worst case on a wheeled
base is it stops or drifts — it cannot fall.

## What you need

- The robot (Unitree R1-A5-D or similar wheeled dual-arm).
- A Raspberry Pi (or Jetson) as the replacement controller running teleoperator-mcp.
- A CAN adapter (e.g. `canable` / MCP2515) or the robot's documented motor bus.
- Multimeter + a safe bench setup with the wheels off the ground for the first test.

## Weekend plan

### Day 1 — inventory and bench

1. Document every actuator group: motor IDs, joint limits, encoder directions.
2. Back up the stock firmware/controller before touching anything (you may want it back).
3. Bench the base first: command wheel motors directly, verify direction + scale.
4. Wire the Pi/Jetson as the new controller; keep the robot on blocks.

### Day 2 — bring it up under the arbiter

1. Implement the adapter in `src/teleoperator_mcp/adapters/` (see `base.py` + `boomy.py`).
   Capability descriptor: `hand_type="gripper"`, `balance_risk=false`.
2. Register it in `registry.py` — the VLA Fleet Control Tower picks it up automatically.
3. First motion: `teleop_estop` from MCP, then slow `teleop_set_gaze`-style single joints.
4. Full `ProducerCommand` drive under DIRECT authority, then AUTO via the waypoint producer.

### Day 3 — handoff + the VLA branch

1. Exercise AUTO -> squeeze takeover -> AUTO under the arbiter. Confirm no lurch.
2. `teleop_task_dispatch(goal)` now resolves manipulation goals (a `manip` group exists).
3. Wire the out-of-process VLA producer (vla-mcp / WALL-OSS on the 4090) as the `vla`
   producer; the arbiter's `VLA_ID` owner routes its commands.
4. Run the fake-VLA harness first (`tests/test_tier12.py`) so the contract is proven before
   real policy weights are in the loop.

## Safety gates

- Keep the robot on blocks for the entire weekend until the watchdog + estop are proven.
- `TELEOP_REQUIRE_CLAIM=1` stays on — the operator claim gate is your identity layer.
- AUTO remains time-bounded and WebXR-gated by default.
- Do the controller swap with the robot **unplugged** and a second person present for the
  first power-on.
