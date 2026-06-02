"""AUTO safety: duration limit, WebXR gate, spoken warnings."""

from __future__ import annotations

import asyncio
import logging
import time

import httpx

from .config import settings
from .runtime import get_arbiter
from .speech import speak_warning

logger = logging.getLogger("teleoperator_mcp.safety")

_auto_started_at: float | None = None
_auto_warned: bool = False


def reset_auto_timer() -> None:
    global _auto_started_at, _auto_warned
    _auto_started_at = None
    _auto_warned = False


def auto_elapsed_s() -> float | None:
    if _auto_started_at is None:
        return None
    return time.monotonic() - _auto_started_at


def arm_auto_timer() -> None:
    global _auto_started_at, _auto_warned
    _auto_started_at = time.monotonic()
    _auto_warned = False


async def speak_auto_start_warning(*, bench: bool = False) -> None:
    limit = int(settings.auto_max_duration_s)
    if bench:
        text = (
            f"Warning. Bench auto drive active. {limit} second limit. "
            "Robot on blocks only. Squeeze or estop to stop."
        )
    else:
        text = f"Warning. Autonomous drive active. {limit} second limit. Squeeze to take over."
    await speak_warning(text)


async def force_auto_stop(http_client: httpx.AsyncClient, *, reason: str) -> dict:
    """End AUTO: human takeover + zero drive (no estop latch — timed stop is not a fault)."""
    reset_auto_timer()
    arbiter = get_arbiter()
    arbiter.takeover()
    await arbiter.adapter.e_stop(http_client)
    logger.warning("AUTO force-stopped (%s)", reason)
    asyncio.create_task(speak_warning("Autonomous drive stopped. Robot halted."))
    return {"stopped": True, "reason": reason}


async def auto_safety_tick(http_client: httpx.AsyncClient) -> bool:
    """Enforce AUTO duration limit. Returns True if AUTO was force-stopped."""
    arbiter = get_arbiter()
    if arbiter.state.base.mode != "AUTO":
        reset_auto_timer()
        return False

    if _auto_started_at is None:
        return False

    elapsed = time.monotonic() - _auto_started_at
    limit = settings.auto_max_duration_s
    warn_at = max(0.0, limit - settings.auto_warn_before_s)

    global _auto_warned
    if not _auto_warned and elapsed >= warn_at:
        _auto_warned = True
        secs = int(settings.auto_warn_before_s)
        await speak_warning(f"Autonomous drive stopping in {secs} seconds.")

    if elapsed >= limit:
        await force_auto_stop(http_client, reason="max_duration")
        return True
    return False
