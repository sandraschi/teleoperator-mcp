"""Robot adapter interface - maps ProducerCommand to platform-specific I/O."""

from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

from ..types import ProducerCommand, RobotCapabilities


class RobotAdapter(ABC):
    @property
    @abstractmethod
    def capabilities(self) -> RobotCapabilities:
        raise NotImplementedError

    @abstractmethod
    async def apply(self, command: ProducerCommand, client: httpx.AsyncClient) -> None:
        raise NotImplementedError

    @abstractmethod
    async def e_stop(self, client: httpx.AsyncClient) -> None:
        raise NotImplementedError
