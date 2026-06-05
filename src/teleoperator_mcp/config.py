"""Runtime configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TELEOP_", env_file=".env", extra="ignore")

    host: str = "0.0.0.0"
    port: int = 10901
    yahboom_api_url: str = "http://127.0.0.1:10892"
    watchdog_ms: int = 1000
    pose_hz_cap: int = 30
    max_linear: float = 0.3
    max_angular: float = 0.8
    pan_gain: float = 60.0
    tilt_gain: float = 45.0
    # Boomy servos: absolute 0-180°, neutral at center (see yahboom camera_set_pos)
    ptz_pan_center: float = 90.0
    ptz_tilt_center: float = 90.0
    gaze_every_n_frames: int = 1
    gaze_min_delta_deg: float = 1.0
    default_robot: str = "boomy"
    bumi_api_url: str = "http://127.0.0.1:10774"
    bumi_max_linear: float = 0.15
    bumi_max_angular: float = 0.4
    bumi_head_yaw_gain: float = 57.3
    bumi_head_pitch_gain: float = 45.0
    # Session recording (LeRobot-compatible JSONL, M4)
    recording_enabled: bool = True
    recording_dir: str = "data/teleop_recordings"
    recording_fps: int = 30
    # LiveKit video return (M5) — myconf SFU on Goliath :15580
    livekit_enabled: bool = True
    livekit_url: str = "ws://127.0.0.1:15580"
    livekit_public_url: str = ""  # Browser WSS URL; empty → livekit_url
    livekit_api_key: str = "devkey"
    livekit_api_secret: str = "secret"
    livekit_room: str = "teleop-boomy"
    livekit_publisher_identity: str = "teleop-publisher"
    livekit_publisher_fps: int = 15
    livekit_frame_width: int = 640
    livekit_frame_height: int = 480
    livekit_mjpeg_url: str = ""  # empty → {yahboom_api_url}/stream
    livekit_snapshot_fallback: bool = True
    livekit_auto_start_publisher: bool = False
    # AUTO safety (M3 nav stub)
    auto_max_duration_s: float = 10.0
    auto_warn_before_s: float = 3.0
    auto_require_webxr: bool = True
    nav_stub_linear: float = 0.15
    nav_stub_angular: float = 0.0
    # Spoken warnings via speech-mcp (port 10909); SAPI fallback if unreachable
    speech_enabled: bool = True
    speech_mcp_url: str = "http://127.0.0.1:10909"
    speech_provider: str = "windows"
    # Comma-separated browser origins (WebXR dev + Pico/Tailscale). No wildcard + credentials.
    cors_origins: str = (
        "http://localhost:10900,"
        "http://127.0.0.1:10900,"
        "https://localhost:10900,"
        "https://127.0.0.1:10900"
    )


settings = Settings()


def cors_origins_list() -> list[str]:
    return [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
