#!/usr/bin/env python3
"""Teleoperator MCP - Unified Gateway (FastAPI + FastMCP + WebSocket)."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime

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
from .config import cors_origins_list, settings
from .livekit import (
    get_publisher,
    issue_subscriber_token,
    livekit_public_config,
    start_publisher,
    stop_publisher,
)
from .ws.handler import (
    disconnect_all,
    session_stats,
    teleop_websocket,
    trigger_estop,
    trigger_set_mode,
    trigger_set_gaze,
    trigger_gaze_center,
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


@mcp.tool()
async def teleop_status() -> dict:
    """Active WebXR teleop session status (connection, frame count, robot target)."""
    stats = session_stats()
    return {
        "success": True,
        "message": "Teleop session active" if stats["active"] else "No active teleop session",
        **stats,
        "yahboom_api": settings.yahboom_api_url,
        "watchdog_ms": settings.watchdog_ms,
    }


@mcp.tool()
async def teleop_configure(
    max_linear: float | None = None,
    max_angular: float | None = None,
    pan_gain: float | None = None,
    tilt_gain: float | None = None,
    yahboom_api_url: str | None = None,
) -> dict:
    """Adjust teleop mapping gains and downstream robot API URL (runtime)."""
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


@mcp.tool()
async def teleop_estop() -> dict:
    """Hard stop: zero drive on all actuator groups. Operator/agent veto."""
    return await trigger_estop(reason="mcp")


@mcp.tool()
async def teleop_set_mode(group: str, mode: str, confirm_bench: bool = False) -> dict:
    """Set actuator group authority: DIRECT (human) or AUTO (nav stub). Groups: base, gaze, manip.

    AUTO on base requires an active WebXR session unless confirm_bench=true (blocks only, timed stop).
    """
    return await trigger_set_mode(group=group.lower(), mode=mode.upper(), confirm_bench=confirm_bench)


@mcp.tool()
async def teleop_takeover(group: str | None = None) -> dict:
    """Human reclaims authority on one group or all available groups. Clears estop latch."""
    g = group.lower() if group else None
    return await trigger_takeover(group=g)


@mcp.tool()
async def teleop_set_gaze(pan: float, tilt: float) -> dict:
    """Move Boomy camera to absolute pan/tilt (0-180°, center ~90). Bench + head-follow prep."""
    return await trigger_set_gaze(pan=pan, tilt=tilt)


@mcp.tool()
async def teleop_gaze_center() -> dict:
    """Center camera servos (neutral head-follow reference)."""
    return await trigger_gaze_center()


@mcp.tool()
async def teleop_livekit_status() -> dict:
    """LiveKit video return status (publisher + room config)."""
    return {
        "success": True,
        "message": "LiveKit status",
        "config": livekit_public_config(),
        **get_publisher().status(),
    }


@mcp.tool()
async def teleop_livekit_publisher_start() -> dict:
    """Start Goliath-side MJPEG → LiveKit publisher for Boomy camera."""
    result = await start_publisher()
    return result


@mcp.tool()
async def teleop_livekit_publisher_stop() -> dict:
    """Stop LiveKit camera publisher."""
    result = await stop_publisher()
    return result


class LiveKitTokenBody(BaseModel):
    identity: str = Field(min_length=1, max_length=128)
    room: str | None = None
    name: str | None = None


_mcp_http = mcp.http_app()


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
    return await trigger_set_mode(group=group.lower(), mode=mode.upper(), confirm_bench=confirm_bench)


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


@app.get("/api/v1/livekit/config")
async def api_livekit_config() -> dict:
    """Public LiveKit connection info for WebXR client (no secrets)."""
    return livekit_public_config()


@app.post("/api/v1/livekit/token")
async def api_livekit_token(body: LiveKitTokenBody) -> dict:
    """Subscribe-only JWT for headset browser (myconf-compatible keys)."""
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


@app.get("/api/v1/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "teleoperator-mcp",
        "uptime_s": round(time.time() - start_time, 1),
        "teleop": session_stats(),
        "livekit": get_publisher().status(),
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
