"""Adapter and producer tests."""

from teleoperator_mcp.adapters.boomy import BoomyAdapter
from teleoperator_mcp.producers.human_pose import HumanPoseProducer


def test_boomy_capabilities() -> None:
    cap = BoomyAdapter().capabilities
    assert cap.robot_id == "boomy"
    assert cap.has_base is True
    assert cap.has_arms is False
    assert cap.hand_type == "none"
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


def test_human_pose_producer_skips_gaze_when_requested() -> None:
    cmd = HumanPoseProducer().from_pose_frame({}, {"buttons": {"trigger": 0}}, include_gaze=False)
    assert cmd.gaze is None
