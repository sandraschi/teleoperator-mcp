"""Mapper and config unit tests."""

from teleoperator_mcp.config import cors_origins_list, settings
from teleoperator_mcp.mappers.boomy import BoomyMapper


def test_boomy_mapper_head_neutral_center() -> None:
    mapper = BoomyMapper()
    ptz = mapper.map_head({"yaw": 0.0, "pitch": 0.0})
    assert ptz.pan == 90.0
    assert ptz.tilt == 90.0


def test_boomy_mapper_head_clamp() -> None:
    mapper = BoomyMapper()
    ptz = mapper.map_head({"yaw": 2.0, "pitch": -1.0})
    assert ptz.pan == 180.0
    assert ptz.tilt == 45.0


def test_boomy_mapper_drive_deadman() -> None:
    mapper = BoomyMapper()
    idle = mapper.map_drive({"axes": [1.0, 1.0], "buttons": {"trigger": 0.0}})
    assert idle.linear == 0.0
    active = mapper.map_drive({"axes": [0.5, -0.5], "buttons": {"trigger": 1.0}})
    assert active.linear > 0
    assert active.angular != 0.0


def test_mapper_reads_live_yahboom_url() -> None:
    original = settings.yahboom_api_url
    try:
        settings.yahboom_api_url = "http://robot-a:10892"
        assert BoomyMapper().api_base == "http://robot-a:10892"
        settings.yahboom_api_url = "http://robot-b:10892/"
        assert BoomyMapper().api_base == "http://robot-b:10892"
    finally:
        settings.yahboom_api_url = original


def test_cors_origins_list_parses() -> None:
    original = settings.cors_origins
    try:
        settings.cors_origins = "https://goliath:10900, http://localhost:10900"
        assert cors_origins_list() == ["https://goliath:10900", "http://localhost:10900"]
    finally:
        settings.cors_origins = original
