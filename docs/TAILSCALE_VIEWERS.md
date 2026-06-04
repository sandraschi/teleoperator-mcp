# Tailscale on VR viewers (Pico 4 and Meta Quest)

WebXR requires **HTTPS**. On Goliath we use **Tailscale Serve** so headsets open `https://goliath.*.ts.net/` without managing certificates. That only works if the **viewer can reach the tailnet**.

Related: [HTTPS.md](HTTPS.md), [WEBXR.md](WEBXR.md), [BRINGUP.md](BRINGUP.md). Fleet hub: [mcp-central-docs/pico](../../mcp-central-docs/pico/README.md).

---

## Will Tailscale on viewers be a problem?

**Usually no** — if each headset runs the Tailscale app on the **same tailnet** as Goliath. That is the intended setup.

| Concern | Reality |
|---------|---------|
| Extra latency | Small (tailnet overlay). Fine for slow teleop; measure on your WiFi. |
| HTTPS for WebXR | **Solved** by Serve — browsers trust `*.ts.net`. |
| Pico / Meta support | Quest: store app. Pico: sideload APK (same Android client). |
| Subnet routing | **Not required** when using Serve on Goliath (headset talks to Goliath's tailnet IP/hostname, not LAN robot IP). |
| Robot on LAN only | Boomy stays on `192.168.x.x`; **Goliath** bridges via yahboom-mcp. Headsets never talk to the Pi directly. |

---

## Setup checklist (each headset once)

1. Install **Tailscale** — **Meta Quest:** store app; **Pico 4:** sideload APK ([fleet revive pack](https://github.com/sandraschi/mcp-central-docs/blob/main/pico/SETUP_SCRIPTS.md) or [pkgs.tailscale.com](https://pkgs.tailscale.com/stable/#android)).
2. Sign in to the **same account/tailnet** as Goliath.
3. Confirm the device appears in [Tailscale admin](https://login.tailscale.com/admin/machines) or `tailscale status` on Goliath.
4. Open **Quest Browser** or **Pico Browser** (not an in-VR WebView shell without Tailscale routes).
5. Navigate to **`https://goliath.<your-tailnet>.ts.net/`** (from `tailscale serve status` on Goliath).
6. Tap **Enter VR**.

---

## Common failure modes

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Page never loads | Headset not on tailnet | Open Tailscale app, confirm Connected |
| Page loads on PC but not headset | Wrong URL (http vs https, LAN IP) | Use `https://*.ts.net` only |
| Vite "host not allowed" | Serve Host header blocked | Fixed in `vite.config.ts` `allowedHosts`; restart `npm run dev` |
| CORS error in browser | Origin not allowlisted | Set `TELEOP_CORS_ORIGINS` to include your exact `https://goliath.*.ts.net` |
| WS stays red in HUD | Backend down or proxy broken | `just serve` + `just web`; check `/api/v1/health` |
| Tailscale connected but only 2 devices on Pico | **Wrong tailnet** (new account on Android login) | Sign out → sign in with **same Microsoft account as Goliath** (`sandraschipal@hotmail.com` / `tailfab45.ts.net`). Confirm Pico appears in [admin machines](https://login.tailscale.com/admin/machines) and `tailscale status` on Goliath. |
| Tailscale connected but no Goliath | ACL or pending approval | Tailscale admin → approve device; ACLs: allow Pico → goliath |
| Watchdog voice repeating | Heartbeat vs 300 ms watchdog bug (fixed) + pose WS dead | Restart backend (`webapp\start.bat`); exit VR properly; HUD should show `WS … ms` when pose is live |
| Gray screen / `vid--` in HUD | Video pipe broken | Start publisher (`Tools → teleop_livekit_publisher_start` or `POST /api/v1/livekit/publisher/start`); LiveKit SFU on `:15580`; `TELEOP_LIVEKIT_PUBLIC_URL` for Pico |
| Session drops in VR | WiFi sleep / app backgrounded | Keep browser foreground; exit VR when done (closes WS) |
| 403 from ts.net URL on Goliath itself | Serve loopback quirk | Normal; test from headset or another tailnet device |

---

## Pico 4 notes

- Tailscale for Pico is available; login may be easier with a linked Google/account flow in 2D first.
- Use **Pico Browser** directly — sideloaded Chromium may not route through Tailscale VPN.
- Same WiFi as Goliath is **not** enough for WebXR unless you also serve LAN HTTPS (harder). Prefer tailnet URL.

---

## Meta Quest notes

- Install Tailscale from the Quest store; enable **Allow local network** if prompted (Serve still goes over tailnet).
- **Quest Browser** (Meta Horizon Browser) is supported; same URL as Pico.
- Controller mapping may differ slightly — see [WEBXR.md](WEBXR.md).

---

## When Tailscale is the wrong tool

- **Public internet access** without tailnet membership -> do not use Funnel for robot control without auth.
- **Ultra-low LAN-only lab** with no internet -> self-signed HTTPS on LAN is possible but painful on headsets; tailnet is still easier.

---

## Goliath-side commands (reference)

```powershell
tailscale serve --bg http://127.0.0.1:10900
tailscale serve status
# reset:
tailscale serve reset
```

Ensure `TELEOP_CORS_ORIGINS` includes your Serve hostname before starting the backend.
