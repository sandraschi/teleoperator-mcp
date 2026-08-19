# Onboarding — teleoperator-mcp

## What this is for

Teleoperator MCP streams VR headset pose (Pico 4, Meta Quest) from a WebXR browser to fleet
robots and virtual twins. It is a teleoperation gateway — not an auto-pilot, not a robot
SDK, and not a substitute for the robot's own safety. The webapp is the VR client; MCP tools
supervise. To get joy you need a robot bridge (yahboom-mcp for Boomy), and for video return a
LiveKit SFU. You can develop and demo without any physical hardware using the vboomy virtual
twin in Resonite.

## Cost and accounts (money / CC)

| Question | Answer |
|----------|--------|
| Do I need an account? | No account required. Local services only (yahboom-mcp, LiveKit SFU, optional Ollama/LM Studio). |
| Free tier? | Yes — everything is free and self-hosted. No vendor accounts. |
| Credit card required? | No |
| Ongoing cost? | Free. Hardware (robot, headset) is your own purchase; software is all local. |
| Who bills? | Nobody. |

## Prerequisites outside this repo

- **Hardware (recommended, not required):** a Pico 4 or Meta Quest headset and a Boomy
  (Yahboom ROSMASTER X3) or Bumi robot. Without hardware you can still drive the vboomy
  virtual twin in Resonite (needs Resonite installed).
- **Robot bridge:** `yahboom-mcp` running on Goliath (port 10892) for Boomy. Install per the
  yahboom-mcp repo.
- **Video return (optional):** the LiveKit SFU Windows service `LiveKitSFU` on port 15580
  (managed by NSSM, configured in `teleconference-mcp/livekit.yaml`).
- **Network:** the headset and Goliath on the same Tailscale tailnet; Tailscale Serve enabled
  for HTTPS (WebXR requires HTTPS).
- **Local LLM (optional):** Ollama on port 11434 or LM Studio on 1234 for the chat panel.

## First-timer setup steps

1. Clone and install: `git clone https://github.com/sandraschi/teleoperator-mcp`, then
   `cd teleoperator-mcp` and `just bootstrap`.
2. Copy the env template: `Copy-Item .env.example .env`. Set `TELEOP_YAHBOOM_API_URL`,
   `TELEOP_CORS_ORIGINS`, and LiveKit credentials to match your tailnet and SFU.
3. Start the stack: `.\webapp\start.bat -WithTailscaleServe`.
4. Verify the backend is healthy:
   `Invoke-RestMethod http://127.0.0.1:10901/api/v1/health` — `status` must be `ok` and the
   `onboarding` block `configured: true` once yahboom-mcp is reachable.
5. Open the webapp at `http://localhost:10900` (or the Tailscale Serve HTTPS URL on the
   headset). The dashboard onboarding cue clears once the bridge reports configured.
6. Select a robot (boomy, bumi, or vboomy) and press Enter VR. Squeeze a grip to take over,
   hold the trigger to drive with the right stick.
7. Optional video: start the LiveKit SFU service and call
   `teleop_livekit_publisher_start()` (or set `TELEOP_LIVEKIT_AUTO_START_PUBLISHER=1`).

## Pitfalls

- **WebXR requires HTTPS.** If you open the webapp over HTTP on the headset, `Enter VR` will
  fail. Use `-WithTailscaleServe` (or your own HTTPS reverse proxy).
- **Watchdog stops the robot.** If pose frames stop for `TELEOP_WATCHDOG_MS` (default 1 s),
  drive latches off. Keep the headset tab in the foreground and the network under the
  watchdog interval.
- **AUTO is time-bounded.** AUTO base runs stop after `TELEOP_AUTO_MAX_DURATION_S` (10 s) and
  normally requires an active WebXR session — pass `confirm_bench=true` only on the bench.
- **estop latches until takeover.** After `teleop_estop()` the robot stays stopped until
  `teleop_takeover()` clears the latch. This is deliberate.
- **LiveKit key mismatch.** If the publisher connects but the headset token is rejected, the
  `TELEOP_LIVEKIT_API_KEY` / `SECRET` do not match the SFU.
- **Robot not moving?** Check yahboom-mcp is up, robot powered, base group in DIRECT (or AUTO
  with an active producer), and no estop/watchdog latch.

## Sanity check

Onboarding worked when:

- `GET /api/v1/health` returns `"onboarding": {"configured": true, "service": "yahboom-mcp", ...}`
- The webapp dashboard no longer shows the MOCK sample content (mock clears on configured).
- A dry-run drive reaches the robot bridge (check yahboom-mcp logs / `teleop_status()` frames
  increase when driving).
- Optional: the headset shows camera video via LiveKit.

## Declared doubles

Without a robot bridge (onboarding incomplete), the webapp may show **MOCK**-badged sample
content (`data-testid="mock-badge"`) so the UI is not a blank desert. Mock KPIs use fake
names and are clearly badged; they clear automatically once `onboarding.configured` is true.
The `FALLBACK_ROBOTS` catalog in the webapp is a declared fallback for the robot list while
the backend is offline — it is not a live robot list. See `TESTING_GUIDE.md` § Declared
doubles.
