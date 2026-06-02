"""LiveKit JWT helpers (myconf-compatible devkey/secret)."""

from __future__ import annotations

from ..config import settings


def _require_livekit_api():
    try:
        from livekit import api
    except ImportError as exc:
        raise RuntimeError(
            "livekit-api not installed — run: uv sync (includes livekit extras)"
        ) from exc
    return api


def issue_subscriber_token(*, room: str, identity: str, name: str | None = None) -> str:
    api = _require_livekit_api()
    token = (
        api.AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        .with_identity(identity)
        .with_name(name or identity)
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=room,
                can_publish=False,
                can_subscribe=True,
            )
        )
    )
    return token.to_jwt()


def issue_publisher_token(*, room: str, identity: str, name: str | None = None) -> str:
    api = _require_livekit_api()
    token = (
        api.AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        .with_identity(identity)
        .with_name(name or identity)
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=room,
                room_create=True,
                can_publish=True,
                can_subscribe=False,
            )
        )
    )
    return token.to_jwt()


def livekit_public_config() -> dict:
    return {
        "enabled": settings.livekit_enabled,
        "url": settings.livekit_public_url or settings.livekit_url,
        "room": settings.livekit_room,
        "publisher_fps": settings.livekit_publisher_fps,
    }
