#!/usr/bin/env python3
"""Teleoperator MCP - Unified Gateway (FastAPI + FastMCP + WebSocket)."""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import uvicorn
from fastapi import FastAPI, Query, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastmcp import FastMCP
from fastmcp.server.providers.skills import SkillsDirectoryProvider
from pydantic import BaseModel, Field

from .activity_log import (
    SortOrder,
    clear_logs,
    export_logs,
    install_log_handler,
    log_activity,
    log_stats,
    query_logs,
)
from .adapters.registry import list_robots
from .auth import claim_robot, list_claims, release_claim
from .config import cors_origins_list, settings
from .livekit import (
    get_publisher,
    issue_subscriber_token,
    livekit_public_config,
    start_publisher,
    stop_publisher,
)
from .recording.recorder import curate_episode, get_episode, list_episodes
from .runtime import get_waypoint, robots_catalog
from .tasks import build_plan, plan_display
from .voice_commands import parse_voice_command
from .ws.handler import (
    disconnect_all,
    session_stats,
    teleop_websocket,
    trigger_estop,
    trigger_gaze_center,
    trigger_set_gaze,
    trigger_set_mode,
    trigger_takeover,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("teleoperator-mcp")

start_time = time.time()
mcp = FastMCP("Teleoperator MCP")

_skills_dir = Path(__file__).resolve().parent / "skills"
if _skills_dir.is_dir():
    mcp.add_provider(SkillsDirectoryProvider(roots=[_skills_dir]))

_READ_ONLY = {"readonly": True}
_MUTATING = {}
_DESTRUCTIVE = {}


def _error_response(message: str, **extra) -> dict:
    """Build a {success, message} failure dict and log the exception in flight."""
    logger.exception(message)
    return {"success": False, "message": message, **extra}


SKILLS: list[dict] = [
    {
        "name": "teleop-supervision",
        "description": (
            "Supervise a WebXR teleoperation session: check status, video return, "
            "authority, and react to hazards."
        ),
    },
    {
        "name": "robot-catalog",
        "description": (
            "List the available robot adapters (boomy, bumi, vboomy) and their capabilities."
        ),
    },
    {
        "name": "livekit-video-return",
        "description": ("Verify and control LiveKit video return for the teleop session."),
    },
]


@mcp.resource("teleop://status")
async def teleop_status_resource() -> str:
    """Live teleop session status as an MCP resource (pollable, no tool call needed)."""
    stats = session_stats()
    lines = [
        f"active={stats.get('active', False)}",
        f"frames_in={stats.get('frames_in', 0)}",
        f"robot={stats.get('robot', 'none')}",
        f"webxr={stats.get('has_webxr', False)}",
        f"mode={stats.get('authority', {}).get('base', 'IDLE')}",
        f"yahboom_api={settings.yahboom_api_url}",
    ]
    return "\n".join(lines)


@mcp.prompt()
def teleop_help(topic: str = "overview") -> str:
    """Teleoperation guidance prompt for supervisors and operators."""
    guides = {
        "overview": (
            "You are supervising a teleoperation session. Check teleop_status() for session "
            "state, teleop_livekit_status() for video return, and GET /api/v1/robots for the "
            "robot catalog. Use teleop_set_mode() to change authority, teleop_estop() for "
            "emergency stop, teleop_takeover() for human reclaim."
        ),
        "estop": (
            "Emergency stop procedure: call teleop_estop() immediately. It zeroes drive on all "
            "actuator groups. After the hazard clears, teleop_takeover() clears the latch."
        ),
        "livekit": (
            "Video return: teleop_livekit_status() shows publisher state. Start with "
            "teleop_livekit_publisher_start() if the camera feed is needed."
        ),
    }
    return guides.get(topic.lower(), guides["overview"])


TELEOP_STATUS_OUTPUT_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "success": {"type": "boolean"},
        "message": {"type": "string"},
        "active": {"type": "boolean"},
        "robot": {"type": "string"},
        "frames_in": {"type": "integer"},
        "uptime_s": {"type": "number"},
        "watchdog_latched": {"type": "boolean"},
        "estop_count": {"type": "integer"},
        "any_auto": {"type": "boolean"},
        "estop_latched": {"type": "boolean"},
        "yahboom_api": {"type": "string"},
    },
}


@mcp.tool(annotations=_READ_ONLY, output_schema=TELEOP_STATUS_OUTPUT_SCHEMA)
async def teleop_status() -> dict:
    """Active WebXR teleop session status (connection, frame count, robot target).

    ## Return Format
    {"success": bool, "message": str, "active": bool, "robot": str,
     "active_robot": str, "robots": dict, "recording": dict, "robot_id": str,
     "display_name": str, "frames_in": int, "last_frame_at": float|None,
     "uptime_s": float, "client": str|None, "watchdog_latched": bool,
     "estop_count": int, "auto_elapsed_s": float|None,
     "authority": {"base|gaze|manip": {"mode": str, "owner": str}, "estop_latched": bool},
     "groups_available": {"base": bool, "gaze": bool, "manip": bool},
     "any_auto": bool, "yahboom_api": str, "watchdog_ms": int}

    ## Examples
    teleop_status()
    """
    stats = session_stats()
    return {
        "success": True,
        "message": "Teleop session active" if stats["active"] else "No active teleop session",
        **stats,
        "yahboom_api": settings.yahboom_api_url,
        "watchdog_ms": settings.watchdog_ms,
    }


@mcp.tool(annotations=_MUTATING)
async def teleop_configure(
    max_linear: Annotated[float | None, Field(description="Linear speed cap (m/s)")] = None,
    max_angular: Annotated[float | None, Field(description="Angular speed cap (rad/s)")] = None,
    pan_gain: Annotated[float | None, Field(description="Camera pan gain factor")] = None,
    tilt_gain: Annotated[float | None, Field(description="Camera tilt gain factor")] = None,
    yahboom_api_url: Annotated[
        str | None, Field(description="Override yahboom-mcp REST URL")
    ] = None,
) -> dict:
    """Adjust teleop mapping gains and downstream robot API URL (runtime).

    ## Return Format
    {"success": bool, "message": str, "max_linear": float, "max_angular": float,
     "pan_gain": float, "tilt_gain": float, "yahboom_api_url": str}

    ## Examples
    teleop_configure(max_linear=0.2, pan_gain=90.0)
    teleop_configure(yahboom_api_url="http://192.168.1.100:10892")
    """
    if max_linear is not None:
        settings.max_linear = max_linear
    if max_angular is not None:
        settings.max_angular = max_angular
    if pan_gain is not None:
        settings.pan_gain = pan_gain
    if tilt_gain is not None:
        settings.tilt_gain = tilt_gain
    if yahboom_api_url is not None:
        settings.yahboom_api_url = yahboom_api_url.rstrip("/")
    return {
        "success": True,
        "message": "Teleop configuration updated",
        "max_linear": settings.max_linear,
        "max_angular": settings.max_angular,
        "pan_gain": settings.pan_gain,
        "tilt_gain": settings.tilt_gain,
        "yahboom_api_url": settings.yahboom_api_url,
    }


@mcp.tool(annotations=_DESTRUCTIVE)
async def teleop_estop() -> dict:
    """Hard stop: zero drive on all actuator groups. Operator/agent veto.

    ## Return Format
    {"success": bool, "message": str, "estop_count": int, "estop_latched": bool}

    ## Examples
    teleop_estop()
    """
    return await trigger_estop(reason="mcp")


@mcp.tool(annotations=_MUTATING)
async def teleop_set_mode(group: str, mode: str, confirm_bench: bool = False) -> dict:
    """Set actuator group authority: DIRECT (human) or AUTO (nav stub). Groups: base, gaze, manip.

    AUTO on base requires an active WebXR session unless confirm_bench=true (blocks only, timed stop).

    ## Return Format
    {"success": bool, "message": str, "confirm_bench": bool,
     "group": str, "mode": str, "owner": str}
    On failure: {"success": false, "message": str}

    ## Examples
    teleop_set_mode(group="base", mode="AUTO", confirm_bench=True)
    teleop_set_mode(group="gaze", mode="DIRECT")
    """
    return await trigger_set_mode(
        group=group.lower(), mode=mode.upper(), confirm_bench=confirm_bench
    )


@mcp.tool(annotations=_MUTATING)
async def teleop_takeover(group: str | None = None) -> dict:
    """Human reclaims authority on one group or all available groups. Clears estop latch.

    ## Return Format
    {"success": bool, "message": str, "takeover": [str], "estop_latched": bool}
    On failure: {"success": false, "message": str}

    ## Examples
    teleop_takeover()                        # reclaim all groups
    teleop_takeover(group="base")            # reclaim base only
    """
    g = group.lower() if group else None
    return await trigger_takeover(group=g)


@mcp.tool(annotations=_MUTATING)
async def teleop_set_gaze(pan: float, tilt: float) -> dict:
    """Move Boomy camera to absolute pan/tilt (0-180 deg, center ~90). Bench + head-follow prep.

    ## Return Format
    {"success": bool, "message": str, "pan": float, "tilt": float}

    ## Examples
    teleop_set_gaze(pan=90, tilt=90)         # center
    teleop_set_gaze(pan=120, tilt=60)         # look up-right
    """
    return await trigger_set_gaze(pan=pan, tilt=tilt)


@mcp.tool(annotations=_MUTATING)
async def teleop_gaze_center() -> dict:
    """Center camera servos (neutral head-follow reference).

    ## Return Format
    {"success": bool, "message": str, "pan": float, "tilt": float}

    ## Examples
    teleop_gaze_center()
    """
    return await trigger_gaze_center()


@mcp.tool(annotations=_READ_ONLY)
async def teleop_livekit_status() -> dict:
    """LiveKit video return status (publisher + room config).

    ## Return Format
    {"success": bool, "message": str, "config": dict,
     "enabled": bool, "running": bool, "connected": bool, "room": str,
     "identity": str, "frames_published": int, "last_frame_at": float|None,
     "last_error": str|None, "source": str, "width": int, "height": int,
     "mjpeg_url": str, "livekit_url": str}

    ## Examples
    teleop_livekit_status()
    """
    return {
        "success": True,
        "message": "LiveKit status",
        "config": livekit_public_config(),
        **get_publisher().status(),
    }


@mcp.tool(annotations=_MUTATING)
async def teleop_livekit_publisher_start() -> dict:
    """Start Goliath-side MJPEG to LiveKit publisher for Boomy camera.

    ## Return Format
    {"success": bool, "message": str, "enabled": bool, "running": bool,
     "connected": bool, "room": str, "frames_published": int, "last_error": str|None,
     "mjpeg_url": str, "livekit_url": str}

    ## Examples
    teleop_livekit_publisher_start()
    """
    result = await start_publisher()
    return result


@mcp.tool(annotations=_MUTATING)
async def teleop_livekit_publisher_stop() -> dict:
    """Stop LiveKit camera publisher.

    ## Return Format
    {"success": bool, "message": str, "enabled": bool, "running": bool,
     "connected": bool, "room": str, "frames_published": int, "last_error": str|None}

    ## Examples
    teleop_livekit_publisher_stop()
    """
    result = await stop_publisher()
    return result


@mcp.tool(annotations=_READ_ONLY)
async def show_teleop_status_card() -> dict:
    """Show Teleoperator robot status and connection health as a rich Prefab card.

    Renders a Prefab App card with robot catalog, session state, LiveKit status,
    and authority mode for each actuator group.

    ## Return Format
    PrefabApp card (in-chat rich UI) or dict fallback if prefab_ui unavailable.

    ## Examples
    show_teleop_status_card()
    """
    stats = session_stats()
    livekit = get_publisher().status()
    robots = list_robots()

    try:
        from prefab_ui import PrefabApp, ToolResult  # type: ignore[reportAttributeAccessIssue]

        card = PrefabApp()
        mode = stats.get("authority", {}).get("base", "IDLE")
        card.add_header("Teleoperator — Robot Status", subtitle=f"Mode: {mode}")  # type: ignore[reportAttributeAccessIssue]
        card.add_stat_grid(  # type: ignore[reportAttributeAccessIssue]
            [
                ("Active", "Yes" if stats.get("active") else "No"),
                ("Frames In", str(stats.get("frames_in", 0))),
                ("Robot", stats.get("robot", "none")),
                ("WebXR", "Connected" if stats.get("has_webxr") else "Idle"),
                ("LiveKit", "Running" if livekit.get("running") else "Stopped"),
            ]
        )
        robot_lines = []
        for rid, meta in robots.items():
            twin = "  virtual" if meta.get("virtual_twin") else ""
            robot_lines.append(f"{rid}: {meta.get('display_name', rid)}{twin}")
        if robot_lines:
            card.add_section("Available Robots")  # type: ignore[reportAttributeAccessIssue]
            for line in robot_lines:
                card.add_text(line)  # type: ignore[reportAttributeAccessIssue]
        return ToolResult(content=str(card), structured_content=card)
    except ImportError:
        return {
            "success": True,
            "message": "Teleoperator robot status",
            "session": stats,
            "livekit": livekit,
            "robots": robots,
        }


@mcp.tool(annotations=_DESTRUCTIVE)
async def teleop_shutdown(
    confirm: Annotated[bool, Field(description="Confirm shutdown — MUST be True")] = False,
) -> dict:
    """Gracefully shut down the teleoperator server.

    Stops LiveKit publisher, disconnects all WebXR clients, and terminates the process.

    ## Return Format
    {"success": bool, "message": str}

    ## Examples
    teleop_shutdown(confirm=True)
    """

    if not confirm:
        return {"success": False, "message": "Pass confirm=True to shut down the server"}
    await stop_publisher()
    await disconnect_all()
    logger.info("Teleoperator MCP shutting down via teleop_shutdown")
    import os

    os._exit(0)


@mcp.tool(annotations=_MUTATING)
async def teleop_voice_command(
    transcript: Annotated[
        str, Field(description="Spoken transcript from speech-mcp STT (e.g. 'emergency stop')")
    ],
) -> dict:
    """Execute a voice command from speech-mcp STT (estop, takeover, mode, gaze, LiveKit).

    Maps the spoken transcript to a deterministic teleop action: emergency stop,
    take over, center or pan the camera, start/stop LiveKit video, switch base/gaze
    between DIRECT and AUTO, or report status. No LLM on the hot path — keyword rules.

    ## Return Format
    {"success": bool, "message": str, "action": str, "result": dict}

    ## Examples
    teleop_voice_command(transcript="emergency stop")
    teleop_voice_command(transcript="take over")
    teleop_voice_command(transcript="set base to auto")
    teleop_voice_command(transcript="look left")
    teleop_voice_command(transcript="start video")
    """
    return await _execute_voice_command(transcript)


async def _voice_llm_fallback(transcript: str) -> dict | None:
    """Ask a local LLM (Ollama) to map free-form speech to a known teleop action.

    Returns None when no LLM is reachable or the model declines. Safety-critical
    verbs (estop etc.) are always handled by keyword rules upstream, never here.
    """
    import httpx

    prompt = (
        "Map this spoken teleop command to exactly one action from this list, "
        'reply with a single JSON object {"action": ..., "args": {...}}.\n'
        "Actions: estop, takeover, gaze_center, set_gaze (pan,tilt 0-180), "
        "set_mode (group base|gaze|manip, mode DIRECT|AUTO), livekit_start, "
        "livekit_stop, status.\n"
        f"Transcript: {transcript}"
    )
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "http://localhost:11434/api/generate",
                json={"model": settings.voice_llm_model, "prompt": prompt, "stream": False},
            )
            data = r.json()
            text = (data.get("response") or "").strip()
        if "estop" in text or "emergency" in text.lower():
            # Never let an LLM accidentally trigger estop from a mis-parse; estop is
            # keyword-gated upstream, and here we refuse to invent it.
            return None
        action_map = {
            "takeover": "takeover",
            "gaze_center": "gaze_center",
            "set_gaze": "set_gaze",
            "set_mode": "set_mode",
            "livekit_start": "livekit_start",
            "livekit_stop": "livekit_stop",
            "status": "status",
        }
        parsed_action = None
        for key in action_map:
            if key in text:
                parsed_action = action_map[key]
                break
        if not parsed_action:
            return None
        return await _dispatch_voice_action(parsed_action, {})
    except Exception:
        logger.debug("voice LLM fallback unavailable", exc_info=True)
        return None


async def _dispatch_voice_action(action: str, args: dict) -> dict:
    """Execute a resolved teleop action (shared by keyword + LLM-fallback paths)."""
    if action == "estop":
        result = await trigger_estop(reason="voice")
    elif action == "takeover":
        result = await trigger_takeover()
    elif action == "gaze_center":
        result = await trigger_gaze_center()
    elif action == "set_gaze":
        result = await trigger_set_gaze(**args)
    elif action == "set_mode":
        result = await trigger_set_mode(**args)
    elif action == "livekit_start":
        result = await start_publisher()
    elif action == "livekit_stop":
        result = await stop_publisher()
    elif action == "status":
        result = {"success": True, "message": "Session status", **session_stats()}
    else:  # pragma: no cover - guarded by callers
        return {"success": False, "message": f"Unhandled action '{action}'", "result": {}}

    return {
        "success": bool(result.get("success", True)),
        "message": result.get("message", action),
        "action": action,
        "result": result,
    }


async def _execute_voice_command(transcript: str) -> dict:
    """Shared voice-command dispatch for the MCP tool and REST mirror."""
    parsed = parse_voice_command(transcript)
    action = parsed.action

    if action == "unknown":
        # T4.1: LLM fallback — let a local LLM interpret free-form voice before giving up.
        # estop/safety keywords are handled upstream in parse_voice_command and never reach here.
        fallback = await _voice_llm_fallback(transcript)
        if fallback is not None:
            return fallback
        return {
            "success": False,
            "message": (
                f"Unrecognized voice command: '{transcript}'. Try: emergency stop, "
                "take over, center camera, look left/right/up/down, start/stop video, "
                "set base to auto/direct, status."
            ),
            "action": "unknown",
            "result": {},
        }

    return await _dispatch_voice_action(action, parsed.args)


async def dispatch_task(goal: str) -> dict:
    """Dispatch a language goal to the AUTO producer (waypoint plan or VLA)."""
    from .ws.handler import trigger_set_mode

    display = plan_display(goal)
    if display is None:
        return {
            "success": False,
            "message": (
                f"Unrecognized goal: '{goal}'. Try: forward, reverse, turn left/right, "
                "approach, sweep/scan/patrol, or a manipulation goal (fridge/can/grasp) "
                "on a dual-arm platform."
            ),
        }

    if display.startswith("vla"):
        return {
            "success": False,
            "message": (
                "VLA manipulation tasks are hardware-gated (wheeled dual-arm with a "
                "manip group + out-of-process producer). Base waypoint tasks work on Boomy."
            ),
        }

    plan = build_plan(goal)
    if not plan:
        return {"success": False, "message": f"No waypoint plan for '{goal}'"}

    mode_result = await trigger_set_mode("base", "AUTO")
    if not mode_result.get("success"):
        return {"success": False, "message": mode_result.get("message", "AUTO refused")}

    get_waypoint().dispatch(plan)
    summary = ", ".join(f"{w.duration_s}s@lin={w.linear}" for w in plan)
    return {
        "success": True,
        "message": f"Task dispatched: {display} ({summary})",
        "plan": display,
        "goal": goal,
        "mode": mode_result,
    }


@mcp.tool(annotations=_MUTATING)
async def teleop_task_dispatch(
    goal: Annotated[
        str, Field(description="Natural-language goal (e.g. 'approach slowly', 'sweep left')")
    ],
) -> dict:
    """Dispatch a language goal to the AUTO producer (waypoint nav now, VLA later).

    Accepts goals like "forward", "reverse", "turn left/right", "approach", "sweep",
    "scan", "patrol". Waypoint profiles run under AUTO base authority with the full
    safety stack (WebXR gate, AUTO timer, estop). Manipulation goals return a
    hardware-gated message until a dual-arm platform ships.

    ## Return Format
    {"success": bool, "message": str, "plan": str|None, "goal": str, "mode": dict}

    ## Examples
    teleop_task_dispatch(goal="approach slowly")
    teleop_task_dispatch(goal="sweep the room")
    teleop_task_dispatch(goal="open the fridge")  # hardware-gated (VLA)
    """
    return await dispatch_task(goal)


class LiveKitTokenBody(BaseModel):
    identity: str = Field(min_length=1, max_length=128)
    room: str | None = None
    name: str | None = None


class RecordingExportBody(BaseModel):
    input_dir: str | None = None
    output_dir: str | None = None
    episodes: list[int] | None = None
    overwrite: bool = False


_mcp_http = mcp.http_app(path="/")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    install_log_handler()
    log_activity("system", f"Teleoperator MCP starting on port {settings.port}", level="INFO")
    logger.info("Teleoperator MCP starting (port %s)", settings.port)
    async with _mcp_http.router.lifespan_context(_mcp_http):
        if settings.livekit_enabled and settings.livekit_auto_start_publisher:
            await start_publisher()
        yield
    await stop_publisher()
    await disconnect_all()
    logger.info("Teleoperator MCP shutdown complete")


app = FastAPI(title="Teleoperator MCP", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins_list(),
    allow_origin_regex=r"https?://(?:[a-zA-Z0-9-]+\.ts\.net|.*?\.tail-[a-f0-9]+\.ts\.net|tauri\.localhost|localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|100\.\d{1,3}\.\d{1,3}\.\d{1,3})(?::\d+)?$|^tauri://localhost$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_api_requests(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/api") and not path.startswith("/api/logs"):
        log_activity(
            "api",
            f"{request.method} {path} -> {response.status_code}",
            level="INFO" if response.status_code < 400 else "WARNING",
            meta={"method": request.method, "path": path, "status": response.status_code},
        )
    return response


@app.get("/api/logs")
async def logs_query(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    level: str | None = Query(None),
    kind: str | None = Query(None),
    search: str | None = Query(None),
    sort: str = Query("desc"),
    after_id: str | None = Query(None),
) -> dict:
    order: SortOrder = "asc" if sort == "asc" else "desc"
    return query_logs(
        limit=limit,
        offset=offset,
        level=level,
        kind=kind,
        search=search,
        sort=order,
        after_id=after_id,
    )


@app.get("/api/logs/stats")
async def logs_stats() -> dict:
    return log_stats()


@app.get("/api/logs/export")
async def logs_export(
    format: str = Query("json"),
    level: str | None = Query(None),
    kind: str | None = Query(None),
    search: str | None = Query(None),
    sort: str = Query("desc"),
) -> Response:
    order: SortOrder = "asc" if sort == "asc" else "desc"
    fmt = format if format in ("json", "csv") else "json"
    body, media_type, filename = export_logs(
        format=fmt,
        level=level,
        kind=kind,
        search=search,
        sort=order,
    )
    return Response(
        content=body,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.delete("/api/logs")
async def logs_clear() -> dict:
    clear_logs()
    log_activity("system", "Log buffer cleared", level="WARNING")
    return {"success": True}


@app.post("/api/v1/teleop/set_mode")
async def api_teleop_set_mode(
    group: str,
    mode: str,
    confirm_bench: bool = False,
) -> dict:
    """REST mirror of teleop_set_mode for bench scripts (hits live server state)."""
    return await trigger_set_mode(
        group=group.lower(), mode=mode.upper(), confirm_bench=confirm_bench
    )


@app.post("/api/v1/teleop/estop")
async def api_teleop_estop() -> dict:
    return await trigger_estop(reason="api")


@app.post("/api/v1/teleop/takeover")
async def api_teleop_takeover() -> dict:
    return await trigger_takeover()


@app.post("/api/v1/teleop/gaze")
async def api_teleop_gaze(pan: float, tilt: float) -> dict:
    return await trigger_set_gaze(pan=pan, tilt=tilt)


@app.post("/api/v1/teleop/gaze/center")
async def api_teleop_gaze_center() -> dict:
    return await trigger_gaze_center()


class VoiceCommandBody(BaseModel):
    transcript: str = Field(min_length=1, max_length=500)


@app.post("/api/v1/teleop/voice")
async def api_teleop_voice(body: VoiceCommandBody) -> dict:
    """REST mirror of teleop_voice_command — STT transcripts from speech-mcp or the bus."""
    return await _execute_voice_command(body.transcript)


@app.get("/api/v1/robots")
async def api_robots() -> dict:
    """Available teleop adapters (?robot= route)."""
    return {"robots": robots_catalog()}


class ClaimBody(BaseModel):
    operator_id: str = Field(min_length=1, max_length=64)
    robot_id: str = Field(min_length=1, max_length=32)


class ReleaseBody(BaseModel):
    token: str = Field(min_length=8, max_length=128)


@app.post("/api/v1/session/claim")
async def api_session_claim(body: ClaimBody) -> dict:
    """Claim a robot for an operator — returns the WS token (estop stays open)."""
    return claim_robot(body.operator_id, body.robot_id)


@app.post("/api/v1/session/release")
async def api_session_release(body: ReleaseBody) -> dict:
    return release_claim(body.token)


@app.get("/api/v1/session/claims")
async def api_session_claims() -> dict:
    return {"claims": list_claims()}


@app.get("/api/v1/supervision")
async def api_supervision() -> dict:
    """Multi-robot supervision view: claim + reachability per robot (drive is single-session)."""
    from .auth import list_claims
    from .ws.handler import session_stats

    claims = list_claims()
    robots = robots_catalog()
    rows = []
    for rid, meta in robots.items():
        if meta.get("status") != "available":
            continue
        claim = claims.get(rid)
        rows.append(
            {
                "robot_id": rid,
                "display_name": meta.get("display_name", rid),
                "virtual_twin": meta.get("virtual_twin", False),
                "claimed": claim is not None,
                "operator_id": claim.get("operator_id") if claim else None,
                "claimed_at": claim.get("claimed_at") if claim else None,
            }
        )
    stats = session_stats()
    return {
        "robots": rows,
        "active": stats.get("active", False),
        "active_robot": stats.get("active_robot"),
        "require_claim": settings.require_claim,
    }


class TaskDispatchBody(BaseModel):
    goal: str = Field(min_length=1, max_length=300)


@app.post("/api/v1/teleop/task")
async def api_teleop_task(body: TaskDispatchBody) -> dict:
    """Dispatch a language goal to the AUTO producer (waypoint or VLA)."""
    return await dispatch_task(body.goal)


@app.get("/api/v1/livekit/config")
async def api_livekit_config(robot: str | None = Query(default=None)) -> dict:
    """Public LiveKit connection info for WebXR client (no secrets)."""
    return livekit_public_config(robot=robot)


@app.post("/api/v1/livekit/token")
async def api_livekit_token(body: LiveKitTokenBody) -> dict:
    """Subscribe-only JWT for headset browser (teleconference-mcp-compatible keys)."""
    if not settings.livekit_enabled:
        return {"success": False, "message": "LiveKit disabled"}
    room = (body.room or settings.livekit_room).strip()
    try:
        token = issue_subscriber_token(room=room, identity=body.identity.strip(), name=body.name)
    except RuntimeError as exc:
        return {"success": False, "message": str(exc)}
    return {
        "success": True,
        "token": token,
        "url": settings.livekit_public_url or settings.livekit_url,
        "room": room,
    }


@app.get("/api/v1/livekit/status")
async def api_livekit_status() -> dict:
    return {"success": True, **get_publisher().status(), "config": livekit_public_config()}


@app.post("/api/v1/livekit/publisher/start")
async def api_livekit_publisher_start() -> dict:
    return await start_publisher()


@app.post("/api/v1/livekit/publisher/stop")
async def api_livekit_publisher_stop() -> dict:
    return await stop_publisher()


@app.post("/api/v1/recording/export")
async def api_recording_export(body: RecordingExportBody | None = None) -> dict:
    """Export JSONL teleop sessions to LeRobot v2.1 parquet."""
    from .recording.export_lerobot import export_lerobot_dataset, export_summary

    req = body or RecordingExportBody()
    input_dir = req.input_dir or settings.recording_dir
    output_dir = req.output_dir or str(Path(settings.recording_dir).parent / "lerobot_export")
    result = export_lerobot_dataset(
        input_dir,
        output_dir,
        episode_indices=req.episodes,
        fps=settings.recording_fps,
        overwrite=req.overwrite,
    )
    return export_summary(result)


class CurateBody(BaseModel):
    label: str = Field(min_length=1, max_length=32)
    note: str = Field(default="", max_length=500)


@app.get("/api/v1/episodes")
async def api_episodes() -> dict:
    """List finalized episodes for replay/curation (T2.3)."""
    return {"episodes": list_episodes()}


@app.get("/api/v1/episodes/{episode_index}")
async def api_episode_detail(episode_index: int) -> dict:
    """One episode including its frames (replay)."""
    ep = get_episode(episode_index)
    if ep is None:
        return {"success": False, "message": f"No episode {episode_index}"}
    return {"success": True, "episode": ep}


@app.post("/api/v1/episodes/{episode_index}/curate")
async def api_episode_curate(episode_index: int, body: CurateBody) -> dict:
    """Attach a curation label + note to an episode."""
    return curate_episode(episode_index, body.label, body.note)


@app.get("/api/skills")
async def api_skills() -> list[dict]:
    """Available supervisor skills for the chat page (skill-first composition)."""
    return SKILLS


@app.get("/api/fleet/apps")
async def fleet_apps() -> dict:
    """Fleet Apps Hub catalog — local MCP webapps on Goliath.

    The AppsPage fetches this on mount and re-legates unknown entries to an
    Experimental section. Entries are the fleet registry snapshot; unknown
    apps discovered here are classified by the client.
    """
    apps = [
        {
            "name": "teleoperator-mcp",
            "port": 10900,
            "desc": "WebXR teleop gateway (this app)",
            "url": "/",
            "known": True,
        },
        {
            "name": "yahboom-mcp",
            "port": 10892,
            "desc": "Boomy ROS 2 robot control",
            "url": "http://localhost:10892",
            "known": True,
        },
        {
            "name": "devices-mcp",
            "port": 10870,
            "desc": "Fleet device inventory",
            "url": "http://localhost:10870",
            "known": True,
        },
        {
            "name": "bookmarks-mcp",
            "port": 10880,
            "desc": "Browser bookmarks + fleet docs RAG",
            "url": "http://localhost:10880",
            "known": True,
        },
        {
            "name": "mcp-central-docs",
            "port": None,
            "desc": "Pico revive pack, WEBXR, teleop runbooks",
            "url": "https://github.com/sandraschi/mcp-central-docs/tree/main/pico",
            "known": True,
        },
    ]
    return {"apps": apps}


@app.get("/api/llm/providers")
async def llm_providers() -> dict:
    import httpx

    models: list[str] = []
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get("http://localhost:11434/api/tags")
            for m in r.json().get("models", []):
                name = m.get("name", "")
                if name:
                    models.append(name)
    except Exception:
        logger.warning("Ollama probe failed - local LLM unavailable", exc_info=True)
    return {
        "providers": [{"name": "ollama", "models": models}],
        "gpu": _gpu_detect(),
    }


def _gpu_detect() -> dict | None:
    """Detect an NVIDIA GPU via nvidia-smi (used for the local-LLM opportunity prompt)."""
    import shutil

    exe = shutil.which("nvidia-smi")
    if not exe:
        return None
    try:
        proc = subprocess.run(
            [exe, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if proc.returncode != 0:
            return None
        name, _, vram = proc.stdout.strip().partition(",")
        return {"name": name.strip(), "vram_gb": int(vram.strip()) if vram.strip().isdigit() else 0}
    except Exception:
        logger.debug("nvidia-smi probe failed", exc_info=True)
        return None


@app.post("/api/llm/chat")
async def llm_chat(body: dict) -> dict:
    import httpx

    model = body.get("model", "gemma3:1b")
    prompt = body.get("prompt", "")
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                "http://localhost:11434/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
            )
            data = r.json()
            return {"response": data.get("response", "")}
    except Exception as e:
        return {"error": str(e)}


async def _bridge_configured() -> dict:
    """Probe whether the primary robot bridge (yahboom-mcp) is reachable.

    Drives the webapp onboarding cue: `configured: true` clears MOCK-until-onboarded
    sample content. Best-effort with a short timeout; never blocks health for long.
    """
    import httpx

    base = settings.yahboom_api_url.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            r = await client.get(f"{base}/api/v1/health")
            ok = r.status_code < 500
    except Exception:
        ok = False
    return {
        "configured": ok,
        "service": "yahboom-mcp",
        "url": base,
    }


@app.get("/api/v1/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "teleoperator-mcp",
        "version": "0.1.0",
        "uptime_s": round(time.time() - start_time, 1),
        "teleop": session_stats(),
        "livekit": get_publisher().status(),
        "onboarding": await _bridge_configured(),
    }


@app.post("/api/shutdown")
async def api_shutdown(confirm: bool = False) -> dict:
    """Gracefully shut down this server. Requires confirm=true."""
    if not confirm:
        return {"success": False, "message": "Pass confirm=true to shut down"}
    await stop_publisher()
    await disconnect_all()
    logger.info("Teleoperator MCP shutting down via REST /api/shutdown")
    import os

    os._exit(0)


@app.get("/api/v1/diagnostics")
async def diagnostics() -> dict:
    """Diagnostics endpoint for CUA-NSIS smoke testing."""
    robots = list_robots()
    tools = [
        {"name": "teleop_status"},
        {"name": "teleop_configure"},
        {"name": "teleop_estop"},
        {"name": "teleop_set_mode"},
        {"name": "teleop_takeover"},
        {"name": "teleop_set_gaze"},
        {"name": "teleop_gaze_center"},
        {"name": "teleop_livekit_status"},
        {"name": "teleop_livekit_publisher_start"},
        {"name": "teleop_livekit_publisher_stop"},
        {"name": "show_teleop_status_card"},
        {"name": "teleop_voice_command"},
        {"name": "teleop_task_dispatch"},
        {"name": "teleop_shutdown"},
    ]
    return {
        "status": "ok",
        "server": "teleoperator-mcp",
        "version": "0.1.0",
        "uptime_seconds": round(time.time() - start_time, 1),
        "tool_count": len(tools),
        "tools": tools,
        "system": {"windows": True},
        "errors": [],
        "teleop": session_stats(),
        "robot_catalog": list(robots.keys()),
    }


@app.get("/api/capabilities")
async def capabilities() -> dict:
    """Fleet webapp introspection — runtime tool surface (no secrets)."""
    tools = [
        "teleop_status",
        "teleop_configure",
        "teleop_estop",
        "teleop_set_mode",
        "teleop_takeover",
        "teleop_set_gaze",
        "teleop_gaze_center",
        "teleop_livekit_status",
        "teleop_livekit_publisher_start",
        "teleop_livekit_publisher_stop",
        "show_teleop_status_card",
        "teleop_voice_command",
        "teleop_task_dispatch",
        "teleop_shutdown",
    ]
    return {
        "status": "ok",
        "server": {"name": "teleoperator-mcp", "version": "0.1.0", "fastmcp": "3.4+"},
        "tool_surface": {
            "total": len(tools),
            "portmanteau_count": 0,
            "atomic_count": len(tools),
            "portmanteau_tools": [],
            "atomic_tools": tools,
        },
        "features": {
            "sampling": False,
            "agentic_workflows": False,
            "prompts": True,
            "resources": True,
            "skills": True,
            "webxr": True,
            "websocket_teleop": True,
            "livekit_video": settings.livekit_enabled,
        },
        "inventory": {
            "workflow_tools": [],
            "prompt_names": ["teleop_help"],
            "resource_uris": ["teleop://status"],
            "skill_uris": ["teleop-supervision", "robot-catalog", "livekit-video-return"],
        },
        "runtime": {
            "transport": "dual",
            "surface_mode": "atomic",
            "web_port": 10900,
            "backend_port": settings.port,
        },
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.websocket("/ws/teleop")
async def ws_teleop(
    websocket: WebSocket,
    robot: str = "boomy",
    token: str = "",
) -> None:
    await teleop_websocket(websocket, robot=robot, token=token)


app.mount("/mcp", _mcp_http)


def main() -> None:
    parser = argparse.ArgumentParser(description="Teleoperator MCP server")
    parser.add_argument("--mode", choices=["stdio", "http", "dual"], default="dual")
    parser.add_argument("--port", type=int, default=settings.port)
    parser.add_argument("--host", default=settings.host)
    args = parser.parse_args()

    if args.mode == "stdio":
        mcp.run(transport="stdio")
        return

    if args.mode == "http":
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")
        return

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
