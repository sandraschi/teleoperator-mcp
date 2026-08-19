# Teleoperator MCP — Build Log

## 2026-08-19 — round 4: LiveKit egress sink (T3.3 complete)

- `recording/egress.py`: ring-buffer frame sink fed by the publisher (mjpeg + snapshot loops); recorder matches to teleop frames, saves `images/observation.image/`, writes `observation.image.image` column.
- Export carries image columns into parquet + copies images into chunked layout + declares `info.json` feature (video_path set when images exist).
- `GET /api/v1/livekit/egress` + `GET /api/v1/episodes/{idx}/image/{frame}` (path-traversal guarded); webapp Episodes thumbnail.
- Env: `TELEOP_LIVEKIT_EGRESS_ENABLED/TOLERANCE_MS/INTERVAL`.
- 9 new tests (`tests/test_egress.py`); 73 total, 63% cov. Gates green.

## 2026-08-19 — round 3: VLA fleet control tower (12 features)

### Tier 1 (safety/production)
- Operator claim/auth: `auth.py`, claim/release/claims REST, WS token gate, Home claim UI. estop open.
- Presence deadman: WS `presence` pulse + server-side estop on lapse.
- `teleop_task_dispatch` + WaypointProducer + tasks.py (forward/reverse/turn/approach/sweep). VLA branch hardware-gated.

### Tier 2 (Mode-B arc)
- SHARED mode in arbiter (confidence blend), `VLA_ID` owner for manip AUTO.
- Fake-VLA producer + `tests/test_tier12.py` (10 tests: claim, waypoint, blend, task gate, endpoints).
- Episode library REST + webapp Episodes page (replay + curation labels).

### Tier 3 (fleet/UX)
- Ops console REST + webapp Ops page (multi-robot supervision; drive single-session by design).
- Video/hub export: `scripts/publish-lerobot-hub.py` (refuses observation-less datasets; `--push`).

### Tier 4 (polish)
- Voice LLM fallback (Ollama) for free-form commands; estop stays keyword-gated.
- `scripts/latency-bench.py` motion-to-command benchmark.
- `docs/CONTROLLER_SWAP.md` weekend guide.
- **VLA Fleet Control Tower** concept doc in mcp-central-docs + README crosslink.

### Gates
- 64 tests pass (63% cov), ruff 0, pyright 0, biome/tsc/build green.

## 2026-08-19 — assfix round 2 (voice control + remainder)

### Voice control via speech-mcp STT (fleet voice command bus)
- `teleop_voice_command` MCP tool — maps STT transcripts to domain actions (estop, takeover, mode, gaze, LiveKit, status) via deterministic keyword rules (`src/teleoperator_mcp/voice_commands.py`)
- `POST /api/v1/teleop/voice` REST mirror (VoiceCommandBody)
- Registered `teleop` entity + handlers in `mcp-central-docs/config/voice_command_bus.yaml`; `teleoperator` server added to fleet-agent `FLEET_SERVERS` (http://127.0.0.1:10901/mcp)
- Tests: `tests/test_voice_commands.py` (11 tests)
- Tool lists updated in `/api/capabilities`, `/api/v1/diagnostics`, README, llms-full.txt, docs/TOOLS.md

### Onboarding (ONBOARDING_STANDARD.md)
- `docs/ONBOARDING.md` created (what/cost/prereqs/steps/pitfalls/sanity/declared doubles)
- `INSTALL.md` created with ONBOARDING link near top; README doc-table row added
- Health `onboarding.configured` signal (yahboom-mcp probe at `/api/v1/health`)
- Webapp: red under-hero `onboarding-cue` CTA + MOCK-until-onboarded banner/badges (`mock-data-banner`, `mock-badge`), clears when configured

### bun (fleet BUN_STANDARDS)
- `bun install` migrated lockfile; `bun.lock` committed, `package-lock.json` removed + gitignored
- CI: `oven-sh/setup-bun@v2` + `bun install --frozen-lockfile`; justfile bootstrap/web/dev/lint/ci use bun; start.ps1 + e2e-start-all.ps1 use bun

### Webapp SOTA remainder
- FloatingChat provider/model wired to Zustand `useLlmStore` (no duplicate localStorage state)
- Inbox + Skills pages added (catch-them-all complete), nav + routes + page titles
- SettingsPage loading/empty/error states + Re-scan button
- Ctrl+K focuses log search (Ctrl+L logger, Ctrl+H help already in place)

### LOW items
- `renovate.json` added (fleet template)
- `.agents/skills/` Antigravity session-start skill + config.json
- ghaudit run: `reports/ghaudit-2026-08-19.md` + `.ghaudit-timestamp` (repo clean: 0 issues, 0 PRs, 16 topics, public)

## 2026-08-19 — assfix pass

### Assessment
- Score: **-73/100 (runt)** before fixes. CRITICAL 1, HIGH 8, MEDIUM 22, LOW 6.
- Full report: `reports/assess-2026-08-19.md`.

### CRITICAL / HIGH fixes
- `.gitignore`: added `mcpb/src/` (stale tracked bundle **untracked**), `*.bak.*`, `*.bak-*`, `*.mcpb`; deleted all `.bak*` dross from disk.
- Pre-commit hook installed (`uv run pre-commit install`).
- MCPB prompts rewritten to 3-4-100 (system 3279w / user 4111w / 111 examples) — verified PASS.
- `.mcpbignore` completed (webapp/, data/, *.bak*); `mcpb-pack.ps1` now fresh-stages `src/<pkg>` -> `mcpb/src/<pkg>` before pack.
- Webapp docs/ stack created: `CONFIGURATION.md`, `DEVELOPMENT.md`, `TOOLS.md`, `TROUBLESHOOTING.md`.
- Biome wired: `webapp/biome.json`, `lint`/`biome:ci` scripts, CI step — all green.
- CI `ci.yml` had **zero runs** because Actions was **disabled at repo level** on a public repo. Re-enabled via `gh api -X PUT /actions/permissions {"enabled": true}`; workflow_dispatch run **PASSED** (ruff/format/pyright/pytest/tsc/biome/build, 1m46s). Ruff `per-file-ignores` added for `scripts/*.py`/`run_server.py` so the pre-commit T201 gate passes repo-wide.
- Webapp docs and README/llms-full synced.

### MEDIUM fixes
- Backend: `GET /api/skills` + `SKILLS` catalog, `SkillsDirectoryProvider` + skill dir, GPU detection in `/api/llm/providers`, `_error_response()` helper, `output_schema` on teleop_status, `/api/fleet/apps`, capabilities skills/prompts/resources flags, phantom `teleop_export_recording` removed, swallowed except fixed.
- Testing: pytest-cov gate `>=50%` (61%), Playwright config + e2e/navigation.spec.ts + idempotent e2e-start-all.ps1, `tests/test_server_routes.py`.
- Webapp: `useTauriBackendListener`, zoom levels 0.5-3.0 + Ctrl+0 + % indicator, Ctrl+L/Ctrl+H, 5 personalities + 6 examples, data-testid across Tools/Logs/Apps/Help, AppsPage dynamic `/api/fleet/apps` with experimental section, GPU status + opportunity prompt, font/contrast fixes.
- Tauri: `cua-nsis-config.json` nav_routes added, feature_smoke_path corrected.
- justfile: `types`, `gates-green`, biome in lint/ci.
- MCPB manifest `tools` + glama fastmcp version corrected.

### Gates after fixes
- ruff check 0, ruff format 0, pyright 0, pytest 42 pass (61% cov), tsc 0, biome 0, webapp build OK (Tailwind 22.8 kB).

### Known issues
- Playwright e2e is stable in a fresh CI stack; reusing a long-running dev Vite server makes some runs flaky (retry passes). `reuseExistingServer: true` + idempotent start script mitigates.
- `free_port` in backend.rs is single-layer (taskkill) — matches the aiwatcher fleet reference; multi-layer UAC + 240s poll not added.
- Webapp uses npm not bun — internally consistent (CI, package-lock.json), bun conversion deferred.
- Onboarding: docs/BRINGUP.md covers hardware bring-up; dedicated ONBOARDING.md + red CTA not shipped (WebXR client, hardware-optional via vboomy).

## 2026-06-25 — Fleet SOTA upgrade

### Changes

- **.env → .env.example**: Updated `native/tauri.conf.json` line 29 to bundle `resources/.env.example`. Updated `native/build.ps1` to Copy-Item `.env.example` instead of `.env`. Verified `.env.example` exists at repo root.
- **hooks.nsh**: Replaced with fleet-standard NSIS hook pattern: `KillFleetProcesses` macro (Stop-Process + taskkill + nsis_tauri_utils::KillProcessCurrentUser), `UninstallPrevious` macro (HKLM/HKCU registry check), Sleep 3000 after kill.
- **build.ps1**: Added Step 0 port freeing, API_BASE port verification (greps :10901 in api.ts), >=5MB size gate on PyInstaller output, frozen binary smoke test with ephemeral port 11999, .env.example bundling.
- **llms-full.txt**: Created at repo root — 80+ lines covering all 11 MCP tools, 20+ REST endpoints, 30 env vars, architecture, robot adapters, run instructions, troubleshooting, fleet integration.
- **BUILD_LOG.md**: Created as running record.
- **Backend (/api/v1/diagnostics)**: Added diagnostics endpoint returning status, version, uptime, tool_count (11), tools list, system info, errors, robot catalog. Required by CUA-NSIS smoke testing standard.
- **Backend (Prefab App)**: Registered `show_teleop_status_card` — PrefabApp tool for robot status and connection health. Uses prefab-ui for rich card rendering.
- **glama.json**: Updated tool count to 11, fastmcp to 3.3+.
- **Webapp**: (pending) Install fleet stack, Tailwind config, data-testid on dashboard, exponential backoff, Zustand store, useZoom hook.

### Known issues

- Webapp npm install pending (requires node_modules access).
- Webapp Tailwind migration pending.
