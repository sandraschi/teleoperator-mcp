# HTTPS for Pico WebXR

WebXR requires a **secure context** (HTTPS or localhost). The Pico browser on your LAN cannot use `http://192.168.x.x:10900` for immersive VR. This guide covers Goliath -> Pico access.

**Recommended:** Tailscale Serve (tailnet HTTPS, no cert management).
**Fallback:** LAN self-signed cert (more Pico browser friction).

Related: Milestone 1 in [TODO.md](TODO.md), ports in [PRD.md](PRD.md).

---

## Architecture

```
Pico Browser  --HTTPS/WSS-->  Tailscale Serve (443 on ts.net hostname)
                                    |
                                    v
                              Vite webapp :10900  --proxy-->  backend :10901
                                    |                              |
                                    +-------- /ws/teleop ----------+
                                    +-------- /api/v1/* -----------+
```

Run **both** processes on Goliath during bring-up:

```powershell
Set-Location D:\Dev\repos\teleoperator-mcp
just serve    # backend :10901
just web      # webapp  :10900 (proxies /api and /ws to backend)
```

The webapp must be the HTTPS entrypoint so `/ws` and `/api` share the same origin as the page (required for WSS without mixed-content blocks).

**Vite 6:** add your Tailscale hostname to `webapp/vite.config.ts` `server.allowedHosts` (repo ships `.ts.net` suffix). Restart `npm run dev` after changing it.

---

## Option A: Tailscale Serve (recommended)

Tailnet-only HTTPS with automatic certificates. Matches fleet patterns (see `myai/docs/TAILSCALE_INTEGRATION.md`).

### 1. Expose the webapp

```powershell
tailscale serve --bg http://127.0.0.1:10900
tailscale serve status
```

Note the hostname, e.g. `https://goliath.tail12345.ts.net/`.

### 2. Allow CORS for that origin

```powershell
$env:TELEOP_CORS_ORIGINS = "https://goliath.tail12345.ts.net,http://localhost:10900,http://127.0.0.1:10900"
just serve
```

Or set `TELEOP_CORS_ORIGINS` in `.env` on Goliath.

### 3. Open on Pico

1. Install Tailscale on Pico (if not already on tailnet) **or** use a phone hotspot path that reaches Goliath on the tailnet.
2. Pico browser -> `https://goliath.tail12345.ts.net/`
3. Tap **Enter VR**

WebSocket URL is derived from `window.location` (`wss://goliath.tail12345.ts.net/ws/teleop`), which Tailscale forwards to Vite; Vite proxies to `:10901`.

### 4. Reset when done

```powershell
tailscale serve reset
```

### Serve vs Funnel

| | Serve | Funnel |
|---|-------|--------|
| Tailnet only | Yes | No (public internet) |
| HTTPS | Auto | Auto |
| Use for teleop | **Yes** | Only if Pico is off-tailnet |

Do **not** use Funnel for robot control unless you add auth; teleop is a control surface.

---

## Option B: Self-signed cert on LAN

Use when Pico and Goliath are on the same WiFi and Tailscale is unavailable.

### 1. Generate cert (one-time, on Goliath)

Use `mkcert` or OpenSSL. Example with mkcert:

```powershell
mkcert -install
mkcert goliath.local 192.168.1.50 localhost 127.0.0.1
```

Produces `goliath.local+3.pem` and `-key.pem`.

### 2. Vite HTTPS dev server

Add to `webapp/vite.config.ts` (or pass CLI flags):

```typescript
server: {
  https: {
    cert: "../certs/goliath.local.pem",
    key: "../certs/goliath.local-key.pem",
  },
  // ... existing port 10900 and proxy
}
```

Do not commit private keys; add `certs/` to `.gitignore`.

### 3. Pico trust

Pico Browser may block self-signed certs. Options:

- Open the HTTPS URL once in 2D, accept the cert warning if offered
- Install the mkcert root CA on Pico (often impractical)
- Prefer Tailscale Serve instead

### 4. CORS

```powershell
$env:TELEOP_CORS_ORIGINS = "https://goliath.local:10900,https://192.168.1.50:10900"
```

---

## Verification checklist

Before Pico hardware test:

- [ ] `https://<host>/` loads the landing page (no cert error)
- [ ] Browser devtools or `curl -k` shows `/api/v1/health` returns `{"status":"ok"}`
- [ ] WebSocket connects: page shows backend stats updating on landing (poll every 3s)
- [ ] `TELEOP_CORS_ORIGINS` includes the exact browser origin (scheme + host + port if non-443)
- [ ] `yahboom-mcp` running on Goliath (`http://127.0.0.1:10892/api/v1/health`)
- [ ] Boomy reachable from Goliath (`YAHBOOM_IP` set for yahboom-mcp)

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Enter VR disabled | Not HTTPS or WebXR unsupported | Use Serve or HTTPS Vite |
| WS red in HUD | Backend down or proxy broken | Start `just serve`; check Vite proxy `/ws` |
| CORS error in console | Origin not in allowlist | Set `TELEOP_CORS_ORIGINS` |
| Robot does not move | yahboom-mcp offline or wrong IP | Check `10892` health and rosbridge |
| Mixed content | Page HTTPS, WS ws:// | Must use same-origin `wss://` via proxy |

---

## Production note (post-M1)

For a non-dev deployment, serve `webapp/dist` behind a reverse proxy (Caddy/nginx) with TLS termination and the same `/api` + `/ws` upstream to `:10901`. Vite dev server is for bring-up only.
