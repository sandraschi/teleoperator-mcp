# WebXR client (in-repo)

All VR client code lives in **`webapp/`**. There is no native Pico SDK app, Unity build, or sideloaded APK in this repo.

---

## Stack

| File | Role |
|------|------|
| `webapp/src/main.ts` | 2D landing: robot select, Enter VR, health poll |
| `webapp/src/xr-session.ts` | WebXR session (`immersive-vr`, `local-floor`), pose loop @ 30 Hz |
| `webapp/src/pose-stream.ts` | WebSocket client, heartbeat, reconnect backoff, estop messages |
| `webapp/src/hud.ts` | Chin-strip HUD (Three.js canvas texture, head-attached) |
| `webapp/src/types.ts` | Pose frame v1 schema |
| `webapp/index.html` | Single-page shell |

**Runtime:** Vite 6 + TypeScript + Three.js 0.170 + browser **WebXR Device API**.

**Target browsers:** Pico 4 browser, **Meta Quest Browser** (Quest 2 / 3 / Pro / 3S), desktop Chrome/Edge with the [WebXR Emulator](https://github.com/MozillaReality/WebXREmulatorExtension). All Chromium WebXR — same build, no per-headset native apps.

---

## Supported headsets (same URL, same repo)

| Headset | Browser | Tailscale | Notes |
|---------|---------|-----------|-------|
| **Pico 4** | Pico Browser | Install Tailscale on Pico (recommended) | Primary M1 target |
| **Meta Quest** | Quest Browser (Meta Horizon Browser) | Install Tailscale from Quest store | Same page; verify trigger/squeeze in section 4 matrix |
| **Desktop dev** | Chrome + WebXR Emulator | N/A | `http://localhost:10900` |

**Pico URL (Goliath, live now):** `https://goliath.tailfab45.ts.net/`

Both headsets must reach Goliath on the tailnet (Tailscale app logged in) or use LAN HTTPS if you configure that instead.

---

## What we do not ship (by design for v1)

| Approach | Status |
|----------|--------|
| Pico SDK (native Android) | Out of scope v1; lower latency, more sideload friction |
| Unity / Unreal XR rig | Out of scope v1 |
| WebXR hand tracking | Not used; controllers via Gamepad API on `XRInputSource` |
| Stereo video in XR | v1.5 (LiveKit plane); v2 stereo |

---

## Session flow

```
Landing (2D)  -->  navigator.xr.requestSession('immersive-vr')
                         |
                         v
              requestAnimationFrame loop
                - getViewerPose -> head yaw/pitch
                - inputSources + gamepad -> sticks/trigger/squeeze
                - PoseStream -> wss://host/ws/teleop
                - XrHud update (throttled redraw)
                         |
                         v
              Three.js render (placeholder video plane until LiveKit)
```

Pose never goes through MCP. Only WebSocket to backend `:10901` (via Vite proxy in dev, or same-origin in production).

---

## HTTPS requirement

WebXR immersive mode requires a secure context. See [HTTPS.md](HTTPS.md) for Tailscale Serve on Goliath.

---

## Dev without headset

1. `just web` + `just serve`
2. Chrome + WebXR Emulator extension
3. Open `http://localhost:10900` (localhost is a secure context for WebXR in some setups; HTTPS still preferred for Pico parity)

---

## Pico-specific notes

- Read gamepad from `inputSource.gamepad`, not `navigator.getGamepads()` alone.
- Cap pose send rate at 30 Hz (implemented in `xr-session.ts`).
- Squeeze on either controller sends `estop` and suppresses drive frames (M0).
- Right trigger is deadman for drive (must hold > 0.5).

## Meta Quest notes

- Use **Quest Browser** (built-in), not a random WebView shell.
- Install **Tailscale** on the headset, sign in to the same tailnet as Goliath.
- Open the same `https://goliath.*.ts.net/` URL as Pico.
- Controller layout is usually compatible (trigger = `buttons[0]`, grip/squeeze = `buttons[1]`). If drive or estop feel wrong on Meta, note which button works in the bring-up matrix — we can add a `?profile=meta` mapping later without leaving the web stack.

Hardware matrix: [BRINGUP.md](BRINGUP.md) section 4.
