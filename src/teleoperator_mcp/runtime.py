"""Shared runtime singletons (arbiter, adapter) for WS and MCP surfaces."""

from __future__ import annotations

from .adapters.boomy import BoomyAdapter
from .arbiter.core import AuthorityArbiter
from .producers.human_pose import HumanPoseProducer

_adapter = BoomyAdapter()
_human = HumanPoseProducer(_adapter)
_arbiter = AuthorityArbiter(_adapter, human=_human)


def get_adapter() -> BoomyAdapter:
    return _adapter


def get_arbiter() -> AuthorityArbiter:
    return _arbiter
