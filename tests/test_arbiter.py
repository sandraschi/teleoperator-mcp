"""Authority arbiter tests."""

from teleoperator_mcp.adapters.boomy import BoomyAdapter
from teleoperator_mcp.arbiter.core import AuthorityArbiter, NAV_STUB_ID
from teleoperator_mcp.producers.human_pose import HumanPoseProducer
from teleoperator_mcp.producers.nav_stub import NavStubProducer
from teleoperator_mcp.types import BaseCommand, ProducerCommand


def _arbiter() -> AuthorityArbiter:
    adapter = BoomyAdapter()
    return AuthorityArbiter(adapter, human=HumanPoseProducer(adapter), nav_stub=NavStubProducer(linear=0.1))


def test_default_authority_is_direct_human() -> None:
    arb = _arbiter()
    resolved = arb.resolve()
    assert resolved.sources["base"] == "human_pose"
    assert arb.state.base.mode == "DIRECT"


def test_set_mode_auto_uses_nav_stub_on_base() -> None:
    arb = _arbiter()
    arb.set_mode("base", "AUTO")
    arb.update_human(
        ProducerCommand(
            producer_id="human_pose",
            base=BaseCommand(linear=0.0, angular=0.0),
        )
    )
    resolved = arb.resolve()
    assert resolved.sources["base"] == NAV_STUB_ID
    assert resolved.command.base is not None
    assert resolved.command.base.linear > 0


def test_takeover_seeds_human_from_last_applied() -> None:
    arb = _arbiter()
    arb.set_mode("base", "AUTO")
    resolved = arb.resolve()
    assert resolved.command.base is not None
    auto_linear = resolved.command.base.linear

    arb.takeover()
    assert arb.state.base.mode == "DIRECT"
    assert arb.state.base.owner == "human_pose"
    assert arb._last_human.base is not None
    assert arb._last_human.base.linear == auto_linear


def test_manip_set_mode_rejected_on_boomy() -> None:
    arb = _arbiter()
    try:
        arb.set_mode("manip", "AUTO")
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "not available" in str(exc)


def test_status_includes_authority() -> None:
    arb = _arbiter()
    arb.set_mode("base", "AUTO")
    st = arb.status()
    assert st["authority"]["base"]["mode"] == "AUTO"
    assert st["any_auto"] is True
