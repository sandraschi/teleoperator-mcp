"""Bench AUTO via live backend REST (not a separate Python process)."""
import json
import sys
import time
import urllib.parse
import urllib.request


BASE = "http://127.0.0.1:10901"


def post(path: str, params: dict | None = None) -> dict:
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def get(path: str) -> dict:
    with urllib.request.urlopen(BASE + path, timeout=10) as resp:
        return json.loads(resp.read().decode())


def main() -> None:
    print("=== BENCH AUTO (live server) ===")
    r = post("/api/v1/teleop/set_mode", {"group": "base", "mode": "AUTO", "confirm_bench": "true"})
    print("set_mode:", r)
    if not r.get("success"):
        sys.exit(1)

    for i in range(12):
        time.sleep(1)
        s = get("/api/v1/health")["teleop"]
        auth = s.get("authority", {}).get("base", {})
        base = (s.get("last_applied") or {}).get("base") or {}
        print(
            f"t+{i + 1}s mode={auth.get('mode')} elapsed={s.get('auto_elapsed_s')} linear={base.get('linear')}"
        )
        if auth.get("mode") == "DIRECT" and i >= 2:
            print("AUTO ended")
            break

    post("/api/v1/teleop/takeover")
    post("/api/v1/teleop/estop")
    print("done — wheels should have spun on blocks")


if __name__ == "__main__":
    main()
