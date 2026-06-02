"""AUTO safety and speech tests."""

import asyncio
from unittest.mock import AsyncMock, patch

import httpx

from teleoperator_mcp.config import settings
from teleoperator_mcp.safety import arm_auto_timer, auto_safety_tick, reset_auto_timer
from teleoperator_mcp.ws.handler import session_active, trigger_set_mode


def test_set_mode_auto_rejected_without_webxr() -> None:
    original = settings.auto_require_webxr
    settings.auto_require_webxr = True
    try:
        result = asyncio.run(trigger_set_mode("base", "AUTO", confirm_bench=False))
        assert result["success"] is False
        assert "WebXR" in result["message"]
    finally:
        settings.auto_require_webxr = original
        reset_auto_timer()


def test_set_mode_auto_allowed_with_confirm_bench() -> None:
    original = settings.auto_require_webxr
    settings.auto_require_webxr = True
    try:
        with patch("teleoperator_mcp.ws.handler.speak_auto_start_warning", new_callable=AsyncMock):
            with patch("teleoperator_mcp.ws.handler.ensure_auto_loop", new_callable=AsyncMock):
                result = asyncio.run(trigger_set_mode("base", "AUTO", confirm_bench=True))
        assert result["success"] is True
        assert result["mode"] == "AUTO"
    finally:
        settings.auto_require_webxr = original
        reset_auto_timer()


def test_auto_timeout_stops_drive() -> None:
    original_limit = settings.auto_max_duration_s
    settings.auto_max_duration_s = 0.05
    reset_auto_timer()
    try:
        with patch("teleoperator_mcp.ws.handler.speak_auto_start_warning", new_callable=AsyncMock):
            with patch("teleoperator_mcp.ws.handler.ensure_auto_loop", new_callable=AsyncMock):
                asyncio.run(trigger_set_mode("base", "AUTO", confirm_bench=True))
        arm_auto_timer()

        async def _run() -> bool:
            async with httpx.AsyncClient() as client:
                with patch("teleoperator_mcp.safety.speak_warning", new_callable=AsyncMock):
                    return await auto_safety_tick(client)

        stopped = asyncio.run(_run())
        assert stopped is True
    finally:
        settings.auto_max_duration_s = original_limit
        reset_auto_timer()


def test_session_active_false_by_default() -> None:
    assert session_active() is False
