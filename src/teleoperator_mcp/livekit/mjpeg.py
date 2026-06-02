"""MJPEG frame extraction and RGB → I420 for LiveKit publish."""

from __future__ import annotations

import io
from collections.abc import AsyncIterator

import httpx
import numpy as np
from PIL import Image


def extract_jpeg_frames(buffer: bytearray) -> list[bytes]:
    """Pull complete JPEG blobs (FF D8 … FF D9) from a growing buffer."""
    frames: list[bytes] = []
    while True:
        start = buffer.find(b"\xff\xd8")
        if start < 0:
            if start > 0:
                del buffer[:start]
            break
        end = buffer.find(b"\xff\xd9", start + 2)
        if end < 0:
            if start > 0:
                del buffer[:start]
            break
        end += 2
        frames.append(bytes(buffer[start:end]))
        del buffer[:end]
    return frames


def decode_jpeg_to_i420(jpeg: bytes, *, width: int, height: int) -> tuple[bytes, int, int]:
    """Decode JPEG, resize, return (i420_bytes, w, h)."""
    img = Image.open(io.BytesIO(jpeg)).convert("RGB")
    if img.size != (width, height):
        img = img.resize((width, height), Image.Resampling.BILINEAR)
    rgb = np.asarray(img, dtype=np.uint8)
    return rgb_to_i420(rgb), width, height


def rgb_to_i420(rgb: np.ndarray) -> bytes:
    """RGB uint8 H×W×3 → I420 bytes."""
    h, w, _ = rgb.shape
    r = rgb[:, :, 0].astype(np.float32)
    g = rgb[:, :, 1].astype(np.float32)
    b = rgb[:, :, 2].astype(np.float32)
    y = (0.299 * r + 0.587 * g + 0.114 * b).clip(0, 255).astype(np.uint8)
    u = (-0.169 * r - 0.331 * g + 0.500 * b + 128.0).clip(0, 255)[::2, ::2].astype(np.uint8)
    v = (0.500 * r - 0.419 * g - 0.081 * b + 128.0).clip(0, 255)[::2, ::2].astype(np.uint8)
    return y.tobytes() + u.tobytes() + v.tobytes()


async def iter_mjpeg_jpegs(client: httpx.AsyncClient, url: str) -> AsyncIterator[bytes]:
    """Stream MJPEG multipart and yield raw JPEG frames."""
    buffer = bytearray()
    async with client.stream("GET", url, timeout=None) as response:
        response.raise_for_status()
        async for chunk in response.aiter_bytes():
            buffer.extend(chunk)
            for frame in extract_jpeg_frames(buffer):
                yield frame
