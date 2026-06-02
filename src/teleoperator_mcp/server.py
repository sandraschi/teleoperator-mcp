#!/usr/bin/env python3
"""Teleoperator MCP - Unified Gateway (FastAPI + FastMCP + WebSocket)."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import FastMCP

from .config import cors_origins_list, settings
from .ws.handler import (
    disconnect_all,
    session_stats,
    teleop_websocket,
    trigger_estop,
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
async def teleop_set_mode(group: str, mode: str) -> dict:
    """Set actuator group authority: DIRECT (human) or AUTO (nav stub). Groups: base, gaze, manip."""
    return await trigger_set_mode(group=group.lower(), mode=mode.upper())


@mcp.tool()
async def teleop_takeover(group: str | None = None) -> dict:
    """Human reclaims authority on one group or all available groups. Clears estop latch."""
    g = group.lower() if group else None
    return await trigger_takeover(group=g)


_mcp_http = mcp.http_app()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Teleoperator MCP starting (port %s)", settings.port)
    async with _mcp_http.router.lifespan_context(_mcp_http):
        yield
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


@app.get("/api/v1/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "teleoperator-mcp",
        "uptime_s": round(time.time() - start_time, 1),
        "teleop": session_stats(),
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
