"""Operator claim / session authentication.

Any browser on the tailnet can reach the backend — CORS restricts *origins*,
not *operators*. Before a WebXR session can drive a robot, the operator must
claim the robot by name and receive a token; the WebSocket requires it. The
e-stop path stays open unauthenticated (safety veto must always work).

Modes:
- TELEOP_REQUIRE_CLAIM=1 (default): WS sessions require a valid claim token.
- TELEOP_REQUIRE_CLAIM=0: claims optional (dev / bench / virtual twins).

Claims are in-memory (single-host gateway); restart clears them.
"""

from __future__ import annotations

import logging
import secrets
import threading
import time
from dataclasses import dataclass

from .config import settings

logger = logging.getLogger("teleoperator_mcp.auth")

_lock = threading.Lock()
_claims: dict[str, OperatorClaim] = {}  # robot_id -> claim


@dataclass
class OperatorClaim:
    robot_id: str
    operator_id: str
    token: str
    claimed_at: float


def require_claim() -> bool:
    return bool(settings.require_claim)


def claim_robot(operator_id: str, robot_id: str) -> dict:
    """Claim a robot for an operator. Replaces any prior claim on that robot."""
    rid = robot_id.strip().lower()
    token = secrets.token_urlsafe(24)
    with _lock:
        _claims[rid] = OperatorClaim(
            robot_id=rid,
            operator_id=operator_id.strip() or "anonymous",
            token=token,
            claimed_at=time.time(),
        )
    logger.info("robot claimed robot=%s operator=%s", rid, operator_id)
    return {
        "success": True,
        "robot_id": rid,
        "operator_id": _claims[rid].operator_id,
        "token": token,
        "claimed_at": _claims[rid].claimed_at,
    }


def verify_token(token: str, robot_id: str) -> bool:
    """True when the token is a valid, current claim for the robot."""
    if not require_claim():
        return True
    if not token:
        return False
    with _lock:
        claim = _claims.get(robot_id.strip().lower())
        return claim is not None and claim.token == token


def release_claim(token: str) -> dict:
    with _lock:
        for rid, claim in list(_claims.items()):
            if claim.token == token:
                del _claims[rid]
                logger.info("robot released robot=%s operator=%s", rid, claim.operator_id)
                return {"success": True, "robot_id": rid, "operator_id": claim.operator_id}
    return {"success": False, "message": "Unknown token"}


def list_claims() -> dict:
    with _lock:
        return {
            rid: {
                "robot_id": c.robot_id,
                "operator_id": c.operator_id,
                "claimed_at": c.claimed_at,
                "token": c.token,
            }
            for rid, c in sorted(_claims.items())
        }
