"""Runtime configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TELEOP_", env_file=".env", extra="ignore")

    host: str = "0.0.0.0"
    port: int = 10901
    yahboom_api_url: str = "http://127.0.0.1:10892"
    watchdog_ms: int = 300
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
