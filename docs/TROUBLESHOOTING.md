# Troubleshooting

Symptom-first guide for the teleoperator-mcp stack. Start with the table, then follow the
matching section.

## Quick reference

| Symptom | First check | Fix |
|---------|-------------|-----|
| Robot frozen / no motion | `teleop_status()` → estop_latched, watchdog_latched, authority | `teleop_takeover()`, verify frames flowing |
| No video in headset | `teleop_livekit_status()` → running, connected, last_error | start publisher; restart LiveKitSFU service |
| WebXR not available | browser + HTTPS | use Tailscale Serve; check navigator.xr |
| WebSocket disconnects | frames in / watchdog | raise TELEOP_WATCHDOG_MS; keep tab foreground |
| **WS rejected (4001)** | claim token | claim the robot (`POST /api/v1/session/claim` or Home page); estop stays open |
| **Enter VR disabled** | claim gate | add operator name on Home + Claim robot |
| AUTO mode won't start | WebXR session | pass confirm_bench=true on the bench |
| CORS blocked in headset | browser console | set TELEOP_CORS_ORIGINS incl. ts.net origin |
| **No frames in episodes** | egress status | check `/api/v1/livekit/egress`, TELEOP_LIVEKIT_EGRESS_ENABLED, publisher running |
| Backend won't start | port + traceback | clear port 10901, uv sync, check .env |
| Health endpoint down | process check | verify backend started; check logs ring buffer |

## Robot does not move

1. Confirm yahboom-mcp is running and reachable on `http://127.0.0.1:10892`.
2. Confirm the robot is powered on and on the network.
3. Call `teleop_status()`: session must be `active` with `frames_in` increasing.
4. Confirm the estop is not latched and the watchdog has not latched.
5. Confirm authority: `base` must be DIRECT (or AUTO with an active producer).
6. Check `/api/v1/health` for the yahboom API URL actually in use — a stale
   `TELEOP_YAHBOOM_API_URL` silently points at the wrong target.

## WebSocket rejected with 4001 (claim)

The operator claim gate is on (`TELEOP_REQUIRE_CLAIM=1`). Claim the robot before connecting:

1. `POST /api/v1/session/claim` with `{"operator_id": "...", "robot_id": "boomy"}` → token.
2. Connect `/ws/teleop?robot=boomy&token=<token>`.
3. Or use the Home page claim UI — Enter VR stays disabled until claimed.

E-stop never requires a token. To disable the gate on a bench/development machine, set
`TELEOP_REQUIRE_CLAIM=0`.

## No video frames in recorded episodes

Episodes should carry an `observation.image.image` column from the egress sink. If not:

1. `GET /api/v1/livekit/egress` — is `egress_enabled` true and `captured_total` rising?
2. Is the LiveKit publisher running? Frames only flow while it publishes
   (`teleop_livekit_status()` → `running`).
3. `TELEOP_LIVEKIT_EGRESS_ENABLED=1` and a sane `TELEOP_LIVEKIT_EGRESS_TOLERANCE_MS`
   (default 300 ms — the teleop frame and its video frame must land close together).
4. Re-export the episode — `POST /api/v1/recording/export` — and confirm the parquet has the
   image column.

## No video in the headset

1. `teleop_livekit_status()` — if `running` is false, call
   `teleop_livekit_publisher_start()`.
2. If `connected` is false, the LiveKit SFU is down. Check `Get-Service LiveKitSFU` and that
   port 15580 is listening.
3. Check teleconference-mcp logs: `teleconference-mcp/logs/livekit.out.log`.
4. Verify `TELEOP_LIVEKIT_API_KEY` / `TELEOP_LIVEKIT_API_SECRET` match the SFU config. A
   token rejection with a successful connect is the signature of a key mismatch.
5. Confirm `TELEOP_LIVEKIT_PUBLIC_URL` is set to the headset-reachable WSS URL on Tailscale;
   if empty the headset falls back to `TELEOP_LIVEKIT_URL` which may not be reachable.
6. If MJPEG fails, the snapshot fallback should still produce frames — check the `source`
   field to see which path is active.

## WebXR not available

1. The browser must support `immersive-vr`. Pico 4 uses Pico Browser; Quest uses its built-in
   browser. Wolvic is not supported.
2. WebXR requires HTTPS. If the page is served over HTTP, use Tailscale Serve
   (`.\webapp\start.bat -WithTailscaleServe`).
3. Check the browser console: `navigator.xr.isSessionSupported("immersive-vr")` must resolve
   true on the headset.

## WebSocket disconnects / watchdog trips

1. The watchdog latches when no pose frames arrive within `TELEOP_WATCHDOG_MS` (default 1000
   ms). Confirm the Frames In KPI is actually climbing.
2. Tailscale latency above the watchdog interval causes trips; raise `TELEOP_WATCHDOG_MS` for
   slow links.
3. Keep the headset browser tab in the foreground; background tabs throttle the frame loop.

## AUTO mode fails to start

1. AUTO on the base group requires an active WebXR session unless `confirm_bench=true` is
   passed.
2. The AUTO timer bounds the run at `TELEOP_AUTO_MAX_DURATION_S` (default 10 s) with a warning
   at `TELEOP_AUTO_WARN_BEFORE_S`.
3. If a spoken warning is expected but missing, speech-mcp may be down; the SAPI fallback
   should still speak.

## Backend fails to start

1. Port 10901 may be occupied by a stale process. The launcher clears it, but check with
   `Get-NetTCPConnection -LocalPort 10901` and kill the owning PID if needed.
2. Re-run `uv sync` after a dependency change.
3. Read the backend window traceback. Common causes: missing `.env` variables, LiveKit
   credentials that do not match the SFU, and a stale editable install (re-run `uv pip
   install -e .` if pytest silently uses old code).

## CORS errors in the headset browser

1. The headset loads the webapp from a `https://*.ts.net` origin. `TELEOP_CORS_ORIGINS` must
   include it. The launcher sets it automatically from `tailscale serve status`.
2. If running the backend by hand, set `TELEOP_CORS_ORIGINS` to include your Tailscale HTTPS
   origin plus localhost origins.

## Health endpoint returns non-200

1. Confirm the backend process is running (launcher window, `Get-Process` for the backend
   python/pyinstaller process).
2. Confirm the port is bound: `Get-NetTCPConnection -LocalPort 10901 -State Listen`.
3. Query the ring buffer: `GET /api/logs?level=ERROR` for startup errors.
4. `GET /api/v1/diagnostics` reports tool count, system info, and any recorded errors.

## Tests fail unexpectedly

1. Verify the editable-install guard passes: tests must import from `src/`, not a stale copy
   in `.venv/Lib/site-packages`. Re-run `uv pip install -e .` if needed.
2. The LiveKit token test emits an `InsecureKeyLengthWarning` (short dev key) — that warning
   is expected, not a failure.
3. `just integration-test` requires the backend to be running; run the stack first.

## Still stuck

- Check the fleet bug depot: `mcp-central-docs/troubleshooting/BUGS_DEPOT.md`.
- Dump diagnostics: `GET /api/v1/diagnostics`.
- Grep the repo docs: `docs/ARCHITECTURE.md`, `docs/LIVEKIT.md`, `docs/TAILSCALE_VIEWERS.md`,
  `docs/BRINGUP.md`.
