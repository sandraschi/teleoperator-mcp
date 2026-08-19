"""Latency benchmark — motion-to-command (T4.2).

Measures the full pose->command->ack path against a live stack:
- WS frame send -> backend ack (round-trip, includes watchdog + command apply)
- Reports p50/p90/max over N frames at the configured pose cadence.

Usage (backend must be running, claim optional):
  uv run python scripts/latency-bench.py --robot boomy --frames 120 --token <claim-token>
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time

import websockets


async def main() -> int:
    parser = argparse.ArgumentParser(description="Motion-to-command latency benchmark")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=10901)
    parser.add_argument("--robot", default="boomy")
    parser.add_argument("--frames", type=int, default=120)
    parser.add_argument("--rate", type=float, default=30.0, help="pose rate (Hz)")
    parser.add_argument("--token", default="")
    args = parser.parse_args()

    url = f"ws://{args.host}:{args.port}/ws/teleop?robot={args.robot}"
    if args.token:
        url += f"&token={args.token}"

    latencies: list[float] = []
    interval = 1.0 / args.rate
    seq = 0

    async with websockets.connect(url) as ws:
        # Warmup
        for _ in range(5):
            await ws.send(json.dumps({"v": 1, "type": "presence", "t": time.time()}))
            await asyncio.sleep(0.05)

        for _ in range(args.frames):
            seq += 1
            t0 = time.perf_counter()
            await ws.send(
                json.dumps(
                    {
                        "v": 1,
                        "seq": seq,
                        "t": time.time(),
                        "type": "pose",
                        "head": {"yaw": 0.0, "pitch": 0.0, "roll": 0.0},
                        "right": {
                            "connected": True,
                            "axes": [0.0, 0.0],
                            "buttons": {"trigger": 0.0},
                        },
                    }
                )
            )
            ack = await asyncio.wait_for(ws.recv(), timeout=1.0)
            dt = (time.perf_counter() - t0) * 1000.0
            latencies.append(dt)
            if seq % 20 == 0:
                print(f"  frame {seq}: {dt:.1f} ms")
            await asyncio.sleep(interval)

    latencies.sort()
    n = len(latencies)
    p50 = statistics.median(latencies)
    p90 = latencies[int(n * 0.9)] if n else 0.0
    p99 = latencies[int(n * 0.99)] if n else 0.0
    print("\n=== motion-to-command latency ===")
    print(f"  frames: {n}")
    print(f"  mean:   {statistics.mean(latencies):.1f} ms")
    print(f"  p50:    {p50:.1f} ms")
    print(f"  p90:    {p90:.1f} ms")
    print(f"  p99:    {p99:.1f} ms")
    print(f"  max:    {latencies[-1]:.1f} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
