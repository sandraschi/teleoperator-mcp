"""Egress sink tests — video frames recorded into episodes and carried into parquet."""

import json
import time
from pathlib import Path

from teleoperator_mcp.config import settings
from teleoperator_mcp.recording.egress import EgressSink, get_egress
from teleoperator_mcp.recording.export_lerobot import (
    _image_path_rewrite,
    _write_parquet,
    export_lerobot_dataset,
)
from teleoperator_mcp.recording.recorder import SessionRecorder

JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01" + b"\x00" * 32 + b"\xff\xd9"


def _make_episode(tmp_path: Path, *, with_images: bool = True) -> Path:
    rec = SessionRecorder(tmp_path / "recordings")
    rec.start_session("boomy")
    if with_images:
        get_egress().reset()
        get_egress().capture(JPEG)  # seq 1 (skipped by default interval=2)
        get_egress().capture(JPEG)  # seq 2 (kept)
    rec.log_frame(
        {
            "type": "pose",
            "seq": 1,
            "head": {"yaw": 0.1, "pitch": 0.0, "roll": 0.0},
            "right": {"axes": [0.0, 0.0], "buttons": {"trigger": 0.0}},
        },
        rec._frames
        and rec._frames[0]
        or type(
            "C", (), {"base": None, "gaze": None, "manip": None, "producer_id": "human_pose"}
        )(),
    )
    summary = rec.end_session()
    assert summary is not None
    return tmp_path / "recordings"


def test_egress_ring_nearest_and_take() -> None:
    sink = EgressSink()
    sink.reset()
    now = time.time()
    sink.capture(JPEG)  # seq 1 (skipped by default interval=2)
    sink.capture(JPEG)  # seq 2 (kept)
    # nearest within tolerance
    frame = sink.nearest(now, 0.5)
    assert frame is not None
    assert frame.jpeg == JPEG
    # take removes it
    taken = sink.take(now, 0.5)
    assert taken is not None
    assert sink.take(now, 0.5) is None


def test_egress_tolerance_rejects_old_frame() -> None:
    sink = EgressSink()
    sink.reset()
    sink.capture(JPEG)
    sink.capture(JPEG)
    # teleop frame way in the past -> no match
    assert sink.nearest(time.time() - 10, 0.5) is None


def test_egress_interval_skips() -> None:
    old = settings.livekit_egress_interval
    settings.livekit_egress_interval = 2
    try:
        sink = EgressSink()
        sink.reset()
        sink.capture(JPEG)  # seq 1 -> skipped (1 % 2 != 0)
        sink.capture(JPEG)  # seq 2 -> kept
        assert len(sink._frames) == 1
    finally:
        settings.livekit_egress_interval = old


def test_recorder_saves_image_row(tmp_path: Path) -> None:
    old_tol = settings.livekit_egress_tolerance_ms
    settings.livekit_egress_tolerance_ms = 3000  # match regardless of capture timing
    try:
        base = _make_episode(tmp_path)
        ep = next(base.glob("data/episode_*"))
        frames = list((ep / "frames.jsonl").read_text(encoding="utf-8").splitlines())
        assert frames and "observation.image.image" in json.loads(frames[0])
        assert (ep / "images" / "observation.image" / "000000.jpg").exists()
    finally:
        settings.livekit_egress_tolerance_ms = old_tol
        get_egress().reset()


def test_export_carries_images(tmp_path: Path) -> None:
    old_tol = settings.livekit_egress_tolerance_ms
    settings.livekit_egress_tolerance_ms = 3000
    try:
        base = _make_episode(tmp_path)
        out = tmp_path / "out"
        result = export_lerobot_dataset(base, out, fps=30)
        assert result.success
        parquet = next((out / "data" / "chunk-000").glob("episode_*.parquet"))
        import pyarrow.parquet as pq

        schema = pq.read_schema(parquet)
        names = set(schema.names)
        assert "observation.image.image" in names
        # images copied into chunked layout
        images = list((out / "data" / "chunk-000").glob("episode_*/images/observation.image/*.jpg"))
        assert images
        # info.json declares image feature
        info = json.loads((out / "meta" / "info.json").read_text(encoding="utf-8"))
        assert "observation.image.image" in info["features"]
        assert info["video_path"] is not None
    finally:
        settings.livekit_egress_tolerance_ms = old_tol
        get_egress().reset()


def test_export_without_images_has_no_video_path(tmp_path: Path) -> None:
    base = _make_episode(tmp_path, with_images=False)
    out = tmp_path / "out2"
    result = export_lerobot_dataset(base, out, fps=30)
    assert result.success
    info = json.loads((out / "meta" / "info.json").read_text(encoding="utf-8"))
    assert info["video_path"] is None
    assert "observation.image.image" not in info["features"]


def test_image_path_rewrite() -> None:
    assert _image_path_rewrite("data/episode_000000/images/observation.image/000000.jpg") == (
        "data/chunk-000/episode_000000/images/observation.image/000000.jpg"
    )


def test_write_parquet_dynamic_image_col(tmp_path: Path) -> None:
    p = tmp_path / "episode_000000.parquet"
    _write_parquet(
        p,
        [
            {
                "timestamp": 1.0,
                "frame_index": 0,
                "episode_index": 0,
                "index": 0,
                "task_index": 0,
                "observation.state": [0.0, 0.0, 0.0, 90.0, 90.0],
                "action": [0.0, 0.0, 0.0, 90.0, 90.0],
                "observation.image.image": "data/chunk-000/episode_000000/images/observation.image/000000.jpg",
                "next.done": True,
            }
        ],
    )
    import pyarrow.parquet as pq

    assert "observation.image.image" in set(pq.read_schema(p).names)


def test_egress_status_endpoint() -> None:
    from teleoperator_mcp.server import app

    assert "/api/v1/livekit/egress" in {r.path for r in app.routes}
