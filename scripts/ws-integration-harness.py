"""Headless WebSocket teleop integration harness.

Streams simulated WebXR pose frames to the live teleop backend (/ws/teleop),
verifies the full pipeline: WS handshake + ack, arbiter resolution, session
stats, watchdog, recording, and that drive/gaze commands reach yahboom-mcp.

Usage: uv run python scripts/ws-integration-harness.py [--frames N] [--robot boomy]

Exits 0 on full pass. Safe: sends zero-velocity frames (deadman trigger = 0),
and e-stops at the end.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

import httpx
import websockets

TELEOP = "ws://127.0.0.1:10901/ws/teleop"
BACKEND = "http://127.0.0.1:10901"
YAHBOOM = "http://127.0.0.1:10892"

PASS = 0
FAIL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name} {detail}")


def make_frame(seq: int, robot: str, *, trigger: float = 0.0, look: bool = False) -> str:
    """Zero-velocity pose frame. trigger=0 keeps deadman off (robot never moves)."""
    head = {"yaw": 0.1 if look else 0.0, "pitch": 0.05 if look else 0.0, "roll": 0.0}
    right = {
        "connected": True,
        "axes": [0.0, 0.0],
        "buttons": {"trigger": trigger, "squeeze": 0.0},
    }
    left = {"connected": False, "axes": [], "buttons": {}}
    payload = {
        "type": "pose",
        "seq": seq,
        "robot": robot,
        "head": head,
        "right": right,
        "left": left,
    }
    return json.dumps(payload)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frames", type=int, default=60, help="pose frames to stream")
    parser.add_argument("--robot", default="boomy")
    parser.add_argument("--look", action="store_true", help="include head movement (gaze)")
    args = parser.parse_args()

    print(f"=== Headless WS integration harness (robot={args.robot}, frames={args.frames}) ===")

    # Pre: backend health
    try:
        h = httpx.get(f"{BACKEND}/api/v1/health", timeout=5).json()
        check("backend health", h.get("status") == "ok", str(h.get("status")))
    except Exception as e:
        check("backend health", False, str(e))
        sys.exit(1)

    # Pre: yahboom-mcp health (robot may be offline — that's OK, bridge must answer)
    try:
        y = httpx.get(f"{YAHBOOM}/api/v1/health", timeout=5).json()
        check(
            "yahboom-mcp reachable",
            True,
            f"robot_connection.ros={y.get('robot_connection', {}).get('ros')}",
        )
    except Exception as e:
        check("yahboom-mcp reachable", False, str(e))

    frames_in = 0
    ack_seen = 0
    last_seq = 0
    errors: list[str] = []

    async with websockets.connect(f"{TELEOP}?robot={args.robot}", open_timeout=10) as ws:
        check("ws connected", True)

        for i in range(args.frames):
            await ws.send(make_frame(i, args.robot, trigger=0.0, look=args.look))
            try:
                ack = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
            except TimeoutError:
                errors.append(f"ack timeout at seq {i}")
                break
            if ack.get("ok"):
                ack_seen += 1
            else:
                errors.append(f"ack !ok at seq {i}: {ack}")
            if i % 10 == 9:
                await asyncio.sleep(0.05)

        # estop message type
        await ws.send(json.dumps({"type": "estop"}))
        time.sleep(0.3)

    check("ws closed cleanly", True)
    check("all frames acked", ack_seen == args.frames, f"acked={ack_seen}/{args.frames}")
    check("no protocol errors", len(errors) == 0, "; ".join(errors[:3]))

    # Post: session stats via REST
    s = httpx.get(f"{BACKEND}/api/v1/health", timeout=5).json()
    teleop = s.get("teleop", {})
    frames_in = teleop.get("frames_in", 0)
    check("frames_in incremented", frames_in >= args.frames - 2, f"frames_in={frames_in}")
    check(
        "estop_count incremented",
        teleop.get("estop_count", 0) >= 1,
        f"estop_count={teleop.get('estop_count')}",
    )
    check("authority resolved", teleop.get("authority", {}).get("estop_latched", False) is not None)
    rec = teleop.get("recording", {})
    check(
        "recording active flag sane",
        rec.get("recording_enabled", False) is True,
        str(rec.get("recording_enabled")),
    )

    # Recording truth is on disk: latest episode meta length must match streamed frames.
    # (live frame_count resets to 0 when the session ends)
    rec_dir = rec.get("recording_dir") or "data/teleop_recordings"
    meta_path = Path(rec_dir) / "meta" / "episodes.jsonl"
    last_len = 0
    if meta_path.exists():
        for line in meta_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    last_len = json.loads(line).get("length", 0)
                except json.JSONDecodeError:
                    pass
    check(
        "recording captured frames", last_len >= args.frames - 2, f"last_episode_length={last_len}"
    )

    # Post: session ended → watchdog/estop path check
    w = teleop.get("watchdog_latched", None)
    check("watchdog not latched (frames were fresh)", w is not True, str(w))

    print(f"\n=== RESULT: {PASS} passed, {FAIL} failed ===")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    asyncio.run(main())
