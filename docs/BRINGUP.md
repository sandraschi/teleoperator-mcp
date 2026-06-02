# Boomy hardware bring-up (Milestone 1)

Step-by-step bench checklist for first Pico -> Boomy teleop session on Goliath.

Prerequisites: [HTTPS.md](HTTPS.md), [TODO.md](TODO.md) Milestone 1.

---

## 1. Goliath stack

```powershell
# Terminal A - yahboom driver (if not already running)
Set-Location D:\Dev\repos\yahboom-mcp
$env:YAHBOOM_IP = "<boomy-pi-ip>"
just serve

# Terminal B - teleoperator backend
Set-Location D:\Dev\repos\teleoperator-mcp
$env:TELEOP_YAHBOOM_API_URL = "http://127.0.0.1:10892"
$env:TELEOP_CORS_ORIGINS = "https://<your-tailscale-host>.ts.net,http://localhost:10900"
just serve

# Terminal C - webapp
Set-Location D:\Dev\repos\teleoperator-mcp
just web
```

Verify:

```powershell
Invoke-RestMethod http://127.0.0.1:10892/api/v1/health
Invoke-RestMethod http://127.0.0.1:10901/api/v1/health
```

---

## 2. HTTPS entry (Pico path)

```powershell
tailscale serve --bg http://127.0.0.1:10900
tailscale serve status
```

Open the `https://*.ts.net` URL on a desktop browser first; confirm health stats appear.

---

## 3. REST contract smoke test (no VR)

From Goliath, confirm yahboom endpoints match the mapper:

```powershell
# Stop command (safe)
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:10892/api/v1/control/move?linear=0&angular=0"

# PTZ (small move)
$body = @{ operation = "camera_set_pos"; param1 = 90; param2 = 45 } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:10892/api/v1/control/tool" -Body $body -ContentType "application/json"
```

If either fails, fix yahboom-mcp before Pico testing. Update `BoomyMapper` if paths differ.

---

## 4. Pico WebXR matrix

On Pico browser, open the HTTPS teleop URL.

| Check | Pass? |
|-------|-------|
| Landing page loads | |
| `/api/v1/health` poll shows `teleop.active: false` | |
| **Enter VR** enabled | |
| Immersive session starts | |
| Chin HUD visible, not blocking center view | |
| Right trigger + stick drives (deadman) | |
| Head motion moves PTZ (may lag ~100 ms) | |
| Squeeze either grip -> ESTOP in HUD, robot stops | |
| Release trigger -> robot stops | |
| Second browser tab rejected (4003) or fails to drive | |

Record Pico Browser version and any console errors.

---

## 5. Safety drills

Perform in order with Boomy on blocks or clear floor:

1. **Deadman:** drive with trigger; release -> stop within one watchdog period.
2. **Squeeze estop:** while idle and while driving.
3. **MCP estop:** from Cursor, call `teleop_estop` while session active.
4. **Watchdog:** kill backend network briefly or stop sending pose (close tab) -> robot stops < 300 ms.
5. **Reconnect:** toggle WiFi on Pico briefly; HUD should go red then recover (WS backoff).

---

## 6. Latency (rough)

Measure subjectively first, then if needed:

- **Motion-to-command:** stick deflection to wheel spin (target < 150 ms on LAN).
- **Head-to-PTZ:** head turn to servo move (target < 200 ms).

Log notes in this file or a dated entry under `docs/archive/`.

---

## 7. Sign-off

Milestone 1 complete when:

- [ ] All section 4 matrix items pass
- [ ] All section 5 safety drills pass
- [ ] REST contract confirmed or mapper patched
- [ ] HTTPS path documented with your actual Tailscale hostname

Then proceed to Milestone 2 (adapter) in [TODO.md](TODO.md).
