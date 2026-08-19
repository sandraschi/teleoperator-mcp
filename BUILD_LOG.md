# Teleoperator MCP — Build Log

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
- CI `ci.yml` (previously **zero runs**) — will verify post-push.
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
