"""Gaze / PTZ head-follow prep tests."""

from teleoperator_mcp.gaze import GazeFollower


def test_gaze_follower_deadband() -> None:
    gf = GazeFollower()
    first = gf.from_head({"yaw": 0.05, "pitch": 0.0})
    assert first is not None
    assert first.pan == 93.0
    second = gf.from_head({"yaw": 0.051, "pitch": 0.0})
    assert second is None


def test_gaze_absolute() -> None:
    cmd = GazeFollower.absolute(120, 60)
    assert cmd.pan == 120.0
    assert cmd.tilt == 60.0
