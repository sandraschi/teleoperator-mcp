# Development

This document explains how to work on the teleoperator-mcp codebase: repo layout, how to run
the gates, how to test, and the conventions to follow.

## Repo layout

```
src/teleoperator_mcp/
  server.py        Unified FastAPI + FastMCP gateway (tools, REST, WebSocket)
  config.py        pydantic-settings (TELEOP_ prefix)
  auth.py          Operator claim/token registry (WS gate; estop open)
  tasks.py         Language goal -> AUTO waypoint plan (teleop_task_dispatch)
  voice_commands.py STT transcript -> domain action keyword parser
  activity_log.py  Ring-buffer logger + REST query/export/clear
  safety.py        Watchdog, estop latch, AUTO timer, presence deadman
  speech.py        Spoken warnings (speech-mcp / SAPI fallback)
  runtime.py       Robot catalog + shared arbiter/VLA/waypoint singletons
  types.py         Shared types
  adapters/        Robot adapters (boomy, bumi, vboomy) + registry
  arbiter/         Authority arbiter (DIRECT/AUTO/SHARED) core + state
  mappers/         Pose/controller -> command mappers per robot
  producers/       ProducerCommand producers (human_pose, nav_stub, waypoint, fake_vla)
  recording/       LeRobot JSONL recording + export + egress frame sink
  ws/              WebSocket teleop handler
  livekit/         LiveKit publisher, tokens, MJPEG source
webapp/            React + Vite + Three.js WebXR client
native/            Tauri 2.0 desktop shell (NSIS installer)
scripts/           Bench, CUA smoke, latency bench, hub publish, fleet start helpers
tests/             Pytest suite
docs/              Architecture and domain documentation
```

## Prerequisites

- Python 3.12+ and uv
- [bun](https://bun.sh) (fleet JS package manager for the webapp)
- just (fleet task runner) — optional but recommended
- For native builds: Rust toolchain + Tauri CLI

## First-time setup

```powershell
just bootstrap
```

This runs `uv sync --all-extras`, `bun install` in `webapp/`, and `pre-commit install`.

## Gates

The fleet five-gate shape: ruff (style), pyright (types) + tsc (types), pytest (behavior).

```powershell
just lint       # ruff check + tsc + biome
just fmt        # ruff format
just test       # pytest tests/
just ci         # uv sync + pytest + bun install + check + biome (matches CI)
```

Run everything by hand:

```powershell
uv run ruff check src/
uv run ruff format src/ --check
uv run pyright src/
uv run pytest tests/ -q
Set-Location webapp; bun run check
Set-Location webapp; bun run biome:ci
```

## Tests

The pytest suite covers adapters, arbiter, mappers, recording, LiveKit tokens, safety, and
the registry. The LiveKit token test emits an `InsecureKeyLengthWarning` because it uses a
short dev key — that is expected and not a failure.

Integration test against a live stack (backend must be running):

```powershell
just integration-test
```

## Conventions

- FastMCP 3.4.4+; never downgrade.
- Tools return `{success, message, ...}` with natural-language messages and documented
  `## Return Format` / `## Examples` docstrings.
- Tool parameters use `Annotated[T, Field(description=...)]`, not `Args:` blocks.
- Tools carry annotations (`READ_ONLY` / `MUTATING` / `DESTRUCTIVE`).
- Logging uses `logging.getLogger(...)`; error paths use `logger.exception` inside
  `except` blocks. No bare `print()` in server code (ruff T201 enforces this).
- No Pydantic v1 methods (`.dict()`, `.json()`, `parse_obj`). Use `.model_dump()` /
  `.model_dump_json()` / `.model_validate()`.
- Session context injection lives in `.claude-plugin/`, `.cursorrules`, `.windsurfrules`,
  `.github/copilot-instructions.md`, and `.opencode/skills/session-context/`. Keep them in
  sync when tools change.

## Pre-commit

`.pre-commit-config.yaml` runs ruff (+format) and a local Biome hook when the webapp is
present. The hook is installed by `just bootstrap`. Check it with:

```powershell
uv run pre-commit run --all-files
```

## CI

`.github/workflows/ci.yml` runs on Windows: uv sync, ruff check, ruff format check, pyright,
pytest, `bun install`, `bun run check`, and `bun run build`. Local equivalent: `just ci`.

## Adding a tool

1. Add the `@mcp.tool` in `src/teleoperator_mcp/server.py` with `## Return Format` and
   `## Examples` docstrings, annotations, and an `Annotated`-style signature.
2. If it needs a REST mirror, add the FastAPI route under `/api/v1/`.
3. Add it to `/api/capabilities` and `/api/v1/diagnostics` tool lists.
4. Update `README.md` tools table, `llms-full.txt`, and the session-context prompts if the
   tool is a supervisor entry point.
5. Add a test under `tests/`.

## Adding a robot adapter

1. Implement the adapter in `src/teleoperator_mcp/adapters/` (see `base.py` for the
   interface and `boomy.py` for the reference implementation).
2. Register it in `registry.py`.
3. Add a mapper in `src/teleoperator_mcp/mappers/` if it maps poses differently.
4. Add `TELEOP_*` settings in `config.py` for its URL and gains.
5. Add it to `runtime.py` catalog, `llms-full.txt`, and the webapp robot list.

## Adding a producer (autonomy under the arbiter)

Producers emit `ProducerCommand` keyed by actuator group; the arbiter forwards only the
owning producer's command per group.

1. Implement a producer in `src/teleoperator_mcp/producers/` (see `nav_stub.py` and
   `fake_vla.py` for reference). It must expose `tick() -> ProducerCommand` and
   `reset_plan()` (hand-back replan).
2. Register it in `runtime.py` and thread it into the `AuthorityArbiter`.
3. To make it selectable, add an owner branch in `arbiter/core.py` `_resolve_group_*` and a
   mode path in `tasks.py` if it should respond to `teleop_task_dispatch`.
4. Out-of-process VLA producers are clients speaking the same `ProducerCommand` schema over
   the fleet bridge (`vla-mcp`); the in-process `FakeVlaProducer` is the test stand-in.

## Debugging

- Backend logs stream to the console (start.ps1 window) and the `/api/logs` ring buffer.
- The webapp health dot uses exponential backoff against `/api/v1/health`.
- `GET /api/v1/diagnostics` dumps tool list, system info, and errors for smoke tests.
- `scripts/ws-integration-harness.py` drives the pose pipeline headlessly.
