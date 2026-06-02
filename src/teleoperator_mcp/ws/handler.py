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
from ..runtime import get_adapter, get_arbiter

logger = logging.getLogger("teleoperator_mcp.ws")

_auto_task: asyncio.Task | None = None


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
_watchdog_latched = False


def session_stats() -> dict:
    arbiter = get_arbiter()
    cap = get_adapter().capabilities
    return {
        "active": _active_session is not None,
        "robot": _stats.robot,
        "robot_id": cap.robot_id,
        "display_name": cap.display_name,
        "frames_in": _stats.frames_in,
        "last_frame_at": _stats.last_frame_at,
        "uptime_s": round(time.time() - _stats.connected_at, 1),
        "client": _stats.client,
        "watchdog_latched": _watchdog_latched,
        "estop_count": _stats.estop_count,
        **arbiter.status(),
    }


async def ensure_auto_loop() -> None:
    """Background tick when any group is AUTO (MCP-only tests without WebXR frames)."""
    global _auto_task
    arbiter = get_arbiter()
    if not arbiter.any_auto():
        return
    if _auto_task is not None and not _auto_task.done():
        return

    async def _loop() -> None:
        arbiter = get_arbiter()
        adapter = get_adapter()
        while arbiter.any_auto():
            if not arbiter.state.estop_latched:
                async with httpx.AsyncClient() as client:
                    await arbiter.apply_resolved(client)
            await asyncio.sleep(0.1)
        logger.info("auto loop stopped (no AUTO groups)")

    _auto_task = asyncio.create_task(_loop())
    logger.info("auto loop started")


async def trigger_estop(reason: str = "mcp") -> dict:
    """Hard stop via arbiter. Callable from MCP tools and WS handler."""
    global _stats
    arbiter = get_arbiter()
    async with httpx.AsyncClient() as client:
        await arbiter.estop(client)
    _stats.estop_count += 1
    logger.warning("e-stop triggered (%s)", reason)
    return {
        "success": True,
        "message": f"E-stop sent ({reason})",
        "estop_count": _stats.estop_count,
        "estop_latched": arbiter.state.estop_latched,
    }


async def trigger_set_mode(group: str, mode: str) -> dict:
    if mode not in ("DIRECT", "AUTO"):
        return {"success": False, "message": f"Invalid mode '{mode}' — use DIRECT or AUTO"}
    if group not in ("base", "gaze", "manip"):
        return {"success": False, "message": f"Invalid group '{group}'"}
    arbiter = get_arbiter()
    try:
        result = arbiter.set_mode(group, mode)  # type: ignore[arg-type]
    except ValueError as exc:
        return {"success": False, "message": str(exc)}
    await ensure_auto_loop()
    return {"success": True, "message": f"{group} -> {mode}", **result}


async def trigger_takeover(group: str | None = None) -> dict:
    arbiter = get_arbiter()
    try:
        result = arbiter.takeover(group)  # type: ignore[arg-type]
    except ValueError as exc:
        return {"success": False, "message": str(exc)}
    return {"success": True, "message": "Human takeover", **result}


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
        await get_arbiter().estop(http_client)
        _stats.estop_count += 1
        return
    if msg_type == "takeover":
        get_arbiter().takeover()
        return

    head = payload.get("head") or {}
    right = payload.get("right") or {}

    include_gaze = _stats.frames_in % 3 == 0
    human = get_arbiter().human
    command = human.from_pose_frame(head, right, include_gaze=include_gaze)
    arbiter = get_arbiter()
    arbiter.update_human(command)
    await arbiter.apply_resolved(http_client)


async def teleop_websocket(websocket: WebSocket, robot: str = "boomy") -> None:
    global _active_session, _stats, _watchdog_latched

    if robot != "boomy":
        await websocket.close(code=4004, reason=f"Robot '{robot}' not supported yet")
        return

    if _active_session is not None:
        await websocket.close(code=4003, reason="Another teleop session is active")
        return

    await websocket.accept()
    _active_session = websocket
    _watchdog_latched = False
    get_arbiter().takeover()
    _stats = SessionStats(robot=robot, client=websocket.client.host if websocket.client else None)
    logger.info("teleop session started robot=%s client=%s", robot, _stats.client)

    watchdog_task: asyncio.Task | None = None

    async def watchdog(http_client: httpx.AsyncClient) -> None:
        global _watchdog_latched
        arbiter = get_arbiter()
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
            await arbiter.estop(http_client)
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
                arbiter = get_arbiter()
                await websocket.send_json(
                    {
                        "ok": True,
                        "seq": payload.get("seq"),
                        "authority": arbiter.state.to_dict(),
                    }
                )
    except WebSocketDisconnect:
        logger.info("teleop session disconnected")
    finally:
        if watchdog_task:
            watchdog_task.cancel()
        get_arbiter().takeover()
        async with httpx.AsyncClient() as http_client:
            await get_adapter().e_stop(http_client)
        _active_session = None
        _watchdog_latched = False


async def disconnect_all() -> None:
    global _active_session
    if _active_session is not None:
        await _active_session.close(code=1001, reason="server shutdown")
        _active_session = None
