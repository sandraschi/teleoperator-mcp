"""Tier 1/2 tests — claim/auth, task dispatch, SHARED arbiter, fake-VLA, waypoints."""

import asyncio

from teleoperator_mcp.adapters.boomy import BoomyAdapter
from teleoperator_mcp.arbiter.core import HUMAN_ID, AuthorityArbiter
from teleoperator_mcp.arbiter.state import GroupAuthority
from teleoperator_mcp.auth import claim_robot, list_claims, release_claim, verify_token
from teleoperator_mcp.producers.fake_vla import FakeVlaProducer
from teleoperator_mcp.producers.human_pose import HumanPoseProducer
from teleoperator_mcp.producers.waypoint import Waypoint, WaypointProducer
from teleoperator_mcp.tasks import build_plan, plan_display


def test_claim_robot_and_verify() -> None:
    c = claim_robot("Sandra", "boomy")
    assert c["success"] is True
    assert verify_token(c["token"], "boomy") is True
    assert verify_token("wrong", "boomy") is False
    assert list_claims()["boomy"]["operator_id"] == "Sandra"


def test_release_claim() -> None:
    c = claim_robot("Sandra", "boomy")
    r = release_claim(c["token"])
    assert r["success"] is True
    assert verify_token(c["token"], "boomy") is False


def test_claim_replaces_previous() -> None:
    claim_robot("A", "bumi")
    c2 = claim_robot("B", "bumi")
    assert verify_token(c2["token"], "bumi") is True
    # only the latest token is valid for the robot
    assert len([x for x in list_claims().values() if x["robot_id"] == "bumi"]) == 1


def test_waypoint_producer_sequence() -> None:
    wp = WaypointProducer()
    wp.dispatch([Waypoint(linear=0.3, duration_s=0.01), Waypoint(linear=0.0, duration_s=0.01)])
    cmd = wp.tick()
    assert cmd.base is not None
    assert cmd.base.linear == 0.3
    # after both segments elapse -> hold (zero)
    import time

    time.sleep(0.05)
    cmd2 = wp.tick()
    assert cmd2.base is not None
    assert cmd2.base.linear == 0.0


def test_task_build_plan() -> None:
    assert build_plan("forward") is not None
    assert build_plan("turn left") is not None
    assert build_plan("approach the table") is not None
    assert build_plan("sweep the room") is not None
    assert plan_display("go forward") == "nav_waypoint:forward"
    assert plan_display("open the fridge") == "vla:manipulation (hardware-gated)"
    assert build_plan("dance") is None


def test_fake_vla_producer_emits_commands() -> None:
    vla = FakeVlaProducer(linear=0.2, confidence=0.9)
    cmd = vla.tick()
    assert cmd.producer_id == "vla"
    assert cmd.base is not None
    assert cmd.base.linear == 0.2
    assert cmd.manip is not None
    assert cmd.manip["source"] == "fake_vla"


def test_arbiter_shared_blend() -> None:
    arb = AuthorityArbiter(
        adapter=BoomyAdapter(),
        human=HumanPoseProducer(BoomyAdapter()),
        waypoint=WaypointProducer(),
    )
    arb.human = HumanPoseProducer(BoomyAdapter())
    # nav_stub default 0.15 m/s, human 0.1 m/s, confidence 0.5
    # blend weight (auto) = 1 - conf = 0.5 -> 0.5*0.1 + 0.5*0.15 = 0.125
    from teleoperator_mcp.types import BaseCommand, ProducerCommand

    arb.update_human(
        ProducerCommand(
            producer_id=HUMAN_ID, base=BaseCommand(linear=0.1, angular=0.0), confidence=0.5
        )
    )
    arb.state.set_group("base", GroupAuthority(mode="SHARED", owner="blend"))
    merged = arb.resolve().command
    assert merged.base is not None
    assert abs(merged.base.linear - 0.125) < 0.01


def test_arbiter_auto_uses_waypoint() -> None:
    arb = AuthorityArbiter(
        adapter=BoomyAdapter(),
        human=HumanPoseProducer(BoomyAdapter()),
        waypoint=WaypointProducer(),
    )
    arb.waypoint.dispatch([Waypoint(linear=0.5, duration_s=1.0)])
    arb.state.set_group("base", GroupAuthority(mode="AUTO", owner="nav_waypoint"))
    merged = arb.resolve().command
    assert merged.base is not None
    assert merged.base.linear == 0.5


def test_supervision_endpoint() -> None:
    from teleoperator_mcp.server import app

    paths = {r.path for r in app.routes}
    for expected in (
        "/api/v1/session/claim",
        "/api/v1/session/claims",
        "/api/v1/session/release",
        "/api/v1/teleop/task",
        "/api/v1/supervision",
        "/api/v1/episodes",
    ):
        assert expected in paths, f"missing route {expected}"


def test_task_dispatch_hardware_gate() -> None:
    from teleoperator_mcp.server import dispatch_task

    result = asyncio.run(dispatch_task("open the fridge"))
    assert result["success"] is False
    assert "hardware-gated" in result["message"]
