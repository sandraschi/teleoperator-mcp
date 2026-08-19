"""Voice command interpretation for teleoperation.

Maps speech-mcp STT transcripts to domain actions (estop, takeover, mode,
gaze, LiveKit). Consumed by the `teleop_voice_command` MCP tool and the fleet
voice command bus router (speech-mcp -> fleet-agent -> this server).

Keyword rules are deterministic (no LLM on the hot path): a small keyword map
covers the fleet voice vocabulary; unknown phrases return a routing hint so the
caller can ask again.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ParsedCommand:
    action: str
    args: dict
    confidence: float = 0.9


_ESTOP_KEYWORDS = ("estop", "e-stop", "emergency stop", "stop now", "kill the robot", "halt")
_TAKEOVER_KEYWORDS = ("take over", "takeover", "reclaim", "hand back", "manual control")
_CENTER_KEYWORDS = (
    "center camera",
    "centre camera",
    "center the camera",
    "look center",
    "camera center",
)
_START_VIDEO_KEYWORDS = (
    "start video",
    "start camera",
    "camera on",
    "video on",
    "start livekit",
    "livekit start",
    "turn on video",
)
_STOP_VIDEO_KEYWORDS = (
    "stop video",
    "stop camera",
    "camera off",
    "video off",
    "stop livekit",
    "livekit stop",
    "turn off video",
)
_STATUS_KEYWORDS = ("status", "report", "how is the robot", "session state")

_GAZE_DIRECTIONS = {
    "left": (60.0, 90.0),
    "right": (120.0, 90.0),
    "up": (90.0, 50.0),
    "down": (90.0, 130.0),
}


def parse_voice_command(transcript: str) -> ParsedCommand:
    """Map a spoken transcript to a deterministic teleop action."""
    text = (transcript or "").strip().lower()

    # E-stop has priority — always exact-match first.
    for kw in _ESTOP_KEYWORDS:
        if kw in text:
            return ParsedCommand(action="estop", args={})

    for kw in _TAKEOVER_KEYWORDS:
        if kw in text:
            return ParsedCommand(action="takeover", args={})

    for kw in _CENTER_KEYWORDS:
        if kw in text:
            return ParsedCommand(action="gaze_center", args={})

    # "look left / right / up / down", "camera left"
    for direction, (pan, tilt) in _GAZE_DIRECTIONS.items():
        if (
            f"look {direction}" in text
            or f"camera {direction}" in text
            or f"turn {direction}" in text
        ):
            return ParsedCommand(action="set_gaze", args={"pan": pan, "tilt": tilt})

    for kw in _START_VIDEO_KEYWORDS:
        if kw in text:
            return ParsedCommand(action="livekit_start", args={})

    for kw in _STOP_VIDEO_KEYWORDS:
        if kw in text:
            return ParsedCommand(action="livekit_stop", args={})

    # Mode changes: "set base auto", "set base to auto", "base to auto",
    # "switch base to direct", "set mode base auto"
    if (
        "set mode" in text
        or "switch" in text
        or "mode to" in text
        or " to auto" in text
        or " to direct" in text
        or " to manual" in text
    ):
        mode = None
        if "auto" in text:
            mode = "AUTO"
        elif "direct" in text or "manual" in text:
            mode = "DIRECT"
        group = "base"
        for g in ("base", "gaze", "manip"):
            if g in text:
                group = g
        if mode:
            return ParsedCommand(
                action="set_mode",
                args={"group": group, "mode": mode},
            )

    for kw in _STATUS_KEYWORDS:
        if kw in text:
            return ParsedCommand(action="status", args={})

    return ParsedCommand(action="unknown", args={}, confidence=0.0)
