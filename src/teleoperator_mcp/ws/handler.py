"""WebSocket teleop session handler."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field

import httpx
from fastapi import WebSocket, WebSocketDisconnect

from ..activity_log import log_activity
from ..adapters.boomy import BoomyAdapter
from ..auth import verify_token
from ..config import settings
from ..gaze import GazeFollower
from ..recording import get_recorder
from ..runtime import bind_robot, get_active_robot, get_adapter, get_arbiter, robots_catalog
from ..safety import (
    arm_auto_timer,
    auto_safety_tick,
    force_auto_stop,
    reset_auto_timer,
    speak_auto_start_warning,
)
from ..speech import speak_warning

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
_presence_at: float = 0.0


def session_active() -> bool:
    return _active_session is not None


def _presence_missed() -> bool:
    """True when the operator presence pulse has expired (headset-removed / suspend)."""
    if _presence_at == 0.0:
        return False
    return (time.time() - _presence_at) > settings.presence_timeout_s


def session_stats() -> dict:
    arbiter = get_arbiter()
    cap = get_adapter().capabilities
    from ..safety import auto_elapsed_s

    elapsed = auto_elapsed_s()
    return {
        "active": _active_session is not None,
        "robot": _stats.robot,
        "active_robot": get_active_robot(),
        "robots": robots_catalog(),
        "recording": get_recorder().status(),
        "robot_id": cap.robot_id,
        "display_name": cap.display_name,
        "frames_in": _stats.frames_in,
        "last_frame_at": _stats.last_frame_at,
        "uptime_s": round(time.time() - _stats.connected_at, 1),
        "client": _stats.client,
        "watchdog_latched": _watchdog_latched,
        "estop_count": _stats.estop_count,
        "auto_elapsed_s": round(elapsed, 1) if elapsed is not None else None,
        "auto_max_duration_s": settings.auto_max_duration_s,
        "auto_require_webxr": settings.auto_require_webxr,
        **arbiter.status(),
    }


async def ensure_auto_loop() -> None:
    """Background tick when any group is AUTO."""
    global _auto_task
    arbiter = get_arbiter()
    if not arbiter.any_auto():
        if _auto_task is not None and not _auto_task.done():
            _auto_task.cancel()
        return
    if _auto_task is not None and not _auto_task.done():
        return

    async def _loop() -> None:
        try:
            while get_arbiter().any_auto():
                async with httpx.AsyncClient() as client:
                    if await auto_safety_tick(client):
                        break
                    if not get_arbiter().state.estop_latched:
                        await get_arbiter().apply_resolved(client)
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            raise
        finally:
            logger.info("auto loop stopped (no AUTO groups)")

    _auto_task = asyncio.create_task(_loop())
    logger.info("auto loop started")


async def trigger_estop(reason: str = "mcp") -> dict:
    """Hard stop via arbiter. Callable from MCP tools and WS handler."""
    global _stats
    reset_auto_timer()
    arbiter = get_arbiter()
    async with httpx.AsyncClient() as client:
        await arbiter.estop(client)
    _stats.estop_count += 1
    logger.warning("e-stop triggered (%s)", reason)
    if reason in ("mcp", "user_estop"):
        await speak_warning("Emergency stop. Robot halted.")
    return {
        "success": True,
        "message": f"E-stop sent ({reason})",
        "estop_count": _stats.estop_count,
        "estop_latched": arbiter.state.estop_latched,
    }


async def trigger_set_mode(
    group: str,
    mode: str,
    *,
    confirm_bench: bool = False,
) -> dict:
    if mode not in ("DIRECT", "AUTO"):
        return {"success": False, "message": f"Invalid mode '{mode}' — use DIRECT or AUTO"}
    if group not in ("base", "gaze", "manip"):
        return {"success": False, "message": f"Invalid group '{group}'"}

    if mode == "AUTO" and settings.auto_require_webxr and not session_active():
        if not confirm_bench:
            return {
                "success": False,
                "message": (
                    "AUTO requires an active WebXR session, or confirm_bench=true "
                    "(robot on blocks only, timed auto-stop)."
                ),
            }

    arbiter = get_arbiter()
    try:
        result = arbiter.set_mode(group, mode)  # type: ignore[arg-type]
    except ValueError as exc:
        return {"success": False, "message": str(exc)}

    if mode == "AUTO" and group == "base":
        reset_auto_timer()
    elif mode == "DIRECT":
        reset_auto_timer()

    await ensure_auto_loop()

    if mode == "AUTO" and group == "base":
        arm_auto_timer()
        asyncio.create_task(speak_auto_start_warning(bench=confirm_bench and not session_active()))

    return {
        "success": True,
        "message": f"{group} -> {mode}",
        "confirm_bench": confirm_bench,
        **result,
    }


async def trigger_takeover(group: str | None = None) -> dict:
    reset_auto_timer()
    arbiter = get_arbiter()
    try:
        result = arbiter.takeover(group)  # type: ignore[arg-type]
    except ValueError as exc:
        return {"success": False, "message": str(exc)}
    return {"success": True, "message": "Human takeover", **result}


async def trigger_set_gaze(pan: float, tilt: float) -> dict:
    """Absolute PTZ (0-180°) for bench tests and head-follow prep."""
    adapter = get_adapter()
    if not isinstance(adapter, BoomyAdapter):
        return {"success": False, "message": "PTZ not supported on this robot"}
    gaze = GazeFollower.absolute(pan, tilt)
    async with httpx.AsyncClient() as client:
        ok = await adapter.apply_gaze(gaze, client)
    return {
        "success": ok,
        "message": f"PTZ pan={int(gaze.pan)} tilt={int(gaze.tilt)}",
        "pan": gaze.pan,
        "tilt": gaze.tilt,
    }


async def trigger_gaze_center() -> dict:
    return await trigger_set_gaze(settings.ptz_pan_center, settings.ptz_tilt_center)


async def _notify_client(payload: dict) -> None:
    if _active_session is None:
        return
    try:
        await _active_session.send_json(payload)
    except Exception:
        pass


async def _handle_pose_frame(payload: dict, http_client: httpx.AsyncClient) -> None:
    global _stats, _watchdog_latched, _presence_at

    msg_type = payload.get("type")
    if msg_type in ("heartbeat", "presence"):
        # Heartbeats keep the socket alive but must not reset pose watchdog or speech latch.
        # A presence pulse extends the operator-presence deadman (headset-removed gate).
        if msg_type == "presence":
            _presence_at = time.time()
        return

    _stats.frames_in += 1
    _stats.last_frame_at = time.time()
    _watchdog_latched = False
    _stats.watchdog_latched = False

    if msg_type == "estop":
        reset_auto_timer()
        await get_arbiter().estop(http_client)
        _stats.estop_count += 1
        return
    if msg_type == "takeover":
        reset_auto_timer()
        get_arbiter().takeover()
        return

    if await auto_safety_tick(http_client):
        return

    head = payload.get("head") or {}
    right = payload.get("right") or {}
    left = payload.get("left") or {}
    hands = payload.get("hands")

    include_gaze = (
        settings.gaze_every_n_frames <= 1 or _stats.frames_in % settings.gaze_every_n_frames == 0
    )
    human = get_arbiter().human
    command = human.from_pose_frame(
        head,
        right,
        left,
        include_gaze=include_gaze,
        hands=hands if isinstance(hands, dict) else None,
    )
    arbiter = get_arbiter()
    arbiter.update_human(command)
    resolved = await arbiter.apply_resolved(http_client)
    get_recorder().log_frame(
        payload,
        resolved.command,
        sources=resolved.sources,
        authority=arbiter.state.to_dict(),
    )


async def teleop_websocket(websocket: WebSocket, robot: str = "boomy", token: str = "") -> None:
    global _active_session, _stats, _watchdog_latched, _presence_at

    if not verify_token(token, robot):
        await websocket.close(code=4001, reason="Operator claim token required (estop stays open)")
        return

    if _active_session is not None:
        await websocket.close(code=4003, reason="Another teleop session is active")
        return

    await websocket.accept()

    try:
        bind_robot(robot)
    except ValueError as exc:
        await websocket.close(code=4004, reason=str(exc))
        return

    _active_session = websocket
    _watchdog_latched = False
    _presence_at = time.time()
    reset_auto_timer()
    get_arbiter().takeover()
    _stats = SessionStats(robot=robot, client=websocket.client.host if websocket.client else None)
    get_recorder().start_session(robot, client=_stats.client)
    logger.info("teleop session started robot=%s client=%s", robot, _stats.client)
    log_activity(
        "teleop",
        f"WebXR session started robot={robot}",
        level="INFO",
        meta={"robot": robot, "client": _stats.client},
    )

    watchdog_task: asyncio.Task | None = None

    async def watchdog(http_client: httpx.AsyncClient) -> None:
        global _watchdog_latched
        arbiter = get_arbiter()
        while _active_session is websocket:
            await asyncio.sleep(min(settings.watchdog_ms, 500) / 1000.0)
            last = _stats.last_frame_at
            if last is not None and (time.time() - last) * 1000.0 > settings.watchdog_ms:
                if not _watchdog_latched:
                    _watchdog_latched = True
                    _stats.watchdog_latched = True
                    logger.warning("watchdog: no frames - e-stop (latched)")
                    reset_auto_timer()
                    await arbiter.estop(http_client)
                    await speak_warning("Watchdog stop. No headset frames. Robot halted.")
                    await _notify_client({"ok": False, "watchdog": True})
            if _presence_missed() and not _watchdog_latched:
                _watchdog_latched = True
                _stats.watchdog_latched = True
                logger.warning("presence deadman: headset presence expired - e-stop")
                reset_auto_timer()
                await arbiter.estop(http_client)
                await speak_warning("Operator presence lost. Robot halted.")
                await _notify_client({"ok": False, "presence": True})

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
        log_activity(
            "teleop", "WebXR session disconnected", level="INFO", meta={"robot": _stats.robot}
        )
    finally:
        if watchdog_task:
            watchdog_task.cancel()
        reset_auto_timer()
        get_arbiter().takeover()
        async with httpx.AsyncClient() as client:
            if get_arbiter().any_auto():
                await force_auto_stop(client, reason="session_ended")
            else:
                await get_adapter().e_stop(client)
        get_recorder().end_session()
        _active_session = None
        _watchdog_latched = False


async def disconnect_all() -> None:
    global _active_session
    if _active_session is not None:
        await _active_session.close(code=1001, reason="server shutdown")
        _active_session = None
