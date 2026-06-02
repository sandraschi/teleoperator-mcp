"""WebSocket teleop session handler."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field

import httpx
from fastapi import WebSocket, WebSocketDisconnect

from ..config import settings
from ..mappers.boomy import BoomyMapper

logger = logging.getLogger("teleoperator_mcp.ws")


@dataclass
class SessionStats:
    connected_at: float = field(default_factory=time.time)
    frames_in: int = 0
    last_frame_at: float | None = None
    robot: str = "boomy"
    client: str | None = None
    watchdog_latched: bool = False
    estop_count: int = 0


_active_session: WebSocket | None = None
_stats = SessionStats()
_mapper = BoomyMapper()
_watchdog_latched = False


def session_stats() -> dict:
    return {
        "active": _active_session is not None,
        "robot": _stats.robot,
        "frames_in": _stats.frames_in,
        "last_frame_at": _stats.last_frame_at,
        "uptime_s": round(time.time() - _stats.connected_at, 1),
        "client": _stats.client,
        "watchdog_latched": _watchdog_latched,
        "estop_count": _stats.estop_count,
    }


async def trigger_estop(reason: str = "mcp") -> dict:
    """Hard stop via yahboom REST. Callable from MCP tools and WS handler."""
    global _stats
    async with httpx.AsyncClient() as client:
        await _mapper.e_stop(client)
    _stats.estop_count += 1
    logger.warning("e-stop triggered (%s)", reason)
    return {
        "success": True,
        "message": f"E-stop sent ({reason})",
        "estop_count": _stats.estop_count,
    }


async def _notify_client(payload: dict) -> None:
    if _active_session is None:
        return
    try:
        await _active_session.send_json(payload)
    except Exception:
        pass


async def _handle_pose_frame(payload: dict, http_client: httpx.AsyncClient) -> None:
    global _stats, _watchdog_latched

    _stats.frames_in += 1
    _stats.last_frame_at = time.time()
    _watchdog_latched = False
    _stats.watchdog_latched = False

    msg_type = payload.get("type")
    if msg_type == "heartbeat":
        return
    if msg_type == "estop":
        await _mapper.e_stop(http_client)
        _stats.estop_count += 1
        return

    head = payload.get("head") or {}
    right = payload.get("right") or {}

    drive = _mapper.map_drive(right)
    await _mapper.apply_drive(drive, http_client)

    if _stats.frames_in % 3 == 0:
        ptz = _mapper.map_head(head)
        await _mapper.apply_ptz(ptz, http_client)


async def teleop_websocket(websocket: WebSocket, robot: str = "boomy") -> None:
    global _active_session, _stats, _watchdog_latched

    if _active_session is not None:
        await websocket.close(code=4003, reason="Another teleop session is active")
        return

    await websocket.accept()
    _active_session = websocket
    _watchdog_latched = False
    _stats = SessionStats(robot=robot, client=websocket.client.host if websocket.client else None)
    logger.info("teleop session started robot=%s client=%s", robot, _stats.client)

    watchdog_task: asyncio.Task | None = None

    async def watchdog(http_client: httpx.AsyncClient) -> None:
        global _watchdog_latched
        while _active_session is websocket:
            await asyncio.sleep(settings.watchdog_ms / 1000.0)
            last = _stats.last_frame_at
            if last is None:
                continue
            if (time.time() - last) * 1000.0 <= settings.watchdog_ms:
                continue
            if _watchdog_latched:
                continue
            _watchdog_latched = True
            _stats.watchdog_latched = True
            logger.warning("watchdog: no frames - e-stop (latched)")
            await _mapper.e_stop(http_client)
            await _notify_client({"ok": False, "watchdog": True})

    try:
        async with httpx.AsyncClient() as http_client:
            watchdog_task = asyncio.create_task(watchdog(http_client))
            while True:
                raw = await websocket.receive_text()
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    await websocket.send_json({"ok": False, "error": "invalid_json"})
                    continue
                await _handle_pose_frame(payload, http_client)
                await websocket.send_json({"ok": True, "seq": payload.get("seq")})
    except WebSocketDisconnect:
        logger.info("teleop session disconnected")
    finally:
        if watchdog_task:
            watchdog_task.cancel()
        async with httpx.AsyncClient() as http_client:
            await _mapper.e_stop(http_client)
        _active_session = None
        _watchdog_latched = False


async def disconnect_all() -> None:
    global _active_session
    if _active_session is not None:
        await _active_session.close(code=1001, reason="server shutdown")
        _active_session = None
