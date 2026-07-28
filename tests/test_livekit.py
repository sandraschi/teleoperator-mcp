"""LiveKit token and MJPEG helpers."""

import numpy as np
import pytest

from teleoperator_mcp.livekit.mjpeg import extract_jpeg_frames, rgb_to_i420


def test_extract_jpeg_frames_single() -> None:
    jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * 10 + b"\xff\xd9"
    buf = bytearray(jpeg)
    frames = extract_jpeg_frames(buf)
    assert len(frames) == 1
    assert frames[0].startswith(b"\xff\xd8")
    assert len(buf) == 0


def test_extract_jpeg_frames_partial_waits() -> None:
    buf = bytearray(b"\xff\xd8\xff")
    assert extract_jpeg_frames(buf) == []
    assert len(buf) == 3


def test_rgb_to_i420_size() -> None:
    rgb = np.zeros((480, 640, 3), dtype=np.uint8)
    i420 = rgb_to_i420(rgb)
    y_size = 640 * 480
    uv_size = (640 // 2) * (480 // 2)
    assert len(i420) == y_size + 2 * uv_size


def _has_livekit_api() -> bool:
    try:
        import livekit.api  # noqa: F401

        return True
    except ImportError:
        return False


@pytest.mark.skipif(not _has_livekit_api(), reason="livekit-api not installed")
def test_issue_subscriber_token() -> None:
    from teleoperator_mcp.livekit.tokens import issue_subscriber_token

    jwt = issue_subscriber_token(room="test-room", identity="viewer-1")
    assert isinstance(jwt, str)
    assert len(jwt) > 20
