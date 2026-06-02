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
    default_robot: str = "boomy"
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
