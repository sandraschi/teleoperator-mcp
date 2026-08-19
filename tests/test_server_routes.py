"""Server-level REST smoke tests (skills, capabilities, LLM probe shape)."""

import asyncio

from teleoperator_mcp.server import SKILLS, app


def test_skills_payload() -> None:
    assert isinstance(SKILLS, list)
    assert len(SKILLS) >= 1
    names = {s["name"] for s in SKILLS}
    assert "teleop-supervision" in names


def test_capabilities_features() -> None:
    from teleoperator_mcp.server import capabilities

    caps = asyncio.run(capabilities())
    assert caps["status"] == "ok"
    assert caps["features"]["skills"] is True
    assert caps["features"]["prompts"] is True
    assert caps["features"]["resources"] is True
    assert "teleop-supervision" in caps["inventory"]["skill_uris"]


def test_health_payload() -> None:
    from teleoperator_mcp.server import health

    h = asyncio.run(health())
    assert h["status"] == "ok"
    assert h["service"] == "teleoperator-mcp"
    assert "teleop" in h
    assert "livekit" in h


def test_app_routes_present() -> None:
    paths = {r.path for r in app.routes}
    for expected in ("/api/v1/health", "/api/skills", "/api/v1/diagnostics", "/api/capabilities"):
        assert expected in paths, f"missing route {expected}"
