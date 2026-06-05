"""Adapter and producer tests."""

from teleoperator_mcp.adapters.boomy import BoomyAdapter
from teleoperator_mcp.adapters.bumi import BumiAdapter
from teleoperator_mcp.adapters.vboomy import VboomyAdapter
from teleoperator_mcp.producers.human_pose import HumanPoseProducer


def test_boomy_capabilities() -> None:
    cap = BoomyAdapter().capabilities
    assert cap.robot_id == "boomy"
    assert cap.has_base is True
    assert cap.has_arms is False
    assert cap.hand_type == "none"
    assert cap.balance_risk is False


def test_bumi_capabilities() -> None:
    cap = BumiAdapter().capabilities
    assert cap.robot_id == "bumi"
    assert cap.has_legs is True
    assert cap.balance_risk is True
    assert cap.has_arms is True


def test_vboomy_capabilities() -> None:
    cap = VboomyAdapter().capabilities
    assert cap.robot_id == "vboomy"
    assert cap.has_base is True
    assert cap.balance_risk is False


def test_human_pose_producer_emits_groups() -> None:
    producer = HumanPoseProducer()
    cmd = producer.from_pose_frame(
        {"yaw": 0.1, "pitch": 0.0},
        {"axes": [0.0, -0.5], "buttons": {"trigger": 1.0}},
        include_gaze=True,
    )
    assert cmd.producer_id == "human_pose"
    assert cmd.base is not None
    assert cmd.base.linear > 0
    assert cmd.gaze is not None
    assert cmd.manip is None


def test_human_pose_bumi_walk_slower_cap() -> None:
    producer = HumanPoseProducer(BumiAdapter())
    cmd = producer.from_pose_frame(
        {"yaw": 0.0, "pitch": 0.0},
        {"axes": [0.0, -1.0], "buttons": {"trigger": 1.0}},
    )
    assert cmd.base is not None
    assert cmd.base.linear <= 0.15


def test_human_pose_producer_skips_gaze_when_requested() -> None:
    cmd = HumanPoseProducer().from_pose_frame({}, {"buttons": {"trigger": 0}}, include_gaze=False)
    assert cmd.gaze is None
