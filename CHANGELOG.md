

## [Unreleased] — 2026-08-19 (round 3: VLA fleet control tower)

### Added
- **Operator claim/auth (safety):** `POST /api/v1/session/claim` + `release` + `claims`; WS teleop requires a claim token (`TELEOP_REQUIRE_CLAIM`); estop stays unauthenticated. Webapp claim UI on Home.
- **Presence deadman:** headset `presence` pulse over WS; estop when it lapses (`TELEOP_PRESENCE_TIMEOUT_S`).
- **`teleop_task_dispatch(goal)`** + `POST /api/v1/teleop/task`: language goal -> AUTO waypoint plan (forward/reverse/turn/approach/sweep); manipulation goals hardware-gated. WaypointProducer added.
- **SHARED mode** in the arbiter (confidence-blended human+auto base command).
- **Fake-VLA producer** harness + tier tests (producer contract, blend, waypoint, handoff).
- **Episode library:** `GET /api/v1/episodes` + `/{idx}` + `/curate`; webapp Episodes page (replay + keep/reject/uncertain).
- **Ops console:** `GET /api/v1/supervision` + webapp Ops page (multi-robot claim/reachability; drive stays single-session).
- **Voice LLM fallback:** free-form voice falls back to Ollama (`TELEOP_VOICE_LLM_MODEL`) when keyword rules miss; estop stays keyword-gated.
- **Latency benchmark:** `scripts/latency-bench.py` (motion-to-command p50/p90/p99).
- **Hub export:** `scripts/publish-lerobot-hub.py` (refuses observation-less datasets).
- **Controller-swap guide:** `docs/CONTROLLER_SWAP.md`.
- **VLA Fleet Control Tower crosslink:** `mcp-central-docs/patterns/VLA_FLEET_CONTROL_TOWER.md` + README section.

### Changed
- Webapp nav: added Ops + Episodes pages; claim gate blocks Enter VR until claimed.

## [Unreleased] — 2026-08-19 (assfix)

### Added
- `GET /api/skills` endpoint + `SKILLS` catalog (chat skill-first loading, was 404)
- `SkillsDirectoryProvider` with `src/teleoperator_mcp/skills/teleop-supervision/SKILL.md`
- GPU detection in `GET /api/llm/providers` (nvidia-smi) + Settings page GPU status + opportunity prompt
- `output_schema` on `teleop_status`; `_error_response()` helper; skills/prompts/resources now flagged in `/api/capabilities`
- Webapp: `useTauriBackendListener` (backend-status event + HTTP poll fallback), Tauri zoom levels 0.5-3.0 + Ctrl+0 reset, 4th personality + Custom, 6 example prompts, data-testid on Tools/Logs/Apps/Help pages, GPU status testid, font/contrast fixes
- Biome: `webapp/biome.json`, `lint`/`lint:fix`/`biome:ci` scripts, CI step
- Playwright: `webapp/playwright.config.ts`, `e2e/navigation.spec.ts`, `e2e-start-all.ps1` (idempotent reuse), `e2e` script
- Coverage gate: pytest-cov with `--cov-fail-under=50`
- `docs/CONFIGURATION.md`, `docs/DEVELOPMENT.md`, `docs/TOOLS.md`, `docs/TROUBLESHOOTING.md`
- `just types`, `just gates-green`
- MCPB 3-4-100 prompts rewritten (system 3.2k / user 4.1k words, 111 examples); `.mcpbignore` + `mcpb-pack.ps1` fresh-stage (wipe+recopy src -> mcpb/src)
- CUA NSIS config: `nav_routes` added, `feature_smoke_path` corrected to `/api/v1/diagnostics`
- Tests: `tests/test_server_routes.py` (42 total, 61% coverage)

### Fixed
- `.gitignore`: `mcpb/src/` (tracked stale bundle untracked), `*.bak.*`, `*.bak-*`, `*.mcpb`
- `teleop_export_recording` phantom entry removed from `/api/capabilities` tool surface (12 real tools)
- `llm_providers` swallowed `except Exception: pass` -> `logger.warning(exc_info=True)`
- Pre-commit hook installed (`uv run pre-commit install`)

## [Unreleased] — 2026-08-03 (session 2)

### Added
- LiveKit SFU is now a **Windows service** (`LiveKitSFU`, NSSM, native livekit-server 1.7.0 + teleconference-mcp/livekit.yaml, auto-start, crash-restart). Docker no longer required for video return
- `scripts/ws-integration-harness.py` + `just integration-test` — headless WS harness proving the pose pipeline against the live stack (12 checks: handshake, acks, estop, authority, recording on disk, watchdog)
- `scripts/start-stack-detached.ps1`, `scripts/launch-*.cmd` — detached stack launchers
- `scripts/install-livekit-service.ps1` / `scripts/start-livekit-service.ps1` — NSSM service install/start (elevated)

### Fixed
- Tool docstrings: `## Return Format` corrected to match actual handler shapes (verified against ws/handler.py, arbiter, livekit publisher) — `teleop_status`, `teleop_estop`, `teleop_set_mode`, `teleop_takeover`, livekit tools

### Verified
- LiveKit publisher connects to the SFU service: room `teleop-boomy`, participant `teleop-publisher`, video track `boomy-camera` 640x480 VP8 published (WebRTC over Tailscale). MJPEG → snapshot fallback degrades correctly when Boomy camera is off
- Headless harness 12/12 vs live stack; drive/gaze commands reach yahboom-mcp (503 when robot offline, correct)

## [Unreleased] — 2026-08-03 (session 1)

### Added
- `teleop_shutdown` MCP tool + `POST /api/shutdown` REST endpoint for graceful server termination
- `CLAUDE.md` — agent instructions for Claude Code / opencode
- `.claude-plugin/plugin.json` + `hooks/hooks.json` — session context injection for Claude Code
- `run_server.py` — PyInstaller dual-transport entry point (MCP_PORT → HTTP, fallback → stdio)

### Fixed
- CORS: added `tauri://localhost`, `http://tauri.localhost`, `https://tauri.localhost` origins
- CORS: added unconditional `allow_origin_regex` for Tailscale `*.ts.net` + LAN IPs
- `@tauri-apps/api` moved from devDependencies to dependencies (required for Tauri WebView)
- Tool docstrings: added `## Return Format` and `## Examples` to all 10 tools
- Tool params: added `Annotated[T, Field(description="...")]` annotations
- `glama.json`: FastMCP version corrected from 3.3 to 3.4, tool count 11→12
- `llms.txt`: added link to `llms-full.txt`
- pyright: 0 errors (fixed 8 pre-existing type errors in vboomy, human_pose, PrefabApp)

### Changed
- `.gitignore`: added `reports/` directory

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
