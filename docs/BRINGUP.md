# Boomy hardware bring-up (Milestone 1)

Step-by-step bench checklist for first **Pico 4 or Meta Quest** teleop session on Goliath.

Prerequisites: [HTTPS.md](HTTPS.md), [TODO.md](TODO.md) Milestone 1.

---

## Raspbot AP + Tailscale (typical lab setup)

| Device | Network | Role |
|--------|---------|------|
| **Goliath PC** | Join **Raspbot AP** WiFi (Pi often `192.168.1.11`) | yahboom-mcp rosbridge to Boomy |
| **Pico / Meta** | **Tailscale** tailnet (WiFi can be home AP or phone hotspot) | Browser -> `https://goliath.*.ts.net` |
| **Boomy Pi** | Raspbot AP host | Robot; not contacted directly by headset |

Headsets do **not** need the Raspbot AP — they reach Goliath over Tailscale. Goliath must be on the AP (or routed to `192.168.1.11`) for drive commands to reach the Pi.

---

## 1. Goliath stack

One-shot (opens minimized windows for backend + webapp, enables Tailscale Serve):

```powershell
Set-Location D:\Dev\repos\teleoperator-mcp
Copy-Item .env.example .env   # edit TELEOP_CORS_ORIGINS if your ts.net host differs
.\scripts\m1-up.ps1
```

Manual (three terminals):

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

## 2. HTTPS entry (headset path)

```powershell
tailscale serve --bg http://127.0.0.1:10900
tailscale serve status
```

**Live URL:** `https://goliath.tailfab45.ts.net/`

On **Pico 4** or **Meta Quest**: install Tailscale on the headset, open Quest/Pico Browser, paste the URL above, tap **Enter VR**.

Open the same URL on a desktop browser first; confirm health stats appear on the landing page.

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

## 4. WebXR matrix (Pico 4 or Meta Quest)

On headset browser, open `https://goliath.tailfab45.ts.net/`.

| Check | Pico 4 | Meta Quest |
|-------|--------|------------|
| Landing page loads | | |
| **Enter VR** enabled | | |
| Immersive session starts | | |
| Chin HUD visible | | |
| Right trigger + stick drives (deadman) | | |
| Head motion moves PTZ | | |
| Squeeze/grip -> ESTOP | | |
| Release trigger -> stop | | |

Record headset model, browser version, and behavior notes (Quest has no easy devtools).

---

## 5. Safety drills

Perform in order with Boomy on blocks or clear floor:

1. **Deadman:** drive with trigger; release -> stop within one watchdog period.
2. **Squeeze takeover (M3):** while `base` is AUTO (via `teleop_set_mode`), squeeze reclaims human drive — HUD shows **TAKEOVER**; trigger drives again with no lurch.
3. **MCP estop:** from Cursor, call `teleop_estop` while session active.
4. **Watchdog:** kill backend network briefly or stop sending pose (close tab) -> robot stops < 300 ms.
5. **Reconnect:** toggle WiFi on headset briefly; HUD should go red then recover (WS backoff).

### M3 without headset (Boomy on bench)

From Cursor while backend is up and Goliath is on the Raspbot AP:

1. `teleop_set_mode(group="base", mode="AUTO")` — Boomy should crawl forward slowly (nav stub).
2. `teleop_status` — confirm `authority.base.mode` is `AUTO`, `owner` is `nav_stub`.
3. `teleop_takeover()` — base returns to `DIRECT` / `human_pose`; robot stops if no WebXR session.
4. `teleop_estop()` — hard stop; latch clears on next `teleop_takeover` or new WebXR session.

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

Then proceed to Milestone 4 (LeRobot logging) in [TODO.md](TODO.md). Milestone 3 (arbiter) is software-complete; squeeze takeover sign-off is part of section 5 above.
