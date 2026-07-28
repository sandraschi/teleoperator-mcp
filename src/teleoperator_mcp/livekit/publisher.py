"""Publish Boomy MJPEG → LiveKit room (Goliath-side encoder path, M5)."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

import httpx

from ..config import settings
from .mjpeg import decode_jpeg_to_i420, iter_mjpeg_jpegs
from .tokens import issue_publisher_token

logger = logging.getLogger("teleoperator_mcp.livekit.publisher")

_publisher: BoomyLiveKitPublisher | None = None


@dataclass
class PublisherState:
    running: bool = False
    connected: bool = False
    room: str | None = None
    identity: str | None = None
    frames_published: int = 0
    last_frame_at: float | None = None
    last_error: str | None = None
    source: str = "mjpeg"
    width: int = 0
    height: int = 0


@dataclass
class BoomyLiveKitPublisher:
    state: PublisherState = field(default_factory=PublisherState)
    _task: asyncio.Task | None = field(default=None, repr=False)
    _stop: asyncio.Event = field(default_factory=asyncio.Event, repr=False)

    def status(self) -> dict:
        return {
            "enabled": settings.livekit_enabled,
            "running": self.state.running,
            "connected": self.state.connected,
            "room": self.state.room or settings.livekit_room,
            "identity": self.state.identity or settings.livekit_publisher_identity,
            "frames_published": self.state.frames_published,
            "last_frame_at": self.state.last_frame_at,
            "last_error": self.state.last_error,
            "source": self.state.source,
            "width": self.state.width,
            "height": self.state.height,
            "mjpeg_url": self._mjpeg_url(),
            "livekit_url": settings.livekit_url,
        }

    def _mjpeg_url(self) -> str:
        if settings.livekit_mjpeg_url:
            return settings.livekit_mjpeg_url.rstrip("/")
        return f"{settings.yahboom_api_url.rstrip('/')}/stream"

    async def start(self) -> dict:
        if not settings.livekit_enabled:
            return {"success": False, "message": "LiveKit disabled (TELEOP_LIVEKIT_ENABLED=0)"}
        if self.state.running:
            return {"success": True, "message": "Publisher already running", **self.status()}

        self._stop = asyncio.Event()
        self.state = PublisherState(
            running=True,
            room=settings.livekit_room,
            identity=settings.livekit_publisher_identity,
        )
        self._task = asyncio.create_task(self._run(), name="livekit-publisher")
        logger.info("LiveKit publisher task started room=%s", settings.livekit_room)
        return {"success": True, "message": "Publisher starting", **self.status()}

    async def stop(self) -> dict:
        if not self.state.running and self._task is None:
            return {"success": True, "message": "Publisher not running", **self.status()}
        self._stop.set()
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=8.0)
            except TimeoutError:
                self._task.cancel()
            self._task = None
        self.state.running = False
        self.state.connected = False
        logger.info("LiveKit publisher stopped")
        return {"success": True, "message": "Publisher stopped", **self.status()}

    async def _run(self) -> None:
        try:
            from livekit import rtc
        except ImportError as exc:
            self.state.last_error = str(exc)
            self.state.running = False
            logger.error("livekit package missing: %s", exc)
            return

        room_name = settings.livekit_room
        identity = settings.livekit_publisher_identity
        width = settings.livekit_frame_width
        height = settings.livekit_frame_height
        fps = max(1, settings.livekit_publisher_fps)
        interval = 1.0 / fps

        token = issue_publisher_token(room=room_name, identity=identity, name="Teleop Publisher")
        room = rtc.Room()
        video_source = rtc.VideoSource(width, height)
        video_track = rtc.LocalVideoTrack.create_video_track("boomy-camera", video_source)
        options = rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_CAMERA)

        try:
            await room.connect(settings.livekit_url, token)
            await room.local_participant.publish_track(video_track, options)
            self.state.connected = True
            self.state.width = width
            self.state.height = height
            logger.info("LiveKit publisher connected room=%s", room_name)
        except Exception as exc:
            self.state.last_error = str(exc)
            self.state.running = False
            logger.exception("LiveKit connect failed")
            return

        client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0))
        try:
            mjpeg_ok = await self._publish_mjpeg_loop(
                client, room, video_source, rtc, width, height, interval
            )
            if not mjpeg_ok and settings.livekit_snapshot_fallback:
                self.state.source = "snapshot"
                await self._publish_snapshot_loop(
                    client, video_source, rtc, width, height, interval
                )
        finally:
            await client.aclose()
            self.state.connected = False
            self.state.running = False
            try:
                await room.disconnect()
            except Exception:
                pass

    async def _publish_mjpeg_loop(
        self,
        client: httpx.AsyncClient,
        room,
        video_source,
        rtc,
        width: int,
        height: int,
        interval: float,
    ) -> bool:
        url = self._mjpeg_url()
        self.state.source = "mjpeg"
        try:
            async for jpeg in iter_mjpeg_jpegs(client, url):
                if self._stop.is_set():
                    break
                loop_start = time.monotonic()
                try:
                    i420, w, h = decode_jpeg_to_i420(jpeg, width=width, height=height)
                    frame = rtc.VideoFrame(
                        width=w,
                        height=h,
                        type=rtc.VideoBufferType.I420,
                        data=i420,
                    )
                    video_source.capture_frame(frame)
                    self.state.frames_published += 1
                    self.state.last_frame_at = time.time()
                    self.state.last_error = None
                except Exception as exc:
                    self.state.last_error = str(exc)
                    logger.warning("frame encode failed: %s", exc)
                elapsed = time.monotonic() - loop_start
                await asyncio.sleep(max(0.0, interval - elapsed))
            return self.state.frames_published > 0
        except Exception as exc:
            self.state.last_error = str(exc)
            logger.warning("MJPEG stream failed (%s): %s", url, exc)
            return False

    async def _publish_snapshot_loop(
        self,
        client: httpx.AsyncClient,
        video_source,
        rtc,
        width: int,
        height: int,
        interval: float,
    ) -> None:
        snap_url = f"{settings.yahboom_api_url.rstrip('/')}/api/v1/snapshot"
        logger.info("Falling back to snapshot polling: %s", snap_url)
        while not self._stop.is_set():
            loop_start = time.monotonic()
            try:
                resp = await client.get(snap_url)
                if resp.status_code == 200 and resp.content:
                    i420, w, h = decode_jpeg_to_i420(resp.content, width=width, height=height)
                    frame = rtc.VideoFrame(
                        width=w,
                        height=h,
                        type=rtc.VideoBufferType.I420,
                        data=i420,
                    )
                    video_source.capture_frame(frame)
                    self.state.frames_published += 1
                    self.state.last_frame_at = time.time()
                    self.state.last_error = None
            except Exception as exc:
                self.state.last_error = str(exc)
                logger.debug("snapshot frame failed: %s", exc)
            elapsed = time.monotonic() - loop_start
            await asyncio.sleep(max(0.0, interval - elapsed))


def get_publisher() -> BoomyLiveKitPublisher:
    global _publisher
    if _publisher is None:
        _publisher = BoomyLiveKitPublisher()
    return _publisher


async def start_publisher() -> dict:
    return await get_publisher().start()


async def stop_publisher() -> dict:
    return await get_publisher().stop()
