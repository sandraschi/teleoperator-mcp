# Teleoperator MCP — Build Log

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
