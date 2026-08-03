#!/usr/bin/env python3
"""Teleoperator MCP - Unified Gateway (FastAPI + FastMCP + WebSocket)."""

from __future__ import annotations

import argparse
import logging
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
from .config import cors_origins_list, settings
from .livekit import (
    get_publisher,
    issue_subscriber_token,
    livekit_public_config,
    start_publisher,
    stop_publisher,
)
from .runtime import robots_catalog
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

_READ_ONLY = {"readonly": True}
_MUTATING = {}
_DESTRUCTIVE = {}


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


@mcp.tool(annotations=_READ_ONLY)
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


@app.get("/api/v1/robots")
async def api_robots() -> dict:
    """Available teleop adapters (?robot= route)."""
    return {"robots": robots_catalog()}


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
        pass
    return {"providers": [{"name": "ollama", "models": models}]}


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


@app.get("/api/v1/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "teleoperator-mcp",
        "version": "0.1.0",
        "uptime_s": round(time.time() - start_time, 1),
        "teleop": session_stats(),
        "livekit": get_publisher().status(),
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
        "teleop_export_recording",
        "teleop_shutdown",
    ]
    return {
        "status": "ok",
        "server": {"name": "teleoperator-mcp", "version": "0.1.0", "fastmcp": "3.2+"},
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
            "prompts": False,
            "resources": False,
            "skills": False,
            "webxr": True,
            "websocket_teleop": True,
            "livekit_video": settings.livekit_enabled,
        },
        "inventory": {
            "workflow_tools": [],
            "prompt_names": [],
            "resource_uris": [],
            "skill_uris": [],
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
async def ws_teleop(websocket: WebSocket, robot: str = "boomy") -> None:
    await teleop_websocket(websocket, robot=robot)


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
