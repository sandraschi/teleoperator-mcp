"""Bench PTZ sweep via live backend (0-180° servos, center 90)."""

import json
import sys
import time
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:10901"

STEPS = [
    ("center", 90, 90),
    ("left", 60, 90),
    ("right", 120, 90),
    ("up", 90, 60),
    ("down", 90, 120),
    ("center", 90, 90),
]


def post(path: str, params: dict | None = None) -> dict:
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def main() -> None:
    print("=== BENCH PTZ SWEEP ===")
    for name, pan, tilt in STEPS:
        r = post("/api/v1/teleop/gaze", {"pan": pan, "tilt": tilt})
        print(f"{name}: {r}")
        if not r.get("success"):
            sys.exit(1)
        time.sleep(1.5)
    print("done — camera should have panned/tilted through sweep")


if __name__ == "__main__":
    main()
