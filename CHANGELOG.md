
## [Unreleased] — 2026-06-14

### Added
- Tauri native wrapper (native/ directory) with bundle.resources + std::process::Command
- CUA-NSIS: just cua-nsis-test recipe, scripts/cua-smoke.py, scripts/cua-nsis-config.json
- Tauri CORS: tauri://localhost origins for WebView API access
- NSIS installer at dist/ and native/target/release/bundle/nsis/

### Changed
- Frontend API calls use absolute http://127.0.0.1:{port} URLs in production build
- CORS middleware includes allow_origin_regex for tauri.localhost
# Changelog

All notable changes to teleoperator-mcp are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added

- **SOTA webapp (fleet WEBAPP_STANDARDS):** React + Vite 6 Iron Shell — Home, Tools, Logs, Apps, Settings, Help; bottom logger panel; `/api/capabilities` UI; hash routes for Tailscale Serve.
- **`/api/logs`*** ring buffer — query, stats, export, clear (`activity_log.py`); API + WebXR session logging.
- **`webapp/start.ps1` / `start.bat`** — fleet launcher with port cleanup, `uv sync`, backend health wait, optional `-WithTailscaleServe`, `-Detached`.
- **`glama.json`** — fleet discovery fields (homepage, entrypoint, transport, web/backend ports).
- **`GET /api/capabilities`** — runtime tool/feature introspection for webapp and agents.

### Fixed

- **`webapp/start.ps1`:** Vite launch on Windows via `cmd /c npm run dev` (`Start-Process npm` is not a valid Win32 app).
- **Watchdog speech loop:** heartbeats no longer reset `_watchdog_latched`; default `TELEOP_WATCHDOG_MS` raised to **1000** (pose frames only count as teleop alive).
- **`start.ps1`:** auto-set `TELEOP_LIVEKIT_PUBLIC_URL=wss://<tailnet-host>:15580` from `tailscale serve status` (alongside CORS).

### Changed

- Webapp entry: `src/main.tsx` + React pages; WebXR core unchanged (`xr-session.ts`, `pose-stream.ts`, `livekit-video.ts`).

### Added (robot)

- **`BumiAdapter`** — `?robot=bumi` → bumi-mcp `/api/v1` (walk, head, estop, manip stub).
- **`VboomyAdapter`** — `?robot=vboomy` → robotics-mcp → Resonite OSC (virtual Boomy twin).
- **[docs/VIRTUAL_TWINS.md](docs/VIRTUAL_TWINS.md)** + **[docs/resonite/VBOOMY_OSC.md](docs/resonite/VBOOMY_OSC.md)** — vBoomy proof loop.
- **[docs/VBOT_CREATIVE_TWINS.md](docs/VBOT_CREATIVE_TWINS.md)** — Mechazilla, kaiju, creative vBot roster.
- **`scripts/register-vboomy.ps1`**, **`scripts/start-vboomy-loop.ps1`**, **`scripts/test-vboomy-osc.ps1`**.
- LiveKit config accepts `?robot=` for room selection (`teleop-vboomy`).
- **[docs/MANIP_AND_HANDS.md](docs/MANIP_AND_HANDS.md)** — WebXR hands vs Pico body trackers vs encoders.

### Added (LeRobot)

- **`export_lerobot.py`** + **`scripts/export-lerobot.ps1`** — JSONL → LeRobot v2.1 parquet (`pyarrow`).
- **`POST /api/v1/recording/export`** — HTTP export with `lerobot-train` hint in response.
- **[docs/LEROBOT.md](docs/LEROBOT.md)** — full capture + export + train path (all robots including vboomy).

### Added (infra)

- **GitHub Actions CI** (`.github/workflows/ci.yml`) — `windows-latest` only: `pytest` + webapp `npm run check`.
- **`just ci`** — local mirror of the workflow.

## [0.1.0] - 2026-06-02

- Initial alpha: WebXR pose gateway, Boomy adapter, arbiter/M3, LeRobot JSONL, LiveKit publisher (M5).

