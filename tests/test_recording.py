"""Session recording (M4)."""

from pathlib import Path

import pytest

from teleoperator_mcp.config import settings
from teleoperator_mcp.recording.recorder import SessionRecorder
from teleoperator_mcp.types import BaseCommand, GazeCommand, ProducerCommand


@pytest.fixture
def recorder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SessionRecorder:
    monkeypatch.setattr(settings, "recording_enabled", True)
    monkeypatch.setattr(settings, "recording_dir", str(tmp_path))
    monkeypatch.setattr(settings, "recording_fps", 30)
    return SessionRecorder(tmp_path)


def test_start_log_end_writes_jsonl(recorder: SessionRecorder) -> None:
    session_id = recorder.start_session("boomy", client="127.0.0.1")
    assert session_id is not None
    assert recorder.state.active is True

    cmd = ProducerCommand(
        producer_id="human_pose",
        base=BaseCommand(linear=0.1, angular=0.0),
        gaze=GazeCommand(pan=95.0, tilt=88.0),
    )
    recorder.log_frame(
        {"seq": 1, "head": {"yaw": 0.1}, "right": {"buttons": {"trigger": 1.0}}},
        cmd,
        sources={"base": "human_pose"},
        authority={"base": {"mode": "DIRECT"}},
    )
    summary = recorder.end_session()
    assert summary is not None
    assert summary["frame_count"] == 1
    assert summary["robot_id"] == "boomy"

    episode_dir = Path(recorder.base_dir) / "data" / "episode_000000"
    frames_path = episode_dir / "frames.jsonl"
    assert frames_path.exists()
    lines = frames_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert '"action"' in lines[0]

    meta = recorder.base_dir / "meta" / "episodes.jsonl"
    assert meta.exists()
    info = recorder.base_dir / "meta" / "info.json"
    assert info.exists()


def test_recording_disabled_skips_start(recorder: SessionRecorder, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "recording_enabled", False)
    assert recorder.start_session("boomy") is None
    assert recorder.state.active is False


def test_heartbeat_not_logged(recorder: SessionRecorder) -> None:
    recorder.start_session("boomy")
    cmd = ProducerCommand(producer_id="human_pose", base=BaseCommand())
    recorder.log_frame({"type": "heartbeat"}, cmd)
    recorder.log_frame({"type": "estop"}, cmd)
    assert recorder.state.frame_count == 0
