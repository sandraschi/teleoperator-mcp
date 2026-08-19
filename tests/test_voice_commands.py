"""Voice command parsing + REST mirror tests."""

import asyncio

from teleoperator_mcp.voice_commands import parse_voice_command


def test_estop_priority() -> None:
    c = parse_voice_command("emergency stop now")
    assert c.action == "estop"
    assert c.args == {}


def test_takeover() -> None:
    c = parse_voice_command("teleop take over")
    assert c.action == "takeover"


def test_gaze_center() -> None:
    c = parse_voice_command("center camera")
    assert c.action == "gaze_center"


def test_gaze_direction() -> None:
    c = parse_voice_command("look left")
    assert c.action == "set_gaze"
    assert c.args["pan"] < 90


def test_livekit_start_stop() -> None:
    assert parse_voice_command("start video").action == "livekit_start"
    assert parse_voice_command("camera off").action == "livekit_stop"


def test_set_mode_auto() -> None:
    c = parse_voice_command("set base to auto")
    assert c.action == "set_mode"
    assert c.args == {"group": "base", "mode": "AUTO"}


def test_set_mode_direct() -> None:
    c = parse_voice_command("switch gaze to manual")
    assert c.action == "set_mode"
    assert c.args["group"] == "gaze"
    assert c.args["mode"] == "DIRECT"


def test_status() -> None:
    assert parse_voice_command("status").action == "status"


def test_unknown() -> None:
    c = parse_voice_command("sing me a song")
    assert c.action == "unknown"
    assert c.confidence == 0.0


def test_voice_rest_mirror_routes() -> None:
    from teleoperator_mcp.server import app

    paths = {r.path for r in app.routes}
    assert "/api/v1/teleop/voice" in paths


def test_execute_voice_unknown() -> None:
    from teleoperator_mcp.server import _execute_voice_command

    result = asyncio.run(_execute_voice_command("sing me a song"))
    assert result["success"] is False
    assert result["action"] == "unknown"


def test_execute_voice_status() -> None:
    from teleoperator_mcp.server import _execute_voice_command

    result = asyncio.run(_execute_voice_command("status"))
    assert result["success"] is True
    assert result["action"] == "status"
    assert "result" in result
