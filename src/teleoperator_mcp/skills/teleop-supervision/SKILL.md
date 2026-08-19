---
name: teleop-supervision
description: Supervise a WebXR teleoperation session - check status, video return, authority, and respond to hazards.
---

# Teleoperator Session Supervision

You are supervising a WebXR teleoperation session on the fleet. A human operator may be
driving a physical robot (Boomy, Bumi) or a virtual twin (vboomy in Resonite) from a VR
headset. Your job is to monitor the session, respond to hazards, and manage authority.

## Before starting work

1. Check session state: `teleop_status()` - active, robot, frames_in, watchdog, estop, authority.
2. Check video return: `teleop_livekit_status()` - publisher running, connected, last_error.
3. Check the robot catalog: `GET /api/v1/robots`.

## During the session

- If the robot moves unexpectedly or anything looks unsafe: `teleop_estop()` immediately.
  It zeroes drive on all actuator groups and latches until `teleop_takeover()`.
- If a group is in AUTO and the operator wants it back: `teleop_set_mode(group=..., mode="DIRECT")`.
- If video is down: check `teleop_livekit_status()`; start with
  `teleop_livekit_publisher_start()` if the publisher is stopped.

## At end of work

- Return any AUTO group to DIRECT: `teleop_set_mode(group="base", mode="DIRECT")`.
- Verify the estop latch is clear unless a hazard persists.
- Leave the session in a safe state for the next operator.
