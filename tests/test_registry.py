"""Robot adapter registry (M2)."""

import pytest

from teleoperator_mcp.adapters.boomy import BoomyAdapter
from teleoperator_mcp.adapters.registry import create_adapter, list_robots
from teleoperator_mcp.runtime import bind_robot, get_active_robot, get_adapter


def test_list_robots_includes_boomy_and_planned() -> None:
    catalog = list_robots()
    assert "boomy" in catalog
    assert catalog["boomy"]["status"] == "available"
    assert "bumi" in catalog
    assert "vboomy" in catalog
    assert catalog["vboomy"].get("virtual_twin") is True
    assert "r1-a5-d" in catalog


def test_create_adapter_boomy() -> None:
    adapter = create_adapter("boomy")
    assert isinstance(adapter, BoomyAdapter)
    assert adapter.capabilities.robot_id == "boomy"


def test_create_adapter_bumi() -> None:
    from teleoperator_mcp.adapters.bumi import BumiAdapter

    adapter = create_adapter("bumi")
    assert isinstance(adapter, BumiAdapter)
    assert adapter.capabilities.balance_risk is True


def test_create_adapter_vboomy() -> None:
    from teleoperator_mcp.adapters.vboomy import VboomyAdapter

    adapter = create_adapter("vboomy")
    assert isinstance(adapter, VboomyAdapter)
    assert adapter.capabilities.robot_id == "vboomy"
    assert adapter.capabilities.has_arms is False


def test_create_adapter_unknown_raises() -> None:
    with pytest.raises(ValueError, match="Unknown robot"):
        create_adapter("not-a-robot")


def test_create_adapter_planned_raises() -> None:
    with pytest.raises(ValueError, match="planned"):
        create_adapter("r1-a5-d")


def test_bind_robot_switches_runtime() -> None:
    bind_robot("boomy")
    assert get_active_robot() == "boomy"
    assert isinstance(get_adapter(), BoomyAdapter)
